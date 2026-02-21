---
name: plugin-maker
version: 2.5.0
description: "Use when creating Claude Code plugins for PB marketplace (rapportlabs-pb-group/pb-plugins), scanning for secrets, or publishing. Triggers: 'create plugin', 'make a plugin', 'publish plugin', 'check secrets', 'PB plugin', 'plugin 생성', '플러그인 만들어줘', 'PB 마켓플레이스'"
---

# Plugin Maker

Guide for creating, securing, and publishing Claude Code plugins to the PB marketplace (`rapportlabs-pb-group/pb-plugins`).

## Bundled Resources

### Scripts
- `scripts/init_plugin.py` - Initialize new plugin with structure and setup skill
- `scripts/check_secrets.py` - 3-layer secrets scanner (files, content, paths, .gitignore)
- `scripts/publish_to_pb.py` - Automated PB marketplace publishing (clone/copy/register/PR)

### References (load as needed)
- `references/official-plugins-reference.md` - Complete technical specs
- `references/official-plugins-guide.md` - Quickstart and development workflow
- `references/official-plugin-marketplaces.md` - Marketplace creation
- `references/plugin-json-schema.md` - plugin.json manifest schema
- `references/mcp-json-schema.md` - .mcp.json schema
- `references/pb-marketplace-publishing.md` - PB repo structure and rules
- `references/publishing-workflow.md` - Step-by-step beginner publishing guide
- `references/pb-conventions.md` - PB marketplace naming, structure, and PR conventions
- `references/setup-skill-template.md` - Setup skill patterns for plugin generators

## Standard Plugin Structure

```
my-plugin/
├── .claude-plugin/plugin.json
├── skills/
│   ├── main/SKILL.md
│   └── setup/SKILL.md      # Auto-generated for downloaders
├── agents/, hooks/, scripts/
├── .mcp.json, .lsp.json, settings.json
├── README.md, .gitignore
```

**Critical**: Only `plugin.json` goes in `.claude-plugin/`. Use `${CLAUDE_PLUGIN_ROOT}` for all internal paths.

## Process

### 1. Initialize
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_plugin.py" my-plugin
# --no-setup to skip setup skill generation
# --marketplace <name> for marketplace structure
# --path <dir> to create in a specific directory
```

### 2. Configure plugin.json (optional)
See `references/plugin-json-schema.md` for full schema.

### 3. Create Skills (preferred over commands)
See `references/official-plugins-reference.md` for SKILL.md frontmatter.

### 4. Configure Hooks
Events (14): `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `UserPromptSubmit`, `Notification`, `Stop`, `SubagentStart`, `SubagentStop`, `SessionStart`, `SessionEnd`, `TeammateIdle`, `TaskCompleted`, `PreCompact`

### 5. Test Locally
```bash
claude --plugin-dir ./my-plugin
```

### 6. Secrets Gate (BLOCKING)
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_secrets.py" ./my-plugin
# --json for machine-readable output
# --strict to fail on warnings too
```
Scans: sensitive files, hardcoded secrets, hardcoded user paths, .gitignore validation. **Must pass before distribution.**

### 7. Distribute
```bash
# PB Marketplace (auto: clone, copy, register, PR)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish_to_pb.py" ./my-plugin
# --dry-run to preview without changes
# --version-bump patch|minor|major
# --repo owner/repo for custom marketplace target
```
See `references/publishing-workflow.md` for beginner guide.

## Sub-Skills

| Command | Description |
|---------|-------------|
| `/plugin-maker:init` | Guided plugin initialization |
| `/plugin-maker:check-secrets` | Guided secrets scan |
| `/plugin-maker:publish` | Guided marketplace publishing |

## Pitfalls

1. **CLAUDE.md must NOT be in plugin** - Add to `.gitignore`
2. **Never hardcode paths** - Use `${CLAUDE_PLUGIN_ROOT}`
3. **Bump version** in plugin.json for updates
4. **No path traversal** - Plugins can't reference files outside their directory
5. **Run secrets scan** before every distribution

## Pre-Distribution Checklist

- [ ] `check_secrets.py` passes (exit 0)
- [ ] All paths use `${CLAUDE_PLUGIN_ROOT}` or `${CWD}`
- [ ] CLAUDE.md NOT included
- [ ] Version bumped for updates
- [ ] Tested with `claude --plugin-dir`
