from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def print_success(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    console.print(f"[red]✗[/red] {message}", style="red")


def print_error(message: str) -> None:
    console.print(f"[red]✗[/red] {message}", style="red")


def print_warning(message: str) -> None:
    console.print(f"[yellow]![/yellow] {message}", style="yellow")


def print_info(message: str) -> None:
    console.print(f"[blue]ℹ[/blue] {message}")


def create_secrets_table(
    secrets: list[Any], show_values: bool = False, show_versions: bool = False
) -> Table:
    table = Table(show_header=True, header_style="bold magenta")

    table.add_column("Path", style="cyan", no_wrap=False)
    table.add_column("Type", style="blue")

    if show_versions:
        table.add_column("Version", justify="right", style="yellow")

    if show_values:
        table.add_column("Value", style="green")
    else:
        table.add_column("Value", style="dim")

    table.add_column("Tags", style="magenta")
    table.add_column("Updated", style="dim")

    for secret in secrets:
        row = [
            secret.path,
            secret.type.value,
        ]

        if show_versions:
            row.append(str(secret.version))

        if show_values:
            row.append(secret.value)
        else:
            row.append("•" * 8)  # Hidden value

        row.extend([
            ", ".join(secret.tags) if secret.tags else "",
            secret.updated_at.strftime("%Y-%m-%d %H:%M"),
        ])

        table.add_row(*row)

    return table


def create_history_table(versions: list[Any]) -> Table:
    table = Table(show_header=True, header_style="bold magenta")

    table.add_column("Version", justify="right", style="yellow")
    table.add_column("Created", style="cyan")
    table.add_column("Created By", style="blue")
    table.add_column("Value Preview", style="dim")

    for version in versions:
        # Preview first 50 chars of value
        preview = version.value[:50] + "..." if len(version.value) > 50 else version.value

        table.add_row(
            str(version.version),
            version.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            version.created_by or "unknown",
            preview,
        )

    return table


def print_panel(title: str, content: str, style: str = "blue") -> None:
    panel = Panel(content, title=title, border_style=style)
    console.print(panel)
