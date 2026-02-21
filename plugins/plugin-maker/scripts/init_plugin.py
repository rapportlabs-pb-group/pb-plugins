#!/usr/bin/env python3
"""
Plugin Initializer Script

Creates a new Claude Code plugin with the recommended directory structure.

Usage:
    python3 init_plugin.py <plugin-name> [--marketplace <name>] [--no-setup]

Examples:
    # Create standalone plugin (includes setup skill)
    python3 init_plugin.py my-tool

    # Create without setup skill
    python3 init_plugin.py my-tool --no-setup

    # Create plugin in marketplace
    python3 init_plugin.py my-tool --marketplace my-marketplace
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def validate_plugin_name(name: str) -> tuple[bool, str]:
    """Validate plugin name is kebab-case. Returns (valid, suggestion)."""
    if re.match(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$', name):
        return True, name
    suggested = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    suggested = re.sub(r'-+', '-', suggested)
    if not suggested or not suggested[0].isalpha():
        suggested = 'my-' + suggested
    return False, suggested


def create_setup_skill(plugin_dir: Path, plugin_name: str) -> None:
    """Generate a setup skill inside the plugin."""
    setup_dir = plugin_dir / "skills" / "setup"
    setup_dir.mkdir(parents=True, exist_ok=True)

    setup_md = f"""---
name: setup
description: "Initial setup for {plugin_name}. Run after installing the plugin."
---

# {plugin_name} Setup

## Step 0: Resume Detection

Check for existing setup state:

```bash
STATE_FILE=".plugin-state/setup-state.json"
if [ -f "$STATE_FILE" ]; then
  LAST_STEP=$(jq -r '.lastCompletedStep // 0' "$STATE_FILE" 2>/dev/null)
  echo "Found previous session at step $LAST_STEP"
fi
```

If state exists, ask user: "Resume from step $LAST_STEP or start fresh?"

## Step 1: Check Environment

Verify required tools are available:

```bash
# TODO: Add your prerequisites here
command -v python3 >/dev/null 2>&1 || {{ echo "python3 required"; exit 1; }}
command -v git >/dev/null 2>&1 || {{ echo "git required"; exit 1; }}
echo "Environment OK"
```

Save progress:
```bash
mkdir -p .plugin-state
cat > ".plugin-state/setup-state.json" << EOF
{{"lastCompletedStep": 1, "timestamp": "$(date '+%Y-%m-%dT%H:%M:%S%z')", "pluginName": "{plugin_name}"}}
EOF
```

## Step 2: Install Dependencies

```bash
# TODO: Add your dependency installation here
# pip install -q -r "${{CLAUDE_PLUGIN_ROOT}}/requirements.txt" 2>/dev/null || true
echo "Dependencies installed"
```

Save progress after completion.

## Step 3: Configure

```bash
# TODO: Add your configuration steps here
mkdir -p .plugin-state
echo "Configuration complete"
```

Save progress after completion.

## Step 4: Validate

```bash
# TODO: Add validation checks here
echo "Validation passed"
```

Clear state on success:
```bash
rm -f ".plugin-state/setup-state.json"
echo "Setup complete!"
```
"""
    (setup_dir / "SKILL.md").write_text(setup_md)


def create_plugin(plugin_name: str, marketplace: str | None = None, with_setup: bool = True, target_path: Path | None = None) -> Path:
    """Create a new plugin with recommended structure."""

    # Validate name
    valid, suggested = validate_plugin_name(plugin_name)
    if not valid:
        print(f"Error: '{plugin_name}' is not valid kebab-case.", file=sys.stderr)
        print(f"Suggestion: '{suggested}'", file=sys.stderr)
        sys.exit(1)

    # Determine base path
    base_dir = target_path or Path.cwd()
    if marketplace:
        base = base_dir / marketplace
        plugin_dir = base / plugin_name
    else:
        plugin_dir = base_dir / plugin_name

    # Create directories
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / ".claude-plugin").mkdir(exist_ok=True)
    (plugin_dir / "skills").mkdir(exist_ok=True)
    (plugin_dir / "agents").mkdir(exist_ok=True)
    (plugin_dir / "hooks").mkdir(exist_ok=True)
    (plugin_dir / "scripts").mkdir(exist_ok=True)

    # Create .claude-plugin/plugin.json
    plugin_json = {
        "name": plugin_name,
        "version": "1.0.0",
        "description": f"{plugin_name} plugin for Claude Code",
        "author": {
            "name": "Your Name"
        }
    }
    (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(plugin_json, indent=2, ensure_ascii=False) + "\n"
    )

    # Create example skill
    skill_dir = plugin_dir / "skills" / "main"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = f"""---
