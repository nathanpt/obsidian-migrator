# Obsidian Migrator

> **Note:** This is a personal tool for replicating my Obsidian setup across machines. The config files here are my own preferences -- they won't be useful to anyone else directly. If you're looking for a general-purpose Obsidian config migration tool, feel free to fork and swap out the `config/` directory with your own.

## What it does

A single Python script that applies or exports an Obsidian vault configuration. Hosted on GitHub so I can clone and run it at work (or any other machine) to get my exact Obsidian setup in one command.

- Applies core settings, community plugins, themes, CSS snippets, and plugin settings
- Downloads plugin JS and theme CSS from GitHub at runtime (no large binaries in the repo)
- Backs up existing `.obsidian` before making changes
- Supports exporting config changes back to the repo for committing

## My setup

- **Theme:** Minimal
- **Fonts:** iA Writer Quattro S, Geist Mono
- **14 community plugins:** Dataview, TaskNotes, Omnisearch, Terminal, Claudian, and more
- **2 CSS snippets:** bullet styles, custom callouts/columns

## Usage

### Apply config to a vault

```bash
git clone https://github.com/nathanpt/obsidian-migrator.git
cd obsidian-migrator

# Preview what would change
python migrate.py apply --vault /path/to/vault --dry-run

# Apply
python migrate.py apply --vault /path/to/vault
```

### Export config from a vault

After making changes at home, export back to the repo:

```bash
python migrate.py export --vault /path/to/vault
git add config/ && git commit -m "update config" && git push
```

## Requirements

- Python 3.10+
- Internet connection (to download plugins and themes from GitHub)
- No pip dependencies -- stdlib only

## Notes

- `workspace.json` (open tabs, UI layout) is excluded since it's machine-specific
- `claudian` is not in the community plugins registry and must be installed manually
- Fonts are not installed automatically -- the script will warn if they're missing

## Screenshots

<img width="2560" height="1380" alt="image" src="https://github.com/user-attachments/assets/671f3f85-0fac-433c-867f-0a57e8ea7a2a" />
<img width="2560" height="1380" alt="image" src="https://github.com/user-attachments/assets/7b90a356-998e-47b6-91c0-868cdfcec892" />

