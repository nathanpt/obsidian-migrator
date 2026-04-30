#!/usr/bin/env python3
"""Obsidian Migrator - Apply or export your Obsidian vault configuration.

Usage:
    python migrate.py apply  --vault <path> [--dry-run]
    python migrate.py export --vault <path> [--dry-run]
"""

import argparse
import json
import shutil
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR / "config"
SNIPPETS_DIR = CONFIG_DIR / "snippets"
PLUGINS_DIR = CONFIG_DIR / "plugins"

COMMUNITY_PLUGINS_URL = (
    "https://raw.githubusercontent.com/obsidianmd/obsidian-releases"
    "/master/community-plugins.json"
)
COMMUNITY_THEMES_URL = (
    "https://raw.githubusercontent.com/obsidianmd/obsidian-releases"
    "/master/community-css-themes.json"
)

CORE_CONFIG_FILES = [
    "app.json",
    "appearance.json",
    "core-plugins.json",
    "community-plugins.json",
    "hotkeys.json",
    "graph.json",
    "backlink.json",
    "daily-notes.json",
    "page-preview.json",
    "types.json",
]

EXCLUDED_CONFIG_FILES = {"workspace.json"}

REQUIRED_FONTS = {
    "iA Writer Quattro S": "https://ia.net/writer/fonts",
    "Geist Mono": "https://github.com/vercel/geist-font",
}

SENSITIVE_KEY_PATTERNS = [
    "apikey", "api_key", "apiauthtoken", "apitoken",
    "secret", "clientsecret", "client_secret",
    "password",
    "accesstoken", "access_token",
    "licensekey", "license_key", "lemonsqueezylicensekey",
    "googleoauthclientid", "googleoauthclientsecret",
    "microsoftoauthclientid", "microsoftoauthclientsecret",
    "bearertoken", "authtoken", "credentials",
    "naverclientsecret", "naverclientid",
]


def redact_json(data) -> tuple:
    """Recursively redact sensitive values in a JSON structure.

    Returns (redacted_data, list_of_redacted_keys).
    """
    redacted_keys = []
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(pattern in key_lower for pattern in SENSITIVE_KEY_PATTERNS):
                if value:  # only flag if non-empty
                    redacted_keys.append(key)
                result[key] = ""
            else:
                result[key], child_keys = redact_json(value)
                redacted_keys.extend(child_keys)
        return result, redacted_keys
    elif isinstance(data, list):
        result = []
        for item in data:
            redacted_item, child_keys = redact_json(item)
            result.append(redacted_item)
            redacted_keys.extend(child_keys)
        return result, redacted_keys
    return data, redacted_keys


def log(msg: str) -> None:
    print(f"  {msg}")


def download_json(url: str) -> list | dict:
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode())


def download_file(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url) as resp:
        dest.write_bytes(resp.read())


def resolve_plugin_repo(plugin_id: str) -> str | None:
    """Look up a plugin ID in the community plugins registry and return 'owner/repo'."""
    try:
        plugins = download_json(COMMUNITY_PLUGINS_URL)
    except urllib.error.URLError as e:
        print(f"  ERROR: Failed to fetch community plugins list: {e}")
        return None
    for entry in plugins:
        if entry.get("id") == plugin_id:
            return entry.get("repo")
    return None


def resolve_theme_repo(theme_name: str) -> str | None:
    """Look up a theme name in the community themes registry and return 'owner/repo'."""
    try:
        themes = download_json(COMMUNITY_THEMES_URL)
    except urllib.error.URLError as e:
        print(f"  ERROR: Failed to fetch community themes list: {e}")
        return None
    for entry in themes:
        if entry.get("name") == theme_name:
            return entry.get("repo")
    return None


