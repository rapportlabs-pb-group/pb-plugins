# Plugins Reference (Official Documentation)

> Complete technical reference for Claude Code plugin system, including schemas, CLI commands, and component specifications.

Source: https://code.claude.com/docs/en/plugins-reference

A **plugin** is a self-contained directory of components that extends Claude Code. Plugin components include skills, agents, hooks, MCP servers, and LSP servers.

---

## Plugin Components Reference

### Skills (Preferred)

Plugins add skills creating `/plugin-name:skill-name` shortcuts.

**Location**: `skills/` directory in plugin root (preferred) or `commands/` (legacy)

**File format**: Skills are directories with `SKILL.md`; commands are simple markdown files

**Skill structure**:

```
skills/
├── pdf-processor/
│   ├── SKILL.md
│   ├── reference.md (optional)
│   └── scripts/ (optional)
└── code-reviewer/
    └── SKILL.md
```

**SKILL.md frontmatter fields**:

| Field | Required | Description |
|:------|:---------|:------------|
| `name` | No | Display name. Defaults to directory name. Lowercase, hyphens, max 64 chars. |
| `description` | Recommended | What it does and when to use it. Drives auto-invocation. |
| `argument-hint` | No | Hint for autocomplete (e.g., `[issue-number]`) |
| `disable-model-invocation` | No | `true` = only user can invoke. Default: `false`. |
| `user-invocable` | No | `false` = hidden from `/` menu. Default: `true`. |
| `allowed-tools` | No | Tools Claude can use without permission when skill is active. |
| `model` | No | Model to use when skill is active. |
| `context` | No | Set to `fork` to run in isolated subagent. |
| `agent` | No | Subagent type when `context: fork` is set. |
| `hooks` | No | Hooks scoped to this skill's lifecycle. |

**String substitutions**:

| Variable | Description |
|:---------|:------------|
| `$ARGUMENTS` | All arguments passed after skill name |
| `$ARGUMENTS[N]` | Nth argument (0-based) |
| `$N` | Shorthand for `$ARGUMENTS[N]` |
| `${CLAUDE_SESSION_ID}` | Current session ID |

**Dynamic context injection**: `!`command`` runs shell commands before content is sent. Output replaces the placeholder.

**Integration behavior**:

- Skills and commands auto-discovered when plugin is installed
- Claude invokes automatically based on task context
- Skills can include supporting files alongside SKILL.md
- Custom slash commands have been **merged into skills**. Skills are preferred for new work.

### Agents

Specialized subagents for specific tasks.

**Location**: `agents/` directory in plugin root

**File format**: Markdown files with YAML frontmatter

```markdown
---
name: agent-name
description: What this agent specializes in and when Claude should invoke it
---

Detailed system prompt describing role, expertise, and behavior.
```

**Integration points**:

- Appear in `/agents` interface
- Claude invokes automatically based on task context
- Can be invoked manually by users
- Work alongside built-in agents

### Hooks

Event handlers that respond to Claude Code lifecycle events.

**Location**: `hooks/hooks.json` in plugin root, or inline in plugin.json

