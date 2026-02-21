---
name: init
description: "Initialize a new Claude Code plugin with recommended structure. Triggers: 'create plugin', 'init plugin', 'new plugin'"
---

# Plugin Initializer

Guided plugin initialization using `scripts/init_plugin.py`.

## Flow

### Step 1: Gather Plugin Name

Ask the user for their plugin name. Validate kebab-case format (lowercase, hyphens only, no spaces or special characters). If invalid, suggest a corrected version and confirm.

### Step 2: Marketplace Membership

Ask: "Should this be a standalone plugin or part of an existing marketplace?"

Options:
- **Standalone** (default) - Plugin lives on its own
- **Marketplace member** - Ask for marketplace directory name

### Step 3: Setup Skill

Ask: "Include a setup skill for first-time plugin users?" (default: yes)

A setup skill auto-runs when someone installs your plugin. Skip only for simple plugins with no configuration.

### Step 4: Target Directory

Ask: "Create in the current directory or a specific path?"

Options:
- **Current directory** (default) - Creates `<plugin-name>/` in CWD
- **Custom path** - Ask for the target directory path

### Step 5: Execute

Assemble and run the command:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_plugin.py" <plugin-name> [--marketplace <name>] [--no-setup] [--path <dir>]
```

Run from the user's current working directory.

### Step 6: Next Steps

After successful creation, show:
1. `cd <plugin-name>` to enter the plugin directory
2. Edit `skills/main/SKILL.md` to add your primary skill logic
3. Configure `.claude-plugin/plugin.json` if needed (see `references/plugin-json-schema.md`)
4. Test with `claude --plugin-dir ./<plugin-name>`
5. Run `/plugin-maker:check-secrets` before distributing
