import os
import sys
import typer
from typing import Optional, Any

from cruxvault.models import SecretType
from cruxvault.config import ConfigManager
from cruxvault.crypto.encryption import Encryptor
from cruxvault.crypto.utils import get_or_create_master_key
from cruxvault.storage.local import SQLiteStorage
from cruxvault.utils.console import (
    console,
    create_history_table,
    create_secrets_table,
    print_error,
    print_info,
    print_success,
    print_warning,
)

app = typer.Typer(
    help="Unified secrets, configs, and feature flags management",
    add_completion=False,
)
dev_app = typer.Typer(help="Development mode commands")
app.add_typer(dev_app, name="dev")

def get_storage() -> SQLiteStorage:
    config_manager = ConfigManager()
    config = config_manager.load_config()

    master_key = get_or_create_master_key()
    encryptor = Encryptor(master_key)

    storage_path = config_manager.get_storage_path()
    storage = SQLiteStorage(storage_path, encryptor)

    return storage

@app.command()
def init() -> None:
    config_manager = ConfigManager()

    if config_manager.config_path is not None and os.path.exists(config_manager.config_path):
        print_warning(f"Already initialized in {config_manager.config_dir}")
        return

    try:
        config_manager.initialize()

        storage = get_storage()
        storage.initialize()

        print_success(f"Initialized cruxvault in {config_manager.config_dir}")
        print_info(f"Storage: {config_manager.get_storage_path()}")

    except Exception as e:
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
        storage = get_storage()

        try:
            SecretType(secret_type)
        except ValueError:
            print_error(f"Invalid type: {secret_type}. Must be: secret, config, or flag")
            sys.exit(1)

        secret = storage.set_secret(path, value, secret_type, tag or [])

        if json_output:
            output = secret.model_dump()
            output["value"] = "•" * 8  # Hide value in JSON output
            console.print_json(data=output)
        else:
            print_success(f"Set {path} (version {secret.version})")

    except Exception as e:
        print_error(f"Failed to set secret: {e}")
        sys.exit(1)


@app.command()
def get(
    path: str = typer.Argument(..., help="Secret path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Only output the value"),
) -> None:
    try:
        storage = get_storage()

        secret = storage.get_secret(path)

        if not secret:
            print_error(f"Secret not found: {path}")
            sys.exit(1)

        if quiet:
            print(secret.value)
        elif json_output:
            console.print_json(data=secret.model_dump())
        else:
            console.print(secret.value)

    except Exception as e:
        print_error(f"Failed to get secret: {e}")
        sys.exit(1)


@app.command()
def list(
    path: Optional[str] = typer.Argument(None, help="Optional path prefix to filter"),
    show_values: bool = typer.Option(False, "--show-values", help="Show secret values"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    try:
        storage = get_storage()

        secrets = storage.list_secrets(path)

        if not secrets:
            print_info("No secrets found")
            return

        if json_output:
            output = [s.model_dump() for s in secrets]
            if not show_values:
                for item in output:
                    item["value"] = "•" * 8
            console.print_json(data=output)
        else:
            table = create_secrets_table(secrets, show_values=show_values, show_versions=True)
            console.print(table)
            console.print(f"\n[dim]Total: {len(secrets)} secret(s)[/dim]")

    except Exception as e:
        print_error(f"Failed to list secrets: {e}")
        sys.exit(1)


@app.command()
def delete(
    path: str = typer.Argument(..., help="Secret path to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    try:
        storage = get_storage()

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

        print_success(f"Deleted {path}")

    except Exception as e:
        print_error(f"Failed to delete secret: {e}")
        sys.exit(1)


@app.command()
def history(
    path: str = typer.Argument(..., help="Secret path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    try:
        storage = get_storage()

        versions = storage.get_history(path)

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
        print_error(f"Failed to get history: {e}")
        sys.exit(1)


@app.command()
def rollback(
    path: str = typer.Argument(..., help="Secret path"),
    version: int = typer.Argument(..., help="Version number to rollback to"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    try:
        storage = get_storage()

        # Confirm rollback
        if not force:
            confirm = typer.confirm(f"Rollback {path} to version {version}?")
            if not confirm:
                print_info("Cancelled")
                return

        # Rollback
        secret = storage.rollback(path, version)

        print_success(f"Rolled back {path} to version {version} (now version {secret.version})")

    except ValueError as e:
        print_error(str(e))
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to rollback: {e}")
        sys.exit(1)


@dev_app.command("start")
def dev_start(
    count: int = typer.Option(10, "--count", "-n", help="Number of fake secrets to generate"),
) -> None:
    try:
        storage = get_storage()

        fake_secrets = [
            ("database/host", "localhost"),
            ("database/port", "5432"),
            ("database/username", "dev_user"),
            ("database/password", secrets.token_urlsafe(16)),
            ("api/key", secrets.token_urlsafe(32)),
            ("api/secret", secrets.token_urlsafe(32)),
            ("stripe/public_key", f"pk_test_{secrets.token_urlsafe(16)}"),
            ("stripe/secret_key", f"sk_test_{secrets.token_urlsafe(16)}"),
            ("jwt/secret", secrets.token_urlsafe(32)),
            ("encryption/key", secrets.token_urlsafe(32)),
        ]

        created = 0
        for path, value in fake_secrets[:count]:
            try:
                storage.set_secret(path, value, "config", ["development", "fake"])
                created += 1
            except Exception:
                continue


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
        storage = get_storage()

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

        storage = get_storage()

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

                path = key.lower().replace("_", "/")

                if prefix:
                    path = f"{prefix}/{path}"

                try:
                    storage.set_secret(path, value, "config", ["imported"])
                    imported += 1
                except Exception:
                    continue

        print_success(f"Imported {imported} secrets from {file_path}")

    except Exception as e:
        print_error(f"Failed to import secrets: {e}")
        sys.exit(1)


def main() -> None:
    app()