**Hook configuration**:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-code.sh"
          }
        ]
      }
    ]
  }
}
```

**Available events (14)**:

| Event | When |
|:------|:-----|
| `PreToolUse` | Before Claude uses any tool |
| `PostToolUse` | After Claude successfully uses any tool |
| `PostToolUseFailure` | After Claude tool execution fails |
| `PermissionRequest` | When a permission dialog is shown |
| `UserPromptSubmit` | When user submits a prompt |
| `Notification` | When Claude Code sends notifications |
| `Stop` | When Claude attempts to stop |
| `SubagentStart` | When a subagent is started |
| `SubagentStop` | When a subagent attempts to stop |
| `SessionStart` | At the beginning of sessions |
| `SessionEnd` | At the end of sessions |
| `TeammateIdle` | When an agent team teammate is about to go idle |
| `TaskCompleted` | When a task is being marked as completed |
| `PreCompact` | Before conversation history is compacted |

**Hook types (3)**:

| Type | Description |
|:-----|:------------|
| `command` | Execute shell commands or scripts |
| `prompt` | Evaluate a prompt with an LLM (uses `$ARGUMENTS` placeholder) |
| `agent` | Run an agentic verifier with tools for complex verification |

### MCP Servers

Bundle Model Context Protocol servers for external tool integration.

**Location**: `.mcp.json` in plugin root, or inline in plugin.json

```json
{
  "mcpServers": {
    "plugin-database": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": {
        "DB_PATH": "${CLAUDE_PLUGIN_ROOT}/data"
      }
    },
    "plugin-api-client": {
      "command": "npx",
      "args": ["@company/mcp-server", "--plugin-mode"],
      "cwd": "${CLAUDE_PLUGIN_ROOT}"
    }
  }
}
```

- Plugin MCP servers start automatically when enabled
- Appear as standard MCP tools in Claude's toolkit
- Can be configured independently of user MCP servers

### LSP Servers

Language Server Protocol servers for real-time code intelligence.

**Location**: `.lsp.json` in plugin root, or inline in plugin.json

**Provides**: Instant diagnostics, code navigation (go-to-definition, find references), type info

```json
{
  "go": {
    "command": "gopls",
    "args": ["serve"],
    "extensionToLanguage": {
      ".go": "go"
    }
  }
}
```

**Required fields**:

| Field | Description |
|:------|:------------|
| `command` | LSP binary to execute (must be in PATH) |
| `extensionToLanguage` | Maps file extensions to language identifiers |

**Optional fields**:

| Field | Description |
|:------|:------------|
| `args` | Command-line arguments |
| `transport` | `stdio` (default) or `socket` |
| `env` | Environment variables |
| `initializationOptions` | Options passed during initialization |
| `settings` | Settings via `workspace/didChangeConfiguration` |
| `workspaceFolder` | Workspace folder path |
| `startupTimeout` | Max startup wait (ms) |
| `shutdownTimeout` | Max shutdown wait (ms) |
| `restartOnCrash` | Auto-restart on crash |
| `maxRestarts` | Max restart attempts |

**Important**: You must install the language server binary separately. LSP plugins configure connections, they don't include the server itself.

**Official LSP plugins** (from Anthropic marketplace):

| Plugin | Language | Install Command |
|:-------|:---------|:----------------|
| `pyright-lsp` | Python | `pip install pyright` or `npm install -g pyright` |
| `typescript-lsp` | TypeScript | `npm install -g typescript-language-server typescript` |
| `rust-lsp` | Rust | [See rust-analyzer installation](https://rust-analyzer.github.io/manual.html#installation) |

Install the language server binary first, then install the plugin from the marketplace.

### Settings

Ship default configuration with your plugin.

**Location**: `settings.json` at plugin root

Currently only `agent` key is supported. Activates one of the plugin's custom agents as the main thread.

```json
{
  "agent": "security-reviewer"
}
```

---

## Plugin Installation Scopes

| Scope | Settings File | Use Case |
|:------|:-------------|:---------|
| `user` | `~/.claude/settings.json` | Personal, all projects (default) |
| `project` | `.claude/settings.json` | Shared via version control |
| `local` | `.claude/settings.local.json` | Project-specific, gitignored |
| `managed` | `managed-settings.json` | Admin-deployed, read-only |

---

## Plugin Manifest Schema

The `.claude-plugin/plugin.json` file defines metadata and configuration. **The manifest is optional.** If omitted, Claude Code auto-discovers components in default locations and derives name from directory name.

### Complete Schema

```json
{
  "name": "plugin-name",
  "version": "1.2.0",
  "description": "Brief plugin description",
  "author": {
    "name": "Author Name",
    "email": "author@example.com",
    "url": "https://github.com/author"
  },
  "homepage": "https://docs.example.com/plugin",
  "repository": "https://github.com/author/plugin",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"],
  "commands": ["./custom/commands/special.md"],
  "agents": "./custom/agents/",
  "skills": "./custom/skills/",
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json"
}
```

### Required Fields

| Field | Type | Description |
|:------|:-----|:------------|
| `name` | string | Unique identifier (kebab-case, no spaces). Used for namespacing: `plugin-name:skill-name`. |

### Metadata Fields

| Field | Type | Description |
|:------|:-----|:------------|
| `version` | string | Semantic version. `plugin.json` takes priority over marketplace entry. |
| `description` | string | Brief explanation of plugin purpose |
| `author` | object | `{name, email?, url?}` |
| `homepage` | string | Documentation URL |
| `repository` | string | Source code URL |
| `license` | string | SPDX identifier (`"MIT"`, `"Apache-2.0"`) |
| `keywords` | array | Discovery tags |

### Component Path Fields

| Field | Type | Description |
|:------|:-----|:------------|
| `commands` | string\|array | Additional command files/directories |
| `agents` | string\|array | Additional agent files |
| `skills` | string\|array | Additional skill directories |
| `hooks` | string\|array\|object | Hook config paths or inline config |
| `mcpServers` | string\|array\|object | MCP config paths or inline config |
| `outputStyles` | string\|array | Output style files/directories |
| `lspServers` | string\|array\|object | LSP server configs |

### Path Behavior Rules

- Custom paths **supplement** default directories (don't replace them)
- All paths must be relative and start with `./`
- Multiple paths can be specified as arrays

### Environment Variables

| Variable | Description |
|:---------|:------------|
| `${CLAUDE_PLUGIN_ROOT}` | Absolute path to plugin directory |
| `${CWD}` | User's current working directory |

---

## Plugin Caching and File Resolution

Marketplace plugins are copied to `~/.claude/plugins/cache` for security.

- **No path traversal**: Installed plugins cannot reference files outside their directory (`../` won't work)
- **Symlinks honored**: Create symlinks inside plugin directory for external dependencies
- **Version required for updates**: If you change code but don't bump version, users won't see changes due to caching

---

## Plugin Directory Structure

### Standard Layout

```
enterprise-plugin/
├── .claude-plugin/           # Metadata directory (optional)
│   └── plugin.json             # Plugin manifest
├── commands/                 # Legacy command location
│   ├── status.md
│   └── logs.md
├── agents/                   # Subagent definitions
│   ├── security-reviewer.md
│   └── compliance-checker.md
├── skills/                   # Agent Skills (preferred)
│   ├── code-reviewer/
│   │   └── SKILL.md
│   └── pdf-processor/
│       ├── SKILL.md
│       └── scripts/
├── hooks/                    # Hook configurations
│   └── hooks.json
├── settings.json            # Default settings
├── .mcp.json                # MCP server definitions
├── .lsp.json                # LSP server configurations
├── scripts/                 # Utility scripts
├── LICENSE
└── CHANGELOG.md
```

**Warning**: Only `plugin.json` goes in `.claude-plugin/`. All other directories at plugin root.

### File Locations Reference

| Component | Default Location | Purpose |
|:----------|:----------------|:--------|
| Manifest | `.claude-plugin/plugin.json` | Plugin metadata (optional) |
| Commands | `commands/` | Legacy skill markdown files |
| Agents | `agents/` | Subagent markdown files |
| Skills | `skills/` | Skills with `<name>/SKILL.md` (preferred) |
| Hooks | `hooks/hooks.json` | Hook configuration |
| MCP servers | `.mcp.json` | MCP server definitions |
| LSP servers | `.lsp.json` | Language server configurations |
| Settings | `settings.json` | Default configuration (agent key) |

---

## CLI Commands Reference

### Bash CLI

```bash
# Install
claude plugin install <plugin>[@marketplace] [-s user|project|local]