def backup_obsidian(obsidian_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = obsidian_dir.parent / f".obsidian.backup.{timestamp}"
    log(f"Backing up .obsidian to {backup}")
    shutil.copytree(obsidian_dir, backup)
    return backup


def apply_config(vault_path: Path, dry_run: bool = False) -> None:
    obsidian_dir = vault_path / ".obsidian"

    if not vault_path.exists():
        print(f"ERROR: Vault directory not found: {vault_path}")
        sys.exit(1)

    if not obsidian_dir.exists():
        if dry_run:
            log(f"Would create .obsidian directory: {obsidian_dir}")
        else:
            log(f"Creating .obsidian directory: {obsidian_dir}")
            obsidian_dir.mkdir()
    else:
        if dry_run:
            log(f"Would back up existing .obsidian")
        else:
            backup_obsidian(obsidian_dir)

    # 1. Core config files
    log("Copying core config files...")
    for filename in CORE_CONFIG_FILES:
        src = CONFIG_DIR / filename
        dst = obsidian_dir / filename
        if src.exists():
            if dry_run:
                log(f"  Would copy {filename}")
            else:
                shutil.copy2(src, dst)
                log(f"  Copied {filename}")
        else:
            log(f"  SKIP {filename} (not found in config/)")

    # 2. CSS snippets
    log("Copying CSS snippets...")
    snippets_dst = obsidian_dir / "snippets"
    if SNIPPETS_DIR.exists():
        if not dry_run:
            snippets_dst.mkdir(exist_ok=True)
        for src in SNIPPETS_DIR.iterdir():
            if src.is_file():
                if dry_run:
                    log(f"  Would copy snippet {src.name}")
                else:
                    shutil.copy2(src, snippets_dst / src.name)
                    log(f"  Copied snippet {src.name}")

    # 3. Themes
    log("Downloading themes...")
    appearance_file = CONFIG_DIR / "appearance.json"
    active_theme = None
    if appearance_file.exists():
        with open(appearance_file) as f:
            appearance = json.load(f)
            active_theme = appearance.get("cssTheme")

    if active_theme:
        themes_dst = obsidian_dir / "themes"
        if not dry_run:
            themes_dst.mkdir(exist_ok=True)

        theme_names = [active_theme]
        # Also check if there are other themes in the vault already; we just ensure the active one
        log(f"  Active theme: {active_theme}")
        repo = resolve_theme_repo(active_theme)
        if repo:
            theme_dir = themes_dst / active_theme
            if not dry_run:
                theme_dir.mkdir(exist_ok=True)
            base = f"https://raw.githubusercontent.com/{repo}/main"
            for asset in ["theme.css", "manifest.json"]:
                url = f"{base}/{asset}"
                dest = theme_dir / asset
                if dry_run:
                    log(f"  Would download {asset} for theme '{active_theme}'")
                else:
                    try:
                        download_file(url, dest)
                        log(f"  Downloaded {asset} for theme '{active_theme}'")
                    except urllib.error.HTTPError:
                        # Try master branch
                        url = f"https://raw.githubusercontent.com/{repo}/master/{asset}"
                        try:
                            download_file(url, dest)
                            log(f"  Downloaded {asset} for theme '{active_theme}' (master)")
                        except urllib.error.HTTPError:
                            log(f"  WARNING: Could not download {asset} for theme '{active_theme}'")
        else:
            log(f"  WARNING: Could not find theme '{active_theme}' in community registry")

    # 4. Community plugins
    log("Installing community plugins...")
    cp_file = CONFIG_DIR / "community-plugins.json"
    plugin_ids = []
    if cp_file.exists():
        with open(cp_file) as f:
            plugin_ids = json.load(f)

    for plugin_id in plugin_ids:
        plugin_dst = obsidian_dir / "plugins" / plugin_id
        if dry_run:
            log(f"  Would install plugin: {plugin_id}")
        else:
            plugin_dst.mkdir(parents=True, exist_ok=True)

        # Download plugin assets from GitHub
        repo = resolve_plugin_repo(plugin_id)
        if repo:
            base_url = f"https://github.com/{repo}/releases/latest/download"
            required_assets = ["main.js", "manifest.json"]
            optional_assets = ["styles.css"]
            for asset in required_assets + optional_assets:
                url = f"{base_url}/{asset}"
                dest = plugin_dst / asset
                is_optional = asset in optional_assets
                if dry_run:
                    log(f"    Would download {asset}")
                else:
                    downloaded = False
                    # Try GitHub release
                    try:
                        download_file(url, dest)
                        log(f"    Downloaded {asset}")
                        downloaded = True
                    except urllib.error.HTTPError:
                        pass
                    # Fallback: raw GitHub source
                    if not downloaded:
                        for branch in ["main", "master"]:
                            try:
                                raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{asset}"
                                download_file(raw_url, dest)
                                log(f"    Downloaded {asset} (from {branch})")
                                downloaded = True
                                break
                            except urllib.error.HTTPError:
                                continue
                    if not downloaded and not is_optional:
                        log(f"    WARNING: Could not download {asset}")
        else:
            log(f"  WARNING: Could not find plugin '{plugin_id}' in community registry")

        # Copy plugin data.json from config
        plugin_data_src = PLUGINS_DIR / f"{plugin_id}.json"
        if plugin_data_src.exists():
            if dry_run:
                log(f"    Would copy data.json for {plugin_id}")
            else:
                shutil.copy2(plugin_data_src, plugin_dst / "data.json")
                log(f"    Copied data.json for {plugin_id}")

    # 5. Font check
    log("Checking fonts...")
    for font_name, url in REQUIRED_FONTS.items():
        log(f"  Font '{font_name}' - ensure it is installed on this system")
        log(f"    Download: {url}")

    print()
    if dry_run:
        print("Dry run complete. No changes were made.")
    else:
        print("Migration complete! Please restart Obsidian to apply changes.")


def export_config(vault_path: Path, dry_run: bool = False, no_redact: bool = False) -> None:
    obsidian_dir = vault_path / ".obsidian"

    if not obsidian_dir.exists():
        print(f"ERROR: .obsidian directory not found: {vault_path / '.obsidian'}")
        sys.exit(1)

    # 1. Core config files
    log("Exporting core config files...")
    for filename in CORE_CONFIG_FILES:
        src = obsidian_dir / filename
        dst = CONFIG_DIR / filename
        if src.exists():
            if dry_run:
                log(f"  Would copy {filename}")
            else:
                shutil.copy2(src, dst)
                log(f"  Exported {filename}")

    # 2. CSS snippets
    log("Exporting CSS snippets...")
    vault_snippets = obsidian_dir / "snippets"
    if vault_snippets.exists():
        if not dry_run:
            SNIPPETS_DIR.mkdir(exist_ok=True)
        for src in vault_snippets.iterdir():
            if src.is_file():
                if dry_run:
                    log(f"  Would copy snippet {src.name}")
                else:
                    shutil.copy2(src, SNIPPETS_DIR / src.name)
                    log(f"  Exported snippet {src.name}")

    # 3. Plugin data.json files
    log("Exporting plugin settings...")
    vault_plugins = obsidian_dir / "plugins"
    if vault_plugins.exists():
        if not dry_run:
            PLUGINS_DIR.mkdir(exist_ok=True)
        for plugin_dir in vault_plugins.iterdir():
            if plugin_dir.is_dir():
                data_file = plugin_dir / "data.json"
                dst = PLUGINS_DIR / f"{plugin_dir.name}.json"
                if data_file.exists():
                    if dry_run:
                        log(f"  Would export {plugin_dir.name}/data.json")
                    else:
                        with open(data_file) as f:
                            data = json.load(f)
                        if not no_redact:
                            data, redacted = redact_json(data)
                            if redacted:
                                log(f"  REDACTED from {plugin_dir.name}: {', '.join(redacted)}")
                        with open(dst, "w") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        log(f"  Exported {plugin_dir.name}/data.json")

    print()
    if dry_run:
        print("Dry run complete. No changes were made.")
    else:
        print("Export complete! You can now commit the config/ directory.")
        print("  git add config/ && git commit -m 'update config'")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Obsidian Migrator - Apply or export your Obsidian vault configuration."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for cmd in ["apply", "export"]:
        p = subparsers.add_parser(cmd, help=f"{cmd.capitalize()} configuration")
        p.add_argument("--vault", required=True, type=Path, help="Path to Obsidian vault")
        p.add_argument("--dry-run", action="store_true", help="Preview without making changes")

    export_parser = subparsers.choices["export"]
    export_parser.add_argument("--no-redact", action="store_true", help="Skip sensitive data redaction")

    args = parser.parse_args()
    vault = args.vault.resolve()

    print(f"Obsidian Migrator - {args.command.upper()}")
    print(f"Vault: {vault}")
    print(f"Config: {CONFIG_DIR}")
    print()

    if args.command == "apply":
        apply_config(vault, dry_run=args.dry_run)
    elif args.command == "export":
        export_config(vault, dry_run=args.dry_run, no_redact=args.no_redact)


if __name__ == "__main__":
    main()
