import os
import sys
import json
import typer
import secrets as secrets_lib
import subprocess
from rich.table import Table
from typing import Optional, Any

from cruxvault.models import SecretType
from cruxvault.config import ConfigManager
from cruxvault.crypto.encryption import Encryptor
from cruxvault.utils.console import (
    console,
    create_history_table,
    create_secrets_table,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from cruxvault.utils.utils import get_storage_and_audit, get_audit_logger, get_storage

app = typer.Typer(
    help="Unified secrets, configs, and feature flags management",
    add_completion=False,
)
dev_app = typer.Typer(help="Development mode commands")
app.add_typer(dev_app, name="dev")

@app.command()
def init() -> None:
    config_manager = ConfigManager()

    if config_manager.config_path is not None and os.path.exists(config_manager.config_path):
        print_warning(f"Already initialized in {config_manager.config_dir}")
        return

    try:
        config_manager.initialize()

        storage, audit_logger = get_storage_and_audit()
        storage.initialize()

        storage.create_branch("main")
        config_manager.set_current_branch("main")

        audit_logger.log("init", ".", success=True)

        print_success(f"Initialized cruxvault in {config_manager.config_dir}")
        print_info(f"Storage: {config_manager.get_storage_path()}")
        print_info(f"Audit log: {config_manager.get_audit_path()}")
        print_info(f"Branch: main")

    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log("init", ".", success=False)
        print_error(f"Initialization failed: {e}")
        sys.exit(1)


@app.command()
def set(
    path: str = typer.Argument(..., help="Secret path (e.g., database/password)"),
    value: str = typer.Argument(..., help="Secret value"),
    tag: Optional[list[str]] = typer.Option(None, "--tag", "-t", help="Tags for organization"),
    secret_type: str = typer.Option("secret", "--type", help="Type: secret, config, or flag"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    try:
        storage, audit_logger = get_storage_and_audit()

        try:
            SecretType(secret_type)
        except ValueError:
            print_error(f"Invalid type: {secret_type}. Must be: secret, config, or flag")
            sys.exit(1)

        secret = storage.set_secret(path, value, secret_type, tag or [])

        audit_logger.log("set", path, success=True, metadata={"tags": tag or []})

        if json_output:
            output = secret.model_dump()
            output["value"] = "•" * 8  # Hide value in JSON output
            console.print_json(data=output)
        else:
            print_success(f"Set {path} (version {secret.version})")

    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log("set", path, success=False, error=str(e))
        print_error(f"Failed to set secret: {e}")
        sys.exit(1)


@app.command()
def get(
    path: str = typer.Argument(..., help="Secret path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only output the value"),
) -> None:
    try:
        storage, audit_logger = get_storage_and_audit()

        secret = storage.get_secret(path)

        audit_logger.log("get", path, success=True)

        if not secret:
            print_error(f"Secret not found: {path}")
            sys.exit(1)

        if quiet:
            print(secret.value)
        elif json_output:
            console.print_json(data=secret.model_dump(mode="json"))
        else:
            console.print(secret.value)

    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log("get", path, success=False, error=str(e))
        print_error(f"Failed to get secret: {e}")
        sys.exit(1)


@app.command()
def list(
    path: Optional[str] = typer.Argument(None, help="Optional path prefix to filter"),
    show_values: bool = typer.Option(False, "--show-values", help="Show secret values"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    try:
        storage, audit_logger = get_storage_and_audit()

        secrets = storage.list_secrets(path)

        audit_logger.log("list", path or ".", success=True)

        if not secrets:
            print_info("No secrets found")
            return

        if json_output:
            output = [s.model_dump(mode="json") for s in secrets]
            if not show_values:
                for item in output:
                    item["value"] = "•" * 8
            console.print_json(data=output)
        else:
            table = create_secrets_table(secrets, show_values=show_values, show_versions=True)
            console.print(table)
            console.print(f"\n[dim]Total: {len(secrets)} secret(s)[/dim]")

    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log("list", path or ".", success=False, error=str(e))
        print_error(f"Failed to list secrets: {e}")
        sys.exit(1)


@app.command()
def delete(
    path: str = typer.Argument(..., help="Secret path to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    try:
        storage, audit_logger = get_storage_and_audit()

        secret = storage.get_secret(path)
        if not secret:
            print_error(f"Secret not found: {path}")
            sys.exit(1)

        if not force:
            confirm = typer.confirm(f"Delete {path}?")
            if not confirm:
                print_info("Cancelled")
                return

        storage.delete_secret(path)

        audit_logger.log("delete", path, success=True)

        print_success(f"Deleted {path}")

    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log("delete", path, success=False, error=str(e))
        print_error(f"Failed to delete secret: {e}")
        sys.exit(1)


@app.command()
def history(
    path: str = typer.Argument(..., help="Secret path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    try:
        storage, audit_logger = get_storage_and_audit()

        versions = storage.get_history(path)

        audit_logger.log("history", path, success=True)

        if not versions:
            print_error(f"No history found for: {path}")
            sys.exit(1)

        if json_output:
            console.print_json(data=[v.model_dump() for v in versions])
        else:
            table = create_history_table(versions)
            console.print(f"\n[bold]History for {path}[/bold]\n")
            console.print(table)

    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log("history", path, success=False, error=str(e))
        print_error(f"Failed to get history: {e}")
        sys.exit(1)


@app.command()
def rollback(
    path: str = typer.Argument(..., help="Secret path"),
    version: int = typer.Argument(..., help="Version number to rollback to"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    try:
        storage, audit_logger = get_storage_and_audit()

        # Confirm rollback
        if not force:
            confirm = typer.confirm(f"Rollback {path} to version {version}?")
            if not confirm:
                print_info("Cancelled")
                return

        # Rollback
        secret = storage.rollback(path, version)

        audit_logger.log(
            "rollback", path, success=True, metadata={"rollback_version": version}
        )

        print_success(f"Rolled back {path} to version {version} (now version {secret.version})")

    except ValueError as e:
        audit_logger.log("rollback", path, success=False, error=str(e))
        print_error(str(e))
        sys.exit(1)
    except Exception as e:
        audit_logger = get_audit_logger()
        audit_logger.log("rollback", path, success=False, error=str(e))
        print_error(f"Failed to rollback: {e}")
        sys.exit(1)


@dev_app.command("start")
def dev_start(
    count: int = typer.Option(10, "--count", "-n", help="Number of fake secrets to generate"),
) -> None:
    try:
        storage, audit_logger = get_storage_and_audit()

        fake_secrets = [
            ("database/host", "localhost"),
            ("database/port", "5432"),
            ("database/username", "dev_user"),
            ("database/password", secrets_lib.token_urlsafe(16)),
            ("api/key", secrets_lib.token_urlsafe(32)),
            ("api/secret", secrets_lib.token_urlsafe(32)),
            ("stripe/public_key", f"pk_test_{secrets_lib.token_urlsafe(16)}"),
            ("stripe/secret_key", f"sk_test_{secrets_lib.token_urlsafe(16)}"),
            ("jwt/secret", secrets_lib.token_urlsafe(32)),
            ("encryption/key", secrets_lib.token_urlsafe(32)),
        ]

        created = 0
        for path, value in fake_secrets[:count]:
            try:
                storage.set_secret(path, value, "config", ["development", "fake"])
                created += 1
            except Exception:
                continue


        audit_logger.log("dev:start", ".", success=True, metadata={"count": created})

        print_success(f"Generated {created} fake secrets for development")
        print_info("Use 'crux list' to see all secrets")

    except Exception as e:
        print_error(f"Failed to generate fake secrets: {e}")
        sys.exit(1)


@dev_app.command("export")
def dev_export(
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    try:
        storage, audit_logger = get_storage_and_audit()

        secrets_list = storage.list_secrets()

        if not secrets_list:
            print_info("No secrets to export")
            return

        lines = []
        for secret in secrets_list:
            # Convert path to env var name (database/password -> DATABASE_PASSWORD)
            env_name = secret.path.replace("/", "_").replace("-", "_").upper()
            lines.append(f'{env_name}="{secret.value}"')

        env_content = "\n".join(lines)

        if output_file:
            with open(output_file, "w") as f:
                f.write(env_content)
            print_success(f"Exported {len(secrets_list)} secrets to {output_file}")
        else:
            console.print(env_content)

        audit_logger.log(
            "dev:export",
            output_file or "stdout",
            success=True,
            metadata={"count": len(secrets_list)},
        )

    except Exception as e:
        print_error(f"Failed to export secrets: {e}")
        sys.exit(1)


@app.command()
def import_env(
    file_path: str = typer.Argument(..., help=".env file to import"),
    prefix: Optional[str] = typer.Option(None, "--prefix", "-p", help="Prefix for imported keys"),
) -> None:
    try:
        if not os.path.exists(file_path):
            print_error(f"File not found: {file_path}")
            sys.exit(1)

        storage, audit_logger = get_storage_and_audit()

        imported = 0
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if not value:
                    continue

                path = key.lower().replace("_", "/")

                if prefix:
                    path = f"{prefix}/{path}"

                try:
                    storage.set_secret(path, value, "config", ["imported"])
                    imported += 1
                except Exception:
                    continue

        audit_logger.log(
            "import:env", file_path, success=True, metadata={"count": imported, "prefix": prefix}
        )
    
        print_success(f"Imported {imported} secrets from {file_path}")

    except Exception as e:
        print_error(f"Failed to import secrets: {e}")
        sys.exit(1)


@app.command()
def shell_env(
    prefix: Optional[str] = typer.Argument(None),
    format: str = typer.Option("bash", help="Shell format: bash, fish, powershell")
) -> None:
    try:
        storage, audit_logger = get_storage_and_audit()
        secrets = storage.list_secrets(prefix)

        for secret in secrets:
            env_key = secret.path.upper().replace('/', '_').replace('-', '_')

            if format == "bash":
                console.print(f'export {env_key}="{secret.value}"')
            elif format == "fish":
                console.print(f'set -x {env_key} "{secret.value}"')
            elif format == "powershell":
                console.print(f'$env:{env_key}="{secret.value}"')
            audit_logger.log(
                    "shell_env", ".", success=True, metadata={"env_var_name": env_key}
            )

    except Exception as e:
        print_error(f"Failed to apply env vars to shell: {e}")
        raise typer.Exit(1)


@app.command()
def scan(
    path: str = typer.Argument(".", help="Path to scan"),
) -> None:
    try:
        result = subprocess.run(
            ["detect-secrets", "scan", path],
            capture_output=True,
            text=True
        )
        output = json.loads(result.stdout)

        if not output.get("results"):
            print_info("No secrets detected!")
        else:
            print_warning("Potential secrets found:")
            console.print(output["results"])

    except Exception as e:
        print_error(f"Failed to scan codebase for potential secrets: {e}")
        raise typer.Exit(1)


@app.command()
def unset_env(
    prefix: Optional[str] = typer.Argument(None),
    tag: Optional[str] = typer.Option(None, help="Filter by tag"),
    format: str = typer.Option("bash", help="Shell format: bash, fish, powershell")
) -> None:
    try:
        storage, audit_logger = get_storage_and_audit()
        secrets = storage.list_secrets(prefix)

        if tag:
            secrets = [s for s in secrets if tag in s.tags]

        for secret in secrets:
            env_key = secret.path.upper().replace('/', '_').replace('-', '_')

            if format == "bash":
                console.print(f'unset {env_key};')
            elif format == "fish":
                console.print(f'set -e {env_key};')
            elif format == "powershell":
                console.print(f'Remove-Item Env:{env_key};')
            audit_logger.log(
                    "unset_env", ".", success=True, metadata={"env_var_name": env_key}
            )

    except Exception as e:
        print_error(f"Failed to unset vars in shell: {e}")
        raise typer.Exit(1)

@app.command()
def branch(
    name: Optional[str] = typer.Argument(None, help="Branch name to create"),
    list_branches: bool = typer.Option(False, "--list", "-l", help="List all branches"),
    delete: Optional[str] = typer.Option(None, "--delete", "-d", help="Delete a branch"),
    from_branch: Optional[str] = typer.Option(None, "--from", help="Create from branch"),
) -> None:
    try:
        config_mgr = ConfigManager()
        storage = get_storage(config_mgr)

        if list_branches:
            branches = storage.list_branches()
            current = config_mgr.get_current_branch()

            if not branches:
                console.print("No branches found")
                return

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Branch")
            table.add_column("Commits")
            table.add_column("Created")

            for b in branches:
                marker = "* " if b.name == current else "  "
                commits = len(storage.get_commit_history(b.name, limit=1000))
                table.add_row(
                    f"{marker}{b.name}",
                    str(commits) if b.head_commit_id else "0",
                    b.created_at.strftime("%Y-%m-%d %H:%M"),
                )

            console.print(table)

        elif delete:
            if storage.delete_branch(delete):
                print_success(f"Deleted branch '{delete}'")
            else:
                print_error(f"Branch '{delete}' not found")
                sys.exit(1)

        elif name:
            branch_obj = storage.create_branch(name, from_branch=from_branch)
            print_success(f"Created branch '{name}'")
            print_success(f"Run `crux checkout '{name}'` to switch to the branch")
        else:
            current = config_mgr.get_current_branch()
            console.print(f"On branch: [cyan]{current}[/cyan]")

    except Exception as e:
        print_error(f"Branch operation failed: {e}")
        sys.exit(1)


@app.command()
def checkout(
    branch_name: str = typer.Argument(..., help="Branch name to checkout"),
) -> None:
    try:
        config_mgr = ConfigManager()
        storage = get_storage(config_mgr)

        branch = storage.get_branch(branch_name)
        if not branch:
            print_error(f"Branch '{branch_name}' not found")
            sys.exit(1)

        confirm = typer.confirm(f"If branch is not clean, proceeding will clear all your dirty secrets(pun intended). Proceed to switching to {branch_name}?")
        if not confirm:
            print_info("Cancelled")
            sys.exit(0)

        storage.checkout_branch(branch_name)
        config_mgr.set_current_branch(branch_name)

        print_success(f"Switched to branch '{branch_name}'")

    except Exception as e:
        print_error(f"Checkout failed: {e}")
        sys.exit(1)


@app.command()
def commit(
    message: str = typer.Option(..., "--message", "-m", help="Commit message"),
) -> None:
    try:
        config_mgr = ConfigManager()
        storage = get_storage(config_mgr)
        current_branch = config_mgr.get_current_branch()

        commit_obj = storage.commit(current_branch, message)
        print_success(f"[{commit_obj.branch} {commit_obj.id[:7] if isinstance(commit_obj.id, str) else commit_obj.id}] {commit_obj.message}")

    except Exception as e:
        print_error(f"Commit failed: {e}")
        sys.exit(1)


@app.command()
def log(
    branch_name: Optional[str] = typer.Argument(None, help="Branch name (default: current)"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of commits to show"),
) -> None:
    try:
        config_mgr = ConfigManager()
        storage = get_storage(config_mgr)

        if not branch_name:
            branch_name = config_mgr.get_current_branch()

        commits = storage.get_commit_history(branch_name, limit=limit)

        if not commits:
            console.print(f"No commits on branch '{branch_name}'")
            return

        for c in commits:
            console.print(f"[yellow]commit {c.id}[/yellow]")
            console.print(f"Author: {c.author}")
            console.print(f"Date:   {c.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            console.print(f"\n    {c.message}\n")

    except Exception as e:
        print_error(f"Log failed: {e}")
        sys.exit(1)


@app.command()
def status() -> None:
    try:
        config_mgr = ConfigManager()
        storage = get_storage(config_mgr)
        current_branch = config_mgr.get_current_branch()

        console.print(f"On branch: [cyan]{current_branch}[/cyan]\n")

        status = storage.get_status(current_branch)

        if not any(status.values()):
            console.print("[green]Nothing to commit, working tree clean[/green]")
            return

        if status["added"]:
            console.print("[green]New secrets:[/green]")
            for path in status["added"]:
                console.print(f"  [green]+ {path}[/green]")

        if status["modified"]:
            console.print("[yellow]Modified secrets:[/yellow]")
            for path in status["modified"]:
                console.print(f"  [yellow]M {path}[/yellow]")

        if status["deleted"]:
            console.print("[red]Deleted secrets:[/red]")
            for path in status["deleted"]:
                console.print(f"  [red]- {path}[/red]")

        console.print(f"\nRun 'crux commit -m \"message\"' to commit changes")

    except Exception as e:
        print_error(f"Status failed: {e}")
        sys.exit(1)


@app.command()
def diff(
    commit1: Optional[str] = typer.Argument(None, help="First commit ID"),
    commit2: Optional[str] = typer.Argument(None, help="Second commit ID"),
) -> None:
    try:
        config_mgr = ConfigManager()
        storage = get_storage(config_mgr)
        current_branch = config_mgr.get_current_branch()

        if not commit1:
            status = storage.get_status(current_branch)
            if not any(status.values()):
                console.print("No changes")
                return

            if status["added"]:
                for path in status["added"]:
                    console.print(f"[green]+ {path}: <new>[/green]")

            if status["modified"]:
                for path in status["modified"]:
                    console.print(f"[yellow]M {path}: <modified>[/yellow]")

            if status["deleted"]:
                for path in status["deleted"]:
                    console.print(f"[red]- {path}: <deleted>[/red]")
            return

        if not commit2:
            print_error("Please provide both commit IDs")
            sys.exit(1)

        diff_entries = storage.diff_commits(int(commit1), int(commit2))

        if not diff_entries:
            console.print("No differences")
            return

        for entry in diff_entries:
            if entry.status == "added":
                console.print(f"[green]+ {entry.path}[/green]")
                console.print(f"  [green]{entry.new_value}[/green]")
            elif entry.status == "modified":
                console.print(f"[yellow]M {entry.path}[/yellow]")
                console.print(f"  [red]- {entry.old_value}[/red]")
                console.print(f"  [green]+ {entry.new_value}[/green]")
            elif entry.status == "deleted":
                console.print(f"[red]- {entry.path}[/red]")
                console.print(f"  [red]{entry.old_value}[/red]")

    except Exception as e:
        print_error(f"Diff failed: {e}")
        sys.exit(1)


@app.command()
def reset(
    commit_id: int = typer.Argument(..., help="Commit ID to reset to"),
    hard: bool = typer.Option(False, "--hard", help="Discard uncommitted changes"),
) -> None:
    try:
        config_mgr = ConfigManager()
        storage = get_storage(config_mgr)
        current_branch = config_mgr.get_current_branch()

        storage.rollback_to_commit(current_branch, commit_id)
        print_success(f"Reset {current_branch} to commit {commit_id}")

    except Exception as e:
        print_error(f"Reset failed: {e}")
        sys.exit(1)


@app.command()
def merge(
    source_branch: str = typer.Argument(..., help="Branch to merge from"),
    force: bool = typer.Option(False, "--force", "-f", help="Force merge on conflicts"),
) -> None:
    try:
        config_mgr = ConfigManager()
        storage = get_storage(config_mgr)
        current_branch = config_mgr.get_current_branch()

        if current_branch == source_branch:
            print_error("Cannot merge branch into itself")
            sys.exit(1)

        success, conflicts = storage.merge_branch(current_branch, source_branch)

        if conflicts and not force:
            console.print("[red]Merge conflicts detected:[/red]\n")
            for conflict in conflicts:
                console.print(f"[yellow]{conflict.path}:[/yellow]")
                console.print(f"  Current:  {conflict.current_value}")
                console.print(f"  Incoming: {conflict.incoming_value}\n")
            console.print("Resolve conflicts manually or use --force to accept incoming changes")
            sys.exit(1)

        if success:
            # Create merge commit
            storage.commit(current_branch, f"Merge branch '{source_branch}' into {current_branch}")
            print_success(f"Merged '{source_branch}' into '{current_branch}'")
        else:
            print_error("Merge failed")
            sys.exit(1)

    except Exception as e:
        print_error(f"Merge failed: {e}")
        sys.exit(1)

def main() -> None:
    app()
