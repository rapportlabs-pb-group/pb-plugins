#!/usr/bin/env python3
"""
PB Marketplace Publisher

Publishes a plugin to the rapportlabs-pb-group/pb-plugins marketplace.

Usage:
    python3 publish_to_pb.py <plugin-path>
    python3 publish_to_pb.py ./my-plugin --dry-run
    python3 publish_to_pb.py ./my-plugin --version-bump patch

Flow:
    prerequisites -> secrets gate -> validate -> clone -> copy -> register -> validate -> PR
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_MARKETPLACE_REPO = "rapportlabs-pb-group/pb-plugins"
MARKETPLACE_JSON_PATH = ".claude-plugin/marketplace.json"
PLUGINS_DIR = "plugins"

RSYNC_EXCLUDES = [
    ".git", ".env*", "credentials*", "secrets*",
    "*.key", "*.pem", "*.p12", "*.pfx",
    "service-account*.json", "node_modules", "__pycache__",
    ".DS_Store", "CLAUDE.md", ".plugin-state", "*.pyc",
    ".venv", "venv",
]

SECRETS_SCRIPT = Path(__file__).parent / "check_secrets.py"


def run(cmd: list[str], capture: bool = True, check: bool = True, cwd: Path | str | None = None) -> subprocess.CompletedProcess:
    """Run a shell command."""
    return subprocess.run(cmd, capture_output=capture, text=True, check=check, cwd=cwd)


def check_prerequisites() -> list[str]:
    """Verify required tools are installed and authenticated."""
    errors = []

    for tool in ["gh", "git", "jq", "rsync"]:
        if not shutil.which(tool):
            errors.append(f"'{tool}' not found. Install with: brew install {tool}")

    if not errors:
        result = run(["gh", "auth", "status"], check=False)
        if result.returncode != 0:
            errors.append("GitHub CLI not authenticated. Run: gh auth login")

    return errors


def get_github_username() -> str:
    """Get the authenticated GitHub username."""
    result = run(["gh", "api", "/user", "--jq", ".login"], check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def run_secrets_check(plugin_path: Path) -> bool:
    """Run secrets scanner. Returns True if passed."""
    print("\n--- Secrets Scan (HARD GATE) ---")

    if not SECRETS_SCRIPT.exists():
        print(f"Error: Secrets scanner not found at {SECRETS_SCRIPT}")
        return False

    result = run(
        [sys.executable, str(SECRETS_SCRIPT), str(plugin_path)],
        check=False,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print("BLOCKED: Secrets detected. Fix issues and re-run.")
        return False

    print("Secrets scan passed.")
    return True


def validate_plugin_structure(plugin_path: Path) -> tuple[bool, dict]:
    """Validate plugin has required structure. Returns (valid, plugin_json)."""
    plugin_json_path = plugin_path / ".claude-plugin" / "plugin.json"

    if not plugin_json_path.exists():
        print(f"Error: {plugin_json_path} not found")
        return False, {}

    try:
        data = json.loads(plugin_json_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in plugin.json: {e}")
        return False, {}

    name = data.get("name", "")
    if not name:
        print("Error: 'name' field missing in plugin.json")
        return False, {}

    if name != name.lower() or " " in name:
        print(f"Error: Plugin name '{name}' must be lowercase kebab-case")
        return False, {}

    if not data.get("version"):
        print("Error: 'version' field missing in plugin.json")
        return False, {}

    if not data.get("description"):
        print("Error: 'description' field missing in plugin.json")
        return False, {}

    # Check author (REQUIRED for PB marketplace)
    author = data.get("author", {})
    author_name = author.get("name", "") if isinstance(author, dict) else ""
    if not author_name:
        print("Error: 'author.name' field missing in plugin.json (required for PB marketplace)")
        print("  Add: \"author\": {\"name\": \"your-name\"}")
        return False, {}

    # Check README.md exists
    if not (plugin_path / "README.md").exists():
        print("Error: README.md not found (required for PB marketplace)")
        return False, {}

    # Check at least one skill or command exists
    skills_dir = plugin_path / "skills"
    commands_dir = plugin_path / "commands"
    has_skills = skills_dir.exists() and any(skills_dir.rglob("SKILL.md"))
    has_commands = commands_dir.exists() and any(commands_dir.glob("*.md"))
    if not has_skills and not has_commands:
        print("Error: No skills or commands found (need at least one)")
        return False, {}

    return True, data


def bump_version(plugin_path: Path, bump_type: str) -> str:
    """Bump version in plugin.json. Returns new version."""
    plugin_json_path = plugin_path / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json_path.read_text())
    current = data.get("version", "1.0.0")

    parts = current.split(".")
    if len(parts) != 3:
        parts = ["1", "0", "0"]

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    data["version"] = new_version
    plugin_json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    print(f"Version bumped: {current} -> {new_version}")
    return new_version


def detect_access_level(marketplace_repo: str) -> str:
    """Detect if user has direct push access or needs to fork."""
    try:
        result = run(["gh", "api", f"/repos/{marketplace_repo}", "--jq", ".permissions.push"], check=False)
        if result.returncode == 0 and result.stdout.strip() == "true":
            return "direct"
    except Exception:
        pass

    return "fork"


def clone_repo(temp_dir: Path, access: str, marketplace_repo: str) -> Path:
    """Clone the marketplace repo (or fork). Returns repo path."""
    repo_name = marketplace_repo.split("/")[-1]
    repo_path = temp_dir / repo_name

    if access == "fork":
        print("Forking repository (external contributor)...")
        # Fork without cloning (avoid polluting CWD)
        run(["gh", "repo", "fork", marketplace_repo, "--clone=false"], check=False)
        # Get username to construct fork URL
        result = run(["gh", "api", "/user", "--jq", ".login"], check=False)
        username = result.stdout.strip()
        if not username:
            print("Error: Could not determine GitHub username")
            sys.exit(1)
        # Clone fork into temp directory
        run(["git", "clone", f"https://github.com/{username}/{repo_name}.git", str(repo_path)])
        run(["git", "-C", str(repo_path), "remote", "add", "upstream",
             f"https://github.com/{marketplace_repo}.git"], check=False)
    else:
        print("Cloning marketplace repository...")
        run(["gh", "repo", "clone", marketplace_repo, str(repo_path)])

    return repo_path


def copy_plugin(plugin_path: Path, repo_path: Path, plugin_name: str) -> None:
    """Copy plugin files to marketplace repo using rsync."""
    target = repo_path / PLUGINS_DIR / plugin_name
    target.mkdir(parents=True, exist_ok=True)

    rsync_cmd = ["rsync", "-av"]
    for pattern in RSYNC_EXCLUDES:
        rsync_cmd.extend(["--exclude", pattern])
    rsync_cmd.extend([str(plugin_path) + "/", str(target) + "/"])

    run(rsync_cmd)
    print(f"Plugin copied to {PLUGINS_DIR}/{plugin_name}/")


def update_marketplace_json(repo_path: Path, plugin_data: dict, github_username: str = "") -> None:
    """Add or update plugin entry in marketplace.json."""
    mp_path = repo_path / MARKETPLACE_JSON_PATH
    name = plugin_data["name"]

    if mp_path.exists():
        mp_data = json.loads(mp_path.read_text())
    else:
        mp_data = {"name": "pb-plugins", "owner": {"name": "rapportlabs-pb-group"}, "plugins": []}

    # Check for existing entry
    existing_idx = None
    for i, p in enumerate(mp_data.get("plugins", [])):
        if isinstance(p, dict) and p.get("name") == name:
            existing_idx = i
            break

    from datetime import date
    entry = {
        "name": name,
        "source": f"./plugins/{name}",
        "description": plugin_data.get("description", ""),
        "version": plugin_data.get("version", "1.0.0"),
        "author": plugin_data.get("author", {"name": "Unknown"}),
        "keywords": plugin_data.get("keywords", []),
        "published_by": github_username,
        "published_at": date.today().isoformat(),
    }

    if existing_idx is not None:
        mp_data["plugins"][existing_idx] = entry
        print(f"Updated existing entry for '{name}' (by @{github_username})")
    else:
        mp_data.setdefault("plugins", []).append(entry)
        print(f"Added new entry for '{name}' (by @{github_username})")

    mp_path.write_text(json.dumps(mp_data, indent=2, ensure_ascii=False) + "\n")


def update_readme_plugin_table(repo_path: Path) -> None:
    """Update the plugin list table in the marketplace README.md from marketplace.json."""
    readme_path = repo_path / "README.md"
    mp_path = repo_path / MARKETPLACE_JSON_PATH

    if not readme_path.exists() or not mp_path.exists():
        print("  Skipped: README.md or marketplace.json not found")
        return

    mp_data = json.loads(mp_path.read_text())
    plugins = mp_data.get("plugins", [])
    if not plugins:
        return

    # Build new table with author column
    header = "| 플러그인 | 설명 | 버전 | 작성자 | 배포자 | 배포일 |\n|---------|------|-----|--------|--------|--------|"
    rows = []
    for p in plugins:
        name = p.get("name", "")
        desc = p.get("description", "")
        ver = p.get("version", "")
        author = p.get("author", {})
        author_name = author.get("name", "") if isinstance(author, dict) else str(author)
        published_by = p.get("published_by", "")
        published_at = p.get("published_at", "")
        gh_link = f"@{published_by}" if published_by else ""
        rows.append(f"| {name} | {desc} | {ver} | {author_name} | {gh_link} | {published_at} |")
    new_table = header + "\n" + "\n".join(rows)

    readme = readme_path.read_text()

    # Find and replace the existing table after "## 플러그인 목록"
    import re
    pattern = r"(## 플러그인 목록\s*\n)(\|.+\|[\s\S]*?)(\n##|\n\Z|\Z)"
    match = re.search(pattern, readme)
    if match:
        replacement = match.group(1) + "\n" + new_table + "\n" + (match.group(3) if match.group(3).startswith("\n##") else match.group(3))
        readme = readme[:match.start()] + replacement + readme[match.end():]
        readme_path.write_text(readme)
        print(f"  README.md plugin table updated ({len(plugins)} plugins)")
    else:
        print("  Skipped: Could not find '## 플러그인 목록' section in README.md")


def ensure_changelog(plugin_path: Path, plugin_name: str, version: str, description: str) -> None:
    """Create or update CHANGELOG.md in the plugin directory."""
    changelog_path = plugin_path / "CHANGELOG.md"
    from datetime import date
    today = date.today().isoformat()
    entry = f"\n## [{version}] - {today}\n\n- {description or 'Update'}\n"

    if changelog_path.exists():
        content = changelog_path.read_text()
        # Insert after the first heading line
        lines = content.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('# '):
                insert_idx = i + 1
                break
        lines.insert(insert_idx, entry)
        changelog_path.write_text('\n'.join(lines))
    else:
        content = f"# Changelog\n{entry}"
        changelog_path.write_text(content)

    print(f"CHANGELOG.md updated with v{version}")


def create_pr(repo_path: Path, plugin_name: str, version: str, description: str, is_update: bool, marketplace_repo: str, author_name: str = "", github_username: str = "") -> str:
    """Create branch, commit, push, and open PR. Returns PR URL."""
    prefix = "update" if is_update else "add"
    branch = f"{prefix}/{plugin_name}-v{version}"

    # Handle branch collision: delete existing remote branch
    check_branch = run(
        ["git", "-C", str(repo_path), "ls-remote", "--heads", "origin", branch],
        check=False,
    )
    if check_branch.returncode == 0 and check_branch.stdout.strip():
        print(f"  Branch '{branch}' already exists on remote, using versioned name...")
        branch = f"{prefix}/{plugin_name}-v{version}-{os.getpid()}"

    run(["git", "-C", str(repo_path), "checkout", "-b", branch])
    run(["git", "-C", str(repo_path), "add", "."])

    action = "Update" if is_update else "Add"
    commit_msg = f"{action} {plugin_name} v{version}\n\nAuthor: {author_name} (@{github_username})\n{description}"
    run(["git", "-C", str(repo_path), "commit", "-m", commit_msg])
    run(["git", "-C", str(repo_path), "push", "-u", "origin", branch])

    pr_title = f"{action} {plugin_name} v{version}"
    pr_body = (
        f"## Summary\n"
        f"- {action}: **{plugin_name}**\n"
        f"- Version: {version}\n"
        f"- Author: **{author_name}** (@{github_username})\n"
        f"- {description}\n\n"
        f"## Test plan\n"
        f"- [ ] `node scripts/validate-plugins.js` passes\n"
        f"- [ ] `node scripts/validate-marketplace.js` passes\n"
        f"- [ ] Local test with `claude --plugin-dir`"
    )

    result = run(
        ["gh", "pr", "create",
         "--title", pr_title,
         "--body", pr_body,
         "--repo", marketplace_repo],
        check=False,
        cwd=repo_path,
    )

    if result.returncode == 0:
        pr_url = result.stdout.strip()
        print(f"\nPR created: {pr_url}")
        return pr_url
    else:
        print(f"PR creation output: {result.stdout}")
        if result.stderr:
            print(f"PR creation error: {result.stderr}")
        return ""


def publish(plugin_path: Path, dry_run: bool = False, version_bump: str | None = None, marketplace_repo: str = DEFAULT_MARKETPLACE_REPO) -> bool:
    """Main publish flow."""
    plugin_path = plugin_path.resolve()
    marketplace_name = marketplace_repo.split("/")[-1]

    # 1. Prerequisites
    print("=== Step 1: Check Prerequisites ===")
    errors = check_prerequisites()
    if errors:
        for e in errors:
            print(f"  Error: {e}")
        if not dry_run:
            return False
        print("  (dry-run: continuing despite errors)")

    # 2. Secrets gate (HARD GATE)
    print("\n=== Step 2: Secrets Gate ===")
    if not dry_run:
        if not run_secrets_check(plugin_path):
            return False
    else:
        print("  (dry-run: skipping secrets scan)")

    # 3. Validate structure
    print("\n=== Step 3: Validate Plugin Structure ===")
    valid, plugin_data = validate_plugin_structure(plugin_path)
    if not valid:
        return False

    plugin_name = plugin_data["name"]
    author_name = plugin_data.get("author", {}).get("name", "Unknown")
    print(f"  Plugin: {plugin_name}")
    print(f"  Author: {author_name}")

    # Resolve GitHub username (REQUIRED for author tracking)
    github_username = get_github_username()
    if not github_username:
        print("Error: Could not detect GitHub username. Run: gh auth login")
        return False
    print(f"  Publisher: @{github_username}")

    # Version bump if requested
    if version_bump:
        plugin_data["version"] = bump_version(plugin_path, version_bump)

    version = plugin_data.get("version", "1.0.0")
    description = plugin_data.get("description", "")
    print(f"  Version: {version}")

    # 3.5. Update CHANGELOG
    ensure_changelog(plugin_path, plugin_name, version, description)

    # 4. Detect access level
    print("\n=== Step 4: Detect Access Level ===")
    if not dry_run:
        access = detect_access_level(marketplace_repo)
        print(f"  Access: {access} ({'org member' if access == 'direct' else 'fork required'})")
    else:
        access = "direct"
        print("  (dry-run: assuming direct access)")

    if dry_run:
        print("\n=== DRY RUN SUMMARY ===")
        print(f"  Plugin: {plugin_name} v{version}")
        print(f"  Target: {marketplace_repo}/{PLUGINS_DIR}/{plugin_name}/")
        print(f"  Access: {access}")
        print("  Actions that would be taken:")
        print(f"    1. Clone {marketplace_repo}")
        print(f"    2. Copy {plugin_path} -> {PLUGINS_DIR}/{plugin_name}/")
        print(f"    3. Update {MARKETPLACE_JSON_PATH}")
        print("    4. Run validation scripts")
        print(f"    5. Create PR: 'Add {plugin_name} v{version}'")
        print("\n  No changes were made.")
        return True

    # 5. Clone repo
    print("\n=== Step 5: Clone Repository ===")
    temp_dir = Path(tempfile.mkdtemp())
    try:
        repo_path = clone_repo(temp_dir, access, marketplace_repo)

        # Check if update
        is_update = (repo_path / PLUGINS_DIR / plugin_name).exists()
        if is_update:
            print(f"  Plugin '{plugin_name}' already exists - treating as update")

        # 6. Copy plugin
        print("\n=== Step 6: Copy Plugin ===")
        copy_plugin(plugin_path, repo_path, plugin_name)

        # 7. Register in marketplace.json
        print("\n=== Step 7: Update marketplace.json ===")
        update_marketplace_json(repo_path, plugin_data, github_username)

        # 7.5. Update README plugin table
        print("\n=== Step 7.5: Update README Plugin Table ===")
        update_readme_plugin_table(repo_path)

        # 8. Run validation
        print("\n=== Step 8: Validate ===")
        validate_script = repo_path / "scripts" / "validate-plugins.js"
        if validate_script.exists():
            result = run(["node", str(validate_script)], check=False)
            if result.returncode != 0:
                print(f"Validation failed: {result.stdout}")
                return False

        # 9. Create PR
        print("\n=== Step 9: Create PR ===")
        pr_url = create_pr(repo_path, plugin_name, version, description, is_update, marketplace_repo, author_name, github_username)

        if pr_url:
            print(f"\nDone! PR created: {pr_url}")
            print(f"\nAfter merge, install with:")
            print(f"  /plugin marketplace add {marketplace_repo}")
            print(f"  /plugin install {plugin_name}@{marketplace_name}")
            return True
        else:
            print("\nPR creation may have had issues. Check GitHub manually.")
            return False

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(
        description="Publish a plugin to the PB marketplace"
    )
    parser.add_argument(
        "plugin_path",
        help="Path to the plugin directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    parser.add_argument(
        "--version-bump",
        choices=["patch", "minor", "major"],
        help="Bump version before publishing",
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_MARKETPLACE_REPO,
        help=f"Marketplace repo (default: {DEFAULT_MARKETPLACE_REPO})",
    )

    args = parser.parse_args()
    plugin_path = Path(args.plugin_path)

    if not plugin_path.exists():
        print(f"Error: Path not found: {plugin_path}", file=sys.stderr)
        sys.exit(1)

    if not plugin_path.is_dir():
        print(f"Error: Not a directory: {plugin_path}", file=sys.stderr)
        sys.exit(1)

    success = publish(plugin_path, args.dry_run, args.version_bump, args.repo)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
