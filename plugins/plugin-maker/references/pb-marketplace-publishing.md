# PB Marketplace Publishing Reference

Technical reference for publishing plugins to the `rapportlabs-pb-group/pb-plugins` marketplace.

## Repository Structure

```
pb-plugins/
├── .claude-plugin/
│   └── marketplace.json    # Plugin registry
├── plugins/
│   ├── plugin-a/           # Each plugin in its own directory
│   ├── plugin-b/
│   └── ...
└── scripts/
    ├── validate-plugins.js
    └── validate-marketplace.js
```

## Strict Rules

1. **No secrets**: `.env`, API keys, tokens, credentials = immediate rejection
2. **No CLAUDE.md**: Development config must not ship
3. **Use `${CLAUDE_PLUGIN_ROOT}`**: All internal paths must use this variable
4. **kebab-case names**: Plugin names must be lowercase with hyphens
5. **plugin.json required**: Must exist at `.claude-plugin/plugin.json`
6. **Version bumping**: Every update must increment semver + CHANGELOG entry

## marketplace.json Entry Format

```json
{
  "name": "my-plugin",
  "source": "./plugins/my-plugin",
  "description": "Short description of the plugin",
  "version": "1.0.0",
  "author": {"name": "Author Name"},
  "keywords": ["category", "tag"],
  "dependencies": [],
  "requirements": {}
}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique kebab-case identifier |
| `source` | Yes | Relative path `./plugins/<name>` |
| `description` | Yes | Short description |
| `version` | Yes | Semver string |
| `author` | Yes | Object with `name` field |
| `keywords` | No | Search tags |
| `dependencies` | No | Other plugin names |
| `requirements` | No | `{"node": ">=18"}` etc. |

## Three Publishing Paths

### 1. Direct Push (Org Members)

Org members with write access:
```
clone -> branch -> copy -> register -> validate -> push -> PR
```

Detection: `gh api /orgs/rapportlabs-pb-group/members --jq '.[].login'` includes current user.

### 2. Fork + PR (External Contributors)

Non-members:
```
fork -> clone fork -> branch -> copy -> register -> validate -> push to fork -> PR to upstream
```

Detection: User not in org members list, or `gh api` returns 403.

### 3. Manual (No gh CLI)

When `gh` is not available:
```
1. Fork https://github.com/rapportlabs-pb-group/pb-plugins
2. Clone your fork
3. Create branch: git checkout -b add/my-plugin
4. Copy plugin to plugins/my-plugin/
5. Update marketplace.json
6. Push and create PR via GitHub web UI
```

## rsync Exclusion List

When copying plugin files to the marketplace repo:

```
--exclude='.git'
--exclude='.env*'
--exclude='credentials*'
--exclude='secrets*'
--exclude='*.key'
--exclude='*.pem'
--exclude='*.p12'
--exclude='*.pfx'
--exclude='service-account*.json'
--exclude='node_modules'
--exclude='__pycache__'
--exclude='.DS_Store'
--exclude='CLAUDE.md'
--exclude='.plugin-state'
--exclude='*.pyc'
--exclude='.venv'
--exclude='venv'
```

## Validation

After copying, run marketplace validation scripts:

```bash
node scripts/validate-plugins.js
node scripts/validate-marketplace.js
```

These check:
- plugin.json exists and is valid JSON
- Name matches directory name
- Required fields present
- marketplace.json is consistent
- No duplicate entries

## Version Bumping (Updates)

For existing plugins:

1. Update plugin source files
2. Bump version in `plugins/<name>/.claude-plugin/plugin.json`
3. Update version in `marketplace.json`
4. Add CHANGELOG.md entry
5. Branch name: `update/<name>-v<version>`

## Installation (After Merge)

```bash
# Add marketplace (one-time)
/plugin marketplace add rapportlabs-pb-group/pb-plugins

# Install plugin
/plugin install my-plugin@pb-plugins

# Update plugin
/plugin update my-plugin@pb-plugins
```
