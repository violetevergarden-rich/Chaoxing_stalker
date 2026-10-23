# Repository Guide

This file gives coding agents and contributors the project-specific context needed to work in this repository.

## Project overview

ChaoXing Stalker checks configured 超星学习通 accounts for unsubmitted assignments that have not passed their deadlines. A run checks every configured user once, prints or sends the full current assignment list, updates optional desktop notes, and exits. Scheduling is handled outside the application.

## Common commands

```bash
# Install dependencies
pip install -r requirements.txt

# Generate the default config template
python3 -m chaoxing_stalker --init-config

# Check once with stalker_config.json
python3 -m chaoxing_stalker

# Use a different config file
python3 -m chaoxing_stalker --config path/to/config.json

# Run the unit test suite
python3 -m unittest discover -v
```

The optional scraper compatibility entry point is `python3 -m chaoxing_stalker.compat <username> <password>`. Avoid putting real credentials in shell history.

## Code layout

```text
chaoxing_stalker/
  __main__.py             Module CLI (`python3 -m chaoxing_stalker`)
  app.py                  Application setup and one-run orchestration
  config.py               Config template, loading, and validation
  assignment_types.py     Typed course and assignment records
  message_formatter.py    Sorted notification formatting
  retry.py                Exponential retry helper
  sticky_notes.py         Cross-platform desktop note writer
  compat.py               ChaoXingStalker compatibility class and CLI
  chaoxing/               Authentication, HTTP client, and HTML parsing
  notifiers/              Console, email, and ServerChan delivery
  services/               Assignment check and notification flow
tests/                    Unit tests
```

Keep application modules inside `chaoxing_stalker/`; the repository root should not contain Python modules. Use package-qualified imports such as `from chaoxing_stalker.config import ...` so the application can be launched with `python -m`.

## Behavior and boundaries

- Each run fetches the full list of unsubmitted assignments. The service sorts known deadlines first in ascending order; unknown deadlines appear last. Past-deadline filtering remains in the ChaoXing parsing/client flow.
- Assignment state is not persisted between runs. Do not add change-detection state unless the product requirement changes.
- The parser keeps remaining-time data for filtering but user-facing output uses the fixed deadline date, or `未知` when the page has no explicit date.
- Sticky notes are opt-in per user. They are written under the user's desktop folder, in the configured `folder_name` (default `学习通作业`), using a two-digit order prefix and the assignment title. Repeated checks overwrite matching names; generated notes no longer in the current list are removed.
- `notify_when_empty` controls notifications for empty lists. `notify_on_error` controls notifications after a fetch error.

## Credentials and local files

`stalker_config.json` may contain real account passwords and notification secrets. It is ignored by Git; never include its values in logs, commits, or example snippets. GitHub Actions reads the full configuration from the `CONFIG_JSON` repository secret. The AES login key is a platform constant, not a user credential.

## Implementation notes

- `chaoxing/` contains platform-specific authentication and parsing code; platform HTML and endpoints can change.
- Notifiers implement `Notifier.send(subject, message) -> bool`. Register new channels in `notifiers/factory.py` and add tests for their construction and behavior.
- Keep OS-specific desktop path handling in `sticky_notes.py` and preserve both XDG desktop discovery on Linux and Windows desktop handling.
