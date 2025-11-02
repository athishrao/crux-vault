import typer

app = typer.Typer(
    help="Unified secrets, configs, and feature flags management",
    add_completion=False,
)
dev_app = typer.Typer(help="Development mode commands")
app.add_typer(dev_app, name="dev")

def main() -> None:
    app()
