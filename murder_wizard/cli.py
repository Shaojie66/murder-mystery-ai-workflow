"""Click CLI entry point for murder-wizard."""

import click
import os
from .state import WizardState

API_KEY = os.environ.get("MURDER_WIZARD_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")


@click.group()
def cli():
    """Murder Wizard - Create murder mystery games with AI."""
    pass


@cli.command()
def init():
    """Start a new murder mystery project."""
    if not API_KEY:
        click.echo("Error: MURDER_WIZARD_API_KEY or ANTHROPIC_API_KEY not set.")
        click.echo("Set it with: export MURDER_WIZARD_API_KEY=your-key")
        return

    click.echo("\n=== Murder Mystery Wizard ===")
    click.echo("Let's create your murder mystery step by step.\n")

    state = WizardState()
    state.ask_type()
    state.ask_story_brief()
    state.ask_characters()
    state.ask_plot()
    state.ask_asset_prompts()

    click.echo("\nGenerating project files...")
    state.save()

    click.echo("\nDone! Your project is ready at:")
    click.echo(f"  {state.project_dir}/")
    click.echo("\nFiles created:")
    for f in ["outline.md", "characters.md", "plot.md", "image-prompts.md"]:
        click.echo(f"  - {f}")


if __name__ == "__main__":
    cli()
