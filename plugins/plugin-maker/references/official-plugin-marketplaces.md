# Plugin Marketplaces (Official Documentation)

> Create and manage plugin marketplaces to distribute Claude Code extensions.

Source: https://code.claude.com/docs/en/plugin-marketplaces

Plugin marketplaces are catalogs of available plugins for discovery, installation, and management.

---

## Overview

A marketplace is a JSON file listing available plugins. Marketplaces provide:

- **Centralized discovery**: Browse plugins from multiple sources
- **Version management**: Track and update plugin versions
- **Team distribution**: Share required plugins across organization
- **Flexible sources**: Git repositories, GitHub repos, local paths, URLs
- **Auto-updates**: Automatically refresh marketplace data at startup

---

## Official Anthropic Marketplace

The `claude-plugins-official` marketplace is **automatically available** without adding it. Browse via `/plugin` Discover tab.

Categories:
- **Code intelligence (LSP)**: Go, Python, TypeScript, Rust, C/C++, C#, Java, Kotlin, Lua, PHP, Swift
- **External integrations (MCP)**: GitHub, GitLab, Atlassian, Asana, Linear, Notion, Figma, Vercel, Firebase, Supabase, Slack, Sentry
- **Development workflows**: `commit-commands`, `pr-review-toolkit`, `agent-sdk-dev`, `plugin-dev`
- **Output styles**: `explanatory-output-style`, `learning-output-style`

---

## Add and Use Marketplaces

### Add Marketplaces

```shell
# GitHub repository
/plugin marketplace add owner/repo

# Git repository (any host)
/plugin marketplace add https://gitlab.com/company/plugins.git

# Specific branch/tag
/plugin marketplace add https://gitlab.com/company/plugins.git#v1.0.0

# SSH
/plugin marketplace add git@gitlab.com:company/plugins.git

# Local directory
/plugin marketplace add ./my-marketplace

# Direct path to marketplace.json
/plugin marketplace add ./path/to/marketplace.json

# Remote URL
/plugin marketplace add https://url.com/marketplace.json
```

### Install Plugins

```shell
# Install from known marketplace
/plugin install plugin-name@marketplace-name

# Browse interactively
/plugin
```

### Manage Marketplaces

```shell
/plugin marketplace list              # List all
/plugin marketplace update name       # Refresh
/plugin marketplace remove name       # Remove (uninstalls plugins from it)
```

**Shortcut**: `/plugin market` instead of `/plugin marketplace`

---

## Configure Team Marketplaces

Set up automatic installation for team projects in `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "team-tools": {
      "source": {
        "source": "github",
        "repo": "your-org/claude-plugins"
      }
    },
    "project-specific": {
      "source": {
        "source": "git",
        "url": "https://git.company.com/project-plugins.git"
      }
    }
  }
}
```

When team members trust the repository folder, Claude Code automatically prompts to install marketplaces and plugins.

---

## Configure Auto-Updates

Toggle per marketplace via UI:

1. `/plugin` > **Marketplaces** tab
2. Select marketplace
3. **Enable/Disable auto-update**

- Official Anthropic marketplaces: auto-update **enabled** by default
- Third-party/local: auto-update **disabled** by default

Environment variables:

```bash
# Disable all auto-updates
export DISABLE_AUTOUPDATER=true

# Keep plugin auto-updates while disabling Claude Code updates
export DISABLE_AUTOUPDATER=true
export FORCE_AUTOUPDATE_PLUGINS=true
```

---

## Create Your Own Marketplace

### Marketplace Structure

```
my-marketplace/
├── .claude-plugin/
│   └── marketplace.json
├── plugin-a/
│   ├── .claude-plugin/
│   │   └── plugin.json
│   ├── skills/
│   └── ...
└── plugin-b/
    └── ...
```

### marketplace.json

```json
{
  "name": "company-tools",
  "owner": {
    "name": "DevTools Team",
    "email": "devtools@company.com"
  },
  "plugins": [
    {
      "name": "code-formatter",
      "source": "./plugins/formatter",
      "description": "Automatic code formatting on save",
      "version": "2.1.0",
      "author": {
        "name": "DevTools Team"
      }
    },
    {
      "name": "deployment-tools",
      "source": {
        "source": "github",
        "repo": "company/deploy-plugin"
      },
      "description": "Deployment automation tools"
    }
  ]
}
```

### Marketplace Schema

**Required fields**:

| Field | Type | Description |
|:------|:-----|:------------|
| `name` | string | Marketplace identifier (kebab-case) |
| `owner` | object | Maintainer information |
| `plugins` | array | List of available plugins |

**Optional metadata**:

| Field | Type | Description |
|:------|:-----|:------------|
| `metadata.description` | string | Brief marketplace description |
| `metadata.version` | string | Marketplace version |
| `metadata.pluginRoot` | string | Base path for relative plugin sources |

### Plugin Entry Fields

**Required**:

| Field | Type | Description |
|:------|:-----|:------------|
| `name` | string | Plugin identifier (kebab-case) |
| `source` | string\|object | Where to fetch the plugin |

**Optional**:

| Field | Type | Description |
|:------|:-----|:------------|
| `description` | string | Brief plugin description |
| `version` | string | Plugin version |
| `author` | object | Plugin author information |
| `homepage` | string | Documentation URL |
| `repository` | string | Source code URL |
| `license` | string | SPDX identifier |
| `keywords` | array | Discovery tags |
| `category` | string | Plugin category |
| `tags` | array | Searchability tags |
| `strict` | boolean | Require plugin.json in folder (default: `true`) |
| `commands` | string\|array | Custom command paths |
| `agents` | string\|array | Custom agent paths |
| `hooks` | string\|object | Hooks configuration |
| `mcpServers` | string\|object | MCP server configurations |

**Schema relationship**: When `strict: false`, marketplace entry serves as complete manifest if no `plugin.json` exists. When `strict: true` (default), marketplace fields supplement plugin's own manifest.

### Plugin Sources

**Relative paths**:
```json
{"name": "my-plugin", "source": "./plugins/my-plugin"}
```

**GitHub**:
```json
{"name": "gh-plugin", "source": {"source": "github", "repo": "owner/repo"}}
```

**Git URL**:
```json
{"name": "git-plugin", "source": {"source": "url", "url": "https://gitlab.com/team/plugin.git"}}
```

---

## Host and Distribute

### GitHub (Recommended)

1. Create repository
2. Add `.claude-plugin/marketplace.json`
3. Share: `/plugin marketplace add owner/repo`

### Other Git Services

```shell
/plugin marketplace add https://gitlab.com/company/plugins.git
```

### Local (Development)

```shell
/plugin marketplace add ./my-local-marketplace
/plugin install test-plugin@my-local-marketplace
```

---

## Troubleshooting

### Marketplace Not Loading

- Verify URL is accessible
- Check `.claude-plugin/marketplace.json` exists at path
- Ensure JSON syntax is valid: `claude plugin validate`
- For private repos, confirm access permissions

### Plugin Installation Failures

- Verify plugin source URLs are accessible
- Check plugin directories contain required files
- For GitHub sources, ensure repos are public or you have access
- Test plugin sources manually

### Validation

```bash
claude plugin validate .
```

```shell
/plugin marketplace add ./path/to/marketplace
/plugin install test-plugin@marketplace-name
```
