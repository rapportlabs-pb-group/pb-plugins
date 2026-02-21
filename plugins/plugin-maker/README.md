# plugin-maker

Create, secure, and publish Claude Code plugins to the PB marketplace (`rapportlabs-pb-group/pb-plugins`).

## Prerequisites

- Claude Code v1.0.33+
- `gh` (GitHub CLI, authenticated)
- `git`, `jq`, `rsync`, `python3`

## Installation

```bash
# Add PB marketplace (one-time)
/plugin marketplace add rapportlabs-pb-group/pb-plugins

# Install
/plugin install plugin-maker@pb-plugins
```

### Local Testing

```bash
claude --plugin-dir ./plugin-maker
```

## Skills

| Skill | Description |
|-------|-------------|
| `/plugin-maker` | Full plugin creation guide (auto-triggered) |
| `/plugin-maker:init` | Guided plugin initialization with structure generation |
| `/plugin-maker:check-secrets` | 3-layer secrets scanner (files, content, paths, .gitignore) |
| `/plugin-maker:publish` | Guided PB marketplace publishing (clone/copy/register/PR) |

## Usage

### Create a new plugin

```
/plugin-maker:init
```

Walks you through plugin name, marketplace membership, setup skill inclusion, and target directory. Generates the full plugin structure with `plugin.json`, example skill, agent, hooks, scripts, README, and `.gitignore`.

### Scan for secrets before publishing

```
/plugin-maker:check-secrets
```

Scans for sensitive files (`.env`, `*.key`, credentials), hardcoded secrets (API keys, tokens, passwords), hardcoded user paths (`/Users/xxx/`, `~/.claude/`), and validates `.gitignore` configuration.

### Publish to PB marketplace

```
/plugin-maker:publish
```

Automates the full publishing workflow: prerequisites check, secrets gate (hard blocker), structure validation, clone pb-plugins, copy plugin, update `marketplace.json`, create PR.

## Bundled References

| Reference | Topic |
|-----------|-------|
| `official-plugins-reference.md` | Complete plugin technical specs |
| `official-plugins-guide.md` | Quickstart and development workflow |
| `plugin-json-schema.md` | plugin.json manifest schema |
| `pb-conventions.md` | PB marketplace naming, structure, PR conventions |
| `publishing-workflow.md` | Step-by-step beginner publishing guide |
| `setup-skill-template.md` | Setup skill patterns for plugin generators |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Skill not appearing | Restart Claude Code after installing |
| Secrets scan fails | Remove sensitive files, replace hardcoded paths with `${CLAUDE_PLUGIN_ROOT}` |
| `gh: command not found` | `brew install gh` then `gh auth login` |
| Publish fails (branch exists) | Delete remote branch: `git push origin --delete add/my-plugin` |
| Script errors | Check `claude --debug` for details |

## License

MIT
