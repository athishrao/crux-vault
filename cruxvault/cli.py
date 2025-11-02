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

    if os.path.exists(config_manager.config_path):
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


def main() -> None:
    app()