# Uninstall (aliases: remove, rm)
claude plugin uninstall <plugin>[@marketplace] [-s user|project|local]

# Enable/Disable
claude plugin enable <plugin>[@marketplace] [-s scope]
claude plugin disable <plugin>[@marketplace] [-s scope]

# Update
claude plugin update <plugin>[@marketplace] [-s user|project|local|managed]

# Validate
claude plugin validate .

# Debug
claude --debug
```

### In-Session (TUI)

```
/plugin                                    # Interactive plugin manager
/plugin install plugin@marketplace         # Install
/plugin uninstall plugin@marketplace       # Uninstall
/plugin enable plugin@marketplace          # Enable
/plugin disable plugin@marketplace         # Disable

/plugin marketplace add owner/repo         # GitHub marketplace
/plugin marketplace add ./local-path       # Local marketplace
/plugin marketplace add https://url.com/marketplace.json  # Remote
/plugin marketplace list                   # List marketplaces
/plugin marketplace update name            # Refresh
/plugin marketplace remove name            # Remove

/debug                                     # Debug mode in TUI
```

### Local Development

```bash
# Test without installing
claude --plugin-dir ./my-plugin

# Load multiple plugins
claude --plugin-dir ./plugin-one --plugin-dir ./plugin-two
```

---

## Debugging and Development

### Common Issues

| Issue | Cause | Solution |
|:------|:------|:---------|
| Plugin not loading | Invalid `plugin.json` | Validate with `claude plugin validate` |
| Commands not appearing | Wrong directory structure | `commands/` at root, not in `.claude-plugin/` |
| Hooks not firing | Script not executable | `chmod +x script.sh` |
| MCP server fails | Missing `${CLAUDE_PLUGIN_ROOT}` | Use variable for all plugin paths |
| Path errors | Absolute paths used | Use relative paths starting with `./` |
| LSP binary not found | Language server not installed | Install binary (check `/plugin` Errors tab) |

### Hook Troubleshooting

1. Check script is executable: `chmod +x ./scripts/your-script.sh`
2. Verify shebang line: `#!/bin/bash` or `#!/usr/bin/env bash`
3. Check path uses `${CLAUDE_PLUGIN_ROOT}`
4. Event names are case-sensitive: `PostToolUse`, not `postToolUse`
5. Confirm hook type is valid: `command`, `prompt`, or `agent`

### MCP Server Troubleshooting

1. Check command exists and is executable
2. Verify all paths use `${CLAUDE_PLUGIN_ROOT}`
3. Check logs: `claude --debug`
4. Test server manually outside Claude Code

---

## Version Management

Follow semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward-compatible)
- **PATCH**: Bug fixes

**Important**: Claude Code uses version to determine updates. If you change code but don't bump version, existing users won't see changes due to caching.

---

## See Also

- [Plugins Guide](https://code.claude.com/docs/en/plugins) - Tutorials and practical usage
- [Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) - Distribution
- [Skills](https://code.claude.com/docs/en/skills) - Skill development details
- [Subagents](https://code.claude.com/docs/en/sub-agents) - Agent configuration
- [Hooks](https://code.claude.com/docs/en/hooks) - Event handling
- [MCP](https://code.claude.com/docs/en/mcp) - External tool integration
- [Settings](https://code.claude.com/docs/en/settings) - Configuration options
