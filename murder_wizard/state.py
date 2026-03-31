"""Wizard state machine and user interaction."""

import click
import json
from pathlib import Path


class WizardState:
    STATES = ["idle", "type_select", "story_brief", "character_design", "plot_build", "asset_prompt", "output"]

    def __init__(self, project_name="my-murder-mystery"):
        self.project_name = project_name
        self.project_dir = Path.cwd() / project_name
        self.murder_type = None  # emotional / mechanical / deductive
        self.story_brief = {}
        self.characters = []
        self.plot = {}
        self.asset_prompts = {}
        self.current_state = "idle"

    def ask_type(self):
        """Ask user to select murder mystery type."""
        click.echo("Step 1/5: Choose your murder mystery type\n")
        click.echo("  1) Emotional (情感) - Focus on relationships and drama")
        click.echo("  2) Mechanical (机制) - Focus on game mechanics")
        click.echo("  3) Deductive (推理) - Focus on mystery solving\n")

        choice = click.prompt("Enter choice (1-3)", type=int, default=1)

        types = {1: "emotional", 2: "mechanical", 3: "deductive"}
        self.murder_type = types.get(choice, "emotional")
        self.current_state = "type_select"
        click.echo(f"\nSelected: {self.murder_type.capitalize()} murder mystery\n")

    def ask_story_brief(self):
        """Ask for story background."""
        click.echo("Step 2/5: Story Background\n")

        self.story_brief = {
            "theme": click.prompt("  Theme (e.g., ancient mansion, modern office)"),
            "setting": click.prompt("  Setting (e.g., 1920s Shanghai, near-future Tokyo)"),
            "tone": click.prompt("  Tone (e.g., dark, comedic, suspenseful)", default="suspenseful"),
            "core_conflict": click.prompt("  Core conflict (what's at stake)"),
        }
        self.current_state = "story_brief"

    def ask_characters(self):
        """Ask for character information."""
        click.echo("\nStep 3/5: Character Design (6 characters)\n")

        self.characters = []
        for i in range(1, 7):
            click.echo(f"  Character {i}:")
            char = {
                "name": click.prompt(f"    Name", default=f"Character{i}"),
                "role": click.prompt(f"    Role (e.g., detective, suspect)", default="suspect"),
                "personality": click.prompt(f"    Personality (e.g., cunning, naive)"),
                "secret": click.prompt(f"    One secret they hide"),
            }
            self.characters.append(char)
        self.current_state = "character_design"

    def ask_plot(self):
        """Ask for plot structure."""
        click.echo("\nStep 4/5: Plot Structure\n")

        self.plot = {
            "victim": click.prompt("  Who is the victim?"),
            "suspects": click.prompt("  How are suspects connected to victim?"),
            "key_events": click.prompt("  What are the 3 key events?"),
            "red_herrings": click.prompt("  What are the false clues (red herrings)?"),
        }
        self.current_state = "plot_build"

    def ask_asset_prompts(self):
        """Ask for asset generation preferences."""
        click.echo("\nStep 5/5: Visual Assets\n")

        self.asset_prompts = {
            "art_style": click.prompt("  Art style (e.g., Chinese ink painting, noir)", default="Chinese ink painting"),
            "mood": click.prompt("  Overall mood (e.g., dark, whimsical)", default="dark"),
        }
        self.current_state = "asset_prompt"

    def save(self):
        """Save project files to disk."""
        self.project_dir.mkdir(exist_ok=True)

        # Save session state
        session_file = self.project_dir / "murder-wizard-session.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump({
                "murder_type": self.murder_type,
                "story_brief": self.story_brief,
                "characters": self.characters,
                "plot": self.plot,
                "asset_prompts": self.asset_prompts,
            }, f, indent=2, ensure_ascii=False)

        # Save markdown files
        self._save_outline()
        self._save_characters()
        self._save_plot()
        self._save_asset_prompts()

        # Create materials dir
        (self.project_dir / "materials").mkdir(exist_ok=True)

    def _save_outline(self):
        """Save story outline."""
        content = f"""# {self.story_brief.get('theme', 'Murder Mystery')} - Story Outline

## Theme
{self.story_brief.get('theme', '')}

## Setting
{self.story_brief.get('setting', '')}

## Tone
{self.story_brief.get('tone', '')}

## Core Conflict
{self.story_brief.get('core_conflict', '')}
"""
        (self.project_dir / "outline.md").write_text(content, encoding="utf-8")

    def _save_characters(self):
        """Save character designs."""
        lines = ["# Characters\n"]
        for i, char in enumerate(self.characters, 1):
            lines.append(f"""
## Character {i}: {char.get('name', f'Character{i}')}

- **Role**: {char.get('role', '')}
- **Personality**: {char.get('personality', '')}
- **Secret**: {char.get('secret', '')}
""")
        (self.project_dir / "characters.md").write_text("".join(lines), encoding="utf-8")

    def _save_plot(self):
        """Save plot structure."""
        content = f"""# Plot Structure

## Victim
{self.plot.get('victim', '')}

## Suspects
{self.plot.get('suspects', '')}

## Key Events
{self.plot.get('key_events', '')}

## Red Herrings
{self.plot.get('red_herrings', '')}
"""
        (self.project_dir / "plot.md").write_text(content, encoding="utf-8")

    def _save_asset_prompts(self):
        """Save image generation prompts."""
        lines = [f"""# Image Prompts

## Art Style
{self.asset_prompts.get('art_style', '')}

## Mood
{self.asset_prompts.get('mood', '')}

## Character Prompts
"""]
        for i, char in enumerate(self.characters, 1):
            prompt = f"A {self.asset_prompts.get('art_style', 'Chinese ink painting')} portrait of {char.get('name', f'Character{i}')}, {char.get('personality', '')} personality, {self.asset_prompts.get('mood', '')} mood"
            lines.append(f"\n### {char.get('name', f'Character{i}')}\n{prompt}\n")
        (self.project_dir / "image-prompts.md").write_text("".join(lines), encoding="utf-8")