name: main
description: "{plugin_name} main skill. Describe when Claude should use this."
# disable-model-invocation: true  # Uncomment to prevent auto-invocation
---

# {plugin_name} Main Skill

## Steps

### 1. Check prerequisites
Verify required files exist in user's project folder.

### 2. Execute
```bash
python3 "${{CLAUDE_PLUGIN_ROOT}}/scripts/main.py"
```

### 3. Verify results
- Output: `./output/` (user's CWD)
"""
    (skill_dir / "SKILL.md").write_text(skill_md)

    # Create example agent
    agent_md = f"""---
name: helper
description: {plugin_name} helper agent for specialized tasks
---

# {plugin_name} Helper Agent

You are a specialized agent for {plugin_name}.

## Role
Assist with tasks specific to this plugin's domain.

## Guidelines
- Focus on the task at hand
- Use available tools appropriately
- Report findings clearly
"""
    (plugin_dir / "agents" / "helper.md").write_text(agent_md)

    # Create hooks/hooks.json (empty)
    hooks_json = {
        "hooks": {}
    }
    (plugin_dir / "hooks" / "hooks.json").write_text(
        json.dumps(hooks_json, indent=2) + "\n"
    )

    # Create example script
    script_py = '''#!/usr/bin/env python3
"""
Main script for the plugin.

Path rules:
- PLUGIN_ROOT: Where plugin scripts live (for imports/templates)
- CWD: Where user runs command (for credentials/output)
"""

from pathlib import Path

# Path resolution
PLUGIN_ROOT = Path(__file__).parent.parent  # Plugin installation directory
CWD = Path.cwd()                            # User's current working directory


def main():
    """Main entry point."""
    print(f"Plugin root: {PLUGIN_ROOT}")
    print(f"Working directory: {CWD}")

    # Example: Read credentials from user's project
    creds_path = CWD / "credentials" / "config.json"
    if creds_path.exists():
        print(f"Found credentials: {creds_path}")

    # Example: Write output to user's project
    output_dir = CWD / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
'''
    (plugin_dir / "scripts" / "main.py").write_text(script_py)

    # Create README.md
    readme = f"""# {plugin_name}

## Description

{plugin_name} plugin for Claude Code.

## Prerequisites

- Claude Code v1.0.33+

## Installation

```bash
# 1. Add PB marketplace (one-time)
/plugin marketplace add rapportlabs-pb-group/pb-plugins

# 2. Install
/plugin install {plugin_name}@pb-plugins
```

### Local Testing

```bash
claude --plugin-dir ./{plugin_name}
```

## Skills

| Skill | Description |
|-------|-------------|
| `/{plugin_name}:main` | Main skill |

## Usage

```
/{plugin_name}:main [arguments]
```

## Configuration

No additional configuration required.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Skill not appearing | Restart Claude Code after installing |
| Script errors | Check `claude --debug` for details |

## License

MIT
"""
    (plugin_dir / "README.md").write_text(readme)

    # Create setup skill (unless --no-setup)
    if with_setup:
        create_setup_skill(plugin_dir, plugin_name)

    # Create .gitignore
    gitignore = """# Secrets and credentials
.env*
credentials/
secrets/
*.key
*.pem
*.p12
*.pfx
service-account*.json

# Development files
CLAUDE.md
__pycache__/
*.pyc
node_modules/

# Plugin state
.plugin-state/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
"""
    (plugin_dir / ".gitignore").write_text(gitignore)

    # Create marketplace structure if needed
    if marketplace:
        marketplace_dir = Path.cwd() / marketplace
        mp_claude_dir = marketplace_dir / ".claude-plugin"
        mp_claude_dir.mkdir(parents=True, exist_ok=True)
        mp_json_path = mp_claude_dir / "marketplace.json"

        if mp_json_path.exists():
            data = json.loads(mp_json_path.read_text())
            existing_names = [p["name"] for p in data.get("plugins", []) if isinstance(p, dict)]
            if plugin_name not in existing_names:
                data.setdefault("plugins", []).append({
                    "name": plugin_name,
                    "source": f"./{plugin_name}",
                    "description": f"{plugin_name} plugin"
                })
                mp_json_path.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False) + "\n"
                )
        else:
            data = {
                "name": marketplace,
                "owner": {
                    "name": "Your Name"
                },
                "plugins": [
                    {
                        "name": plugin_name,
                        "source": f"./{plugin_name}",
                        "description": f"{plugin_name} plugin"
                    }
                ]
            }
            mp_json_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n"
            )

    return plugin_dir


def main():
    parser = argparse.ArgumentParser(
        description="Initialize a new Claude Code plugin"
    )
    parser.add_argument(
        "plugin_name",
        help="Name of the plugin to create"
    )
    parser.add_argument(
        "--marketplace",
        help="Marketplace name (creates marketplace structure)"
    )
    parser.add_argument(
        "--no-setup",
        action="store_true",
        help="Skip generating setup skill inside the plugin"
    )
    parser.add_argument(
        "--path",
        help="Target directory to create plugin in (default: current directory)",
    )

    args = parser.parse_args()

    target_path = Path(args.path) if args.path else None
    if target_path and not target_path.is_dir():
        print(f"Error: Target path not found: {target_path}", file=sys.stderr)
        sys.exit(1)

    plugin_dir = create_plugin(args.plugin_name, args.marketplace, with_setup=not args.no_setup, target_path=target_path)

    if args.marketplace:
        print(f"""
Plugin created in marketplace!

Location: {plugin_dir}

Structure:
{args.marketplace}/
├── .claude-plugin/
│   └── marketplace.json
└── {args.plugin_name}/
    ├── .claude-plugin/
    │   └── plugin.json
    ├── skills/
    │   └── main/
    │       └── SKILL.md
    ├── agents/
    │   └── helper.md
    ├── hooks/
    │   └── hooks.json
    ├── scripts/
    │   └── main.py
    ├── README.md
    └── .gitignore

Next steps:
1. Edit .claude-plugin/plugin.json with your details
2. Customize skills/main/SKILL.md
3. Implement scripts/main.py
4. Test: claude --plugin-dir ./{args.plugin_name}
5. Add marketplace: /plugin marketplace add ./{args.marketplace}
6. Install: /plugin install {args.plugin_name}@{args.marketplace}
""")
    else:
        setup_note = ""
        if not args.no_setup:
            setup_note = f"""│   └── setup/
│       └── SKILL.md    (setup skill for downloaders)
"""
        print(f"""
Plugin created!

Location: {plugin_dir}

Structure:
{args.plugin_name}/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── main/
│   │   └── SKILL.md
{setup_note}├── agents/
│   └── helper.md
├── hooks/
│   └── hooks.json
├── scripts/
│   └── main.py
├── README.md
└── .gitignore

Next steps:
1. Edit .claude-plugin/plugin.json with your details
2. Customize skills/main/SKILL.md
3. Implement scripts/main.py
4. Test: claude --plugin-dir ./{args.plugin_name}
5. Scan: /plugin-maker:check-secrets
6. Publish: /plugin-maker:publish
""")


if __name__ == "__main__":
    main()
