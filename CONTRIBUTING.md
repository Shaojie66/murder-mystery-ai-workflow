# Contributing to murder-wizard

Thank you for your interest in contributing.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Shaojie66/murder-mystery-ai-workflow.git
cd murder-mystery-ai-workflow

# Install in development mode
pip install -e .

# Run tests
pytest tests/ -v
```

## Project Structure

```
murder_wizard/
├── cli/               # CLI entry points and commands
│   ├── __init__.py   # Click CLI group
│   ├── commands.py    # Command implementations
│   ├── phase_runner.py # Stage execution logic
│   └── wizard_tui.py  # Interactive init wizard
├── llm/               # LLM adapter layer
│   └── client.py      # Claude / OpenAI adapters
├── print/             # PDF generation
│   └── pdf_gen.py     # reportlab-based PDF output
└── wizard/            # Core wizard logic
    ├── session.py     # Session persistence
    └── state_machine.py # Stage state machine
```

## Adding a New Stage

1. Add the stage enum to `Stage` in `state_machine.py`
2. Add `run_stage_N()` method to `PhaseRunner` in `phase_runner.py`
3. Add the `elif stage == N: runner.run_stage_N()` branch in `commands.py`
4. Update `show_status()` artifact list in `commands.py`
5. Add tests in `tests/`

## Code Style

- Python >= 3.10
- Type hints required for public methods
- Use `rich` for all CLI output
- Docstrings in Chinese for user-facing strings, English for internal

## Reporting Issues

Please report issues at:
https://github.com/Shaojie66/murder-mystery-ai-workflow/issues

Include:
- murder-wizard version (`murder-wizard --version`)
- Python version
- Full error traceback
- Steps to reproduce

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
