# PB Marketplace Conventions

Guidelines for `rapportlabs-pb-group/pb-plugins` contributors.

## Naming

- **Format**: kebab-case (`my-tool`, not `myTool` or `my_tool`)
- **Prefix**: Use domain prefix for related plugins (`pb-auth`, `pb-deploy`)
- **Uniqueness**: Check existing names before creating: `gh api repos/rapportlabs-pb-group/pb-plugins/contents/plugins --jq '.[].name'`

## Required Files

| File | Purpose |
|------|---------|
| `.claude-plugin/plugin.json` | Manifest with name, version, description |
| `skills/<name>/SKILL.md` | At least one skill |
| `README.md` | Installation and usage documentation |
| `.gitignore` | Exclude secrets, dev files, CLAUDE.md |

## plugin.json Fields

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Brief purpose (under 100 chars)",
  "author": {
    "name": "Your Name"
  },
  "keywords": ["category"]
}
```

**Required**: `name`, `version`, `description`
**Recommended**: `author`, `keywords`

## Keywords

Use consistent keywords for discoverability:

| Category | Keywords |
|----------|----------|
| Development workflow | `workflow`, `automation`, `productivity` |
| Code quality | `linting`, `formatting`, `review` |
| Testing | `testing`, `tdd`, `e2e` |
| DevOps | `deployment`, `ci-cd`, `infrastructure` |
| Data | `data`, `analytics`, `database` |
| Integration | `api`, `mcp`, `integration` |
| Security | `security`, `scanning`, `audit` |

## README Requirements

PB marketplace plugins must include:

1. **Description**: What the plugin does
2. **Installation**: PB-specific install commands
3. **Skills table**: List all skills with descriptions
4. **Usage**: At least one usage example
5. **Prerequisites**: Any external dependencies

### Installation Section Template

```markdown
## Installation

\`\`\`bash
# Add PB marketplace (one-time)
/plugin marketplace add rapportlabs-pb-group/pb-plugins

# Install
/plugin install my-plugin@pb-plugins
\`\`\`
```

## Path Rules

| Context | Use |
|---------|-----|
| Plugin's own files | `${CLAUDE_PLUGIN_ROOT}/scripts/...` |
| User's project files | `${CWD}/...` |
| Never use | `~/.claude/...`, `/Users/xxx/...`, absolute paths |

## Version Bumping

Every update to pb-plugins must increment the version:

| Change Type | Bump | Example |
|-------------|------|---------|
| Bug fix | patch | 1.0.0 -> 1.0.1 |
| New skill/feature | minor | 1.0.0 -> 1.1.0 |
| Breaking change | major | 1.0.0 -> 2.0.0 |

## PR Conventions

- Branch: `add/<plugin-name>-v<version>` (new) or `update/<plugin-name>-v<version>` (update)
- Title: `Add <name> v<version>` or `Update <name> v<version>`
- Body: Summary + test plan

## Validation

The pb-plugins repo runs validation scripts on PRs:

```bash
node scripts/validate-plugins.js    # Plugin structure
node scripts/validate-marketplace.js # marketplace.json consistency
```

These check:
- plugin.json exists with valid JSON
- Name matches directory name
- Required fields present
- marketplace.json entry is consistent
- No duplicate entries

## Prohibited Content

- `.env` files or any environment variable files
- API keys, tokens, credentials (hardcoded or in files)
- `CLAUDE.md` (development config)
- `node_modules/`, `__pycache__/`, `.venv/`
- Database files (`.sqlite`, `.db`)
- SSH/GPG keys
- Hardcoded user paths (`~/.claude/`, `/Users/xxx/`)
