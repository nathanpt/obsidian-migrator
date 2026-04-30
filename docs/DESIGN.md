# Obsidian Migrator - Design Document

## Problem

I use Obsidian at home with a heavily customized setup -- 14 community plugins, custom fonts, CSS snippets, a specific theme, and various settings tweaks. Manually replicating this setup on another machine (e.g., at work) is tedious and error-prone. I need a script I can host on GitHub and run on any machine to bootstrap an identical Obsidian configuration.

## Goals

1. **One-command setup** -- Run a single script on a fresh machine and get my exact Obsidian config.
2. **Hosted on GitHub** -- The script and config files live in a repo. No local-only setup steps.
3. **Idempotent** -- Safe to re-run. Overwrites config but doesn't destroy vault content.
4. **Cross-platform** -- Should work on Windows, macOS, and Linux (the machines I use).

## Current Vault Profile

Source vault: `Y:\Nathan\Documents\Brain`

### Core Settings

| File | Purpose |
|------|---------|
| `app.json` | Editor behavior (link format, attachment folder, spellcheck, etc.) |
| `core-plugins.json` | Which built-in Obsidian plugins are enabled/disabled |
| `appearance.json` | Theme (Minimal), fonts (iA Writer Quattro S, Geist Mono), font size |
| `hotkeys.json` | Custom keyboard shortcuts |
| `workspace.json` | Open tabs / UI layout (excluded from migration -- machine-specific) |
| `graph.json` | Graph view settings |
| `backlink.json` | Backlink settings |
| `daily-notes.json` | Daily note configuration |
| `page-preview.json` | Page preview behavior |
| `types.json` | File type settings |

### Community Plugins (14)

| Plugin | Has data.json | Notes |
|--------|:-------------:|-------|
| mermaid-tools | Likely | Mermaid diagram helpers |
| obsidian-icon-folder | Likely | Custom folder icons |
| omnisearch | Likely | Enhanced search |
| obsidian-mind-map | Likely | Mind map visualization |
| make-md | Likely | Make.md features |
| obsidian-minimal-settings | Likely | Minimal theme settings |
| obsidian-book-search-plugin | Likely | Book search |
| dataview | Yes | Query engine -- confirmed `data.json` |
| obsidian-style-settings | Likely | Style adjustments |
| obsidian-hider | Yes | UI element hiding -- confirmed `data.json` |
| obsidian-outliner | Likely | Outliner behavior |
| terminal | Likely | Embedded terminal |
| tasknotes | Likely | Task management |
| claudian | Likely | AI assistant integration |

### Themes (5 installed, Minimal active)

- Atom
- Minimal (active)
- Obsidian gruvbox
- Obsidian Nord
- Typewriter

### CSS Snippets (2)

- `bullet-styles.css`
- `config.css`

### Other Folders

- `icons/` -- Icon folder plugin assets (empty at time of audit)
- `terminal/` -- Terminal plugin config

## Architecture

### Repository Structure

```
obsidian-migrator/
├── docs/
│   └── DESIGN.md
├── config/                          # All config files tracked here
│   ├── app.json
│   ├── appearance.json
│   ├── core-plugins.json
│   ├── community-plugins.json
│   ├── hotkeys.json
│   ├── graph.json
│   ├── backlink.json
│   ├── daily-notes.json
│   ├── page-preview.json
│   ├── types.json
│   ├── snippets/
│   │   ├── bullet-styles.css
│   │   └── config.css
│   └── plugins/                     # Per-plugin data.json files
│       ├── dataview.json
│       ├── obsidian-hider.json
│       ├── obsidian-icon-folder.json
│       ├── omnisearch.json
│       ├── obsidian-mind-map.json
│       ├── make-md.json
│       ├── obsidian-minimal-settings.json
│       ├── obsidian-book-search-plugin.json
│       ├── obsidian-style-settings.json
│       ├── obsidian-outliner.json
│       ├── terminal.json
│       ├── tasknotes.json
│       ├── claudian.json
│       └── mermaid-tools.json
├── themes/
│   ├── Atom/
│   ├── Minimal/
│   ├── Obsidian gruvbox/
│   ├── Obsidian Nord/
│   └── Typewriter/
├── migrate.ps1                      # Windows PowerShell script
├── migrate.sh                       # Bash script (macOS/Linux)
└── README.md
```

### Migration Script Behavior

```
migrate [--vault <path>] [--dry-run]
```

1. **Validate** -- Check that the target vault path exists (or create it). If `.obsidian` doesn't exist, initialize it.
2. **Back up** -- If `.obsidian` already exists, back it up to `.obsidian.backup.<timestamp>`.
3. **Copy core config** -- Overwrite all JSON config files from `config/` into `.obsidian/`.
4. **Copy CSS snippets** -- Mirror `config/snippets/` into `.obsidian/snippets/`.
5. **Copy themes** -- Mirror `themes/` into `.obsidian/themes/`.
6. **Install community plugins** -- For each plugin in `community-plugins.json`:
   - Create `.obsidian/plugins/<name>/` if it doesn't exist.
   - Copy the plugin's `data.json` from `config/plugins/<name>.json`.
   - **Download `main.js`, `manifest.json`, and `styles.css`** from the Obsidian community plugin GitHub releases (using the plugin's repo URL from the Obsidian community plugins list). This avoids tracking large JS blobs in the repo.
7. **Exclusions** -- Do NOT copy `workspace.json` (machine-specific tabs/layout).

### Plugin Source Resolution

Community plugins are distributed via GitHub. The script will:

1. Fetch the community plugins manifest from `https://raw.githubusercontent.com/obsidianmd/obsidian-releases/master/community-plugins.json`.
2. Look up each plugin ID to get its GitHub repo URL.
3. Download the latest release assets (`main.js`, `manifest.json`, `styles.css`) from the repo.

This keeps the repo lightweight (no large JS files) and ensures plugins are always up to date.

### Font Handling

Custom fonts (iA Writer Quattro S, Geist Mono) are referenced in `appearance.json` but cannot be installed via script alone. The script will:

- Detect if fonts are installed.
- Print a warning with download links if they are missing.
- Optionally accept a `--fonts-dir` flag to install fonts from a bundled directory.

## Usage

### First-time setup on a new machine

```bash
# Clone the repo
git clone https://github.com/<user>/obsidian-migrator.git
cd obsidian-migrator

# Run the migration (point at your vault)
./migrate.sh --vault ~/Documents/MyVault

# Or on Windows PowerShell
.\migrate.ps1 -Vault "Y:\Nathan\Documents\Brain"
```

### Updating config after making changes at home

```bash
# Re-export your current config into the repo
./migrate.sh --export --vault ~/Documents/MyVault
git add . && git commit -m "update config"
git push
```

## Open Questions

- [ ] Should `--export` mode be included in v1, or just the apply direction?
- [ ] Should themes be tracked in the repo or also downloaded on-the-fly?
- [ ] How to handle plugins that store binary assets (e.g., icon folder images)?
- [ ] Should we prompt the user to restart Obsidian after migration?
