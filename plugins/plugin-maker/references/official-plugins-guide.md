# Plugins Guide (Official Documentation)

> Create custom plugins to extend Claude Code with skills, agents, hooks, MCP servers, and LSP servers.

Source: https://code.claude.com/docs/en/plugins

## When to Use Plugins vs Standalone

| Approach | Skill Names | Best For |
|:---------|:-----------|:---------|
| **Standalone** (`.claude/`) | `/hello` | Personal workflows, quick experiments |
| **Plugins** (`.claude-plugin/plugin.json`) | `/plugin-name:hello` | Sharing, distribution, versioned releases |

**Start standalone** in `.claude/` for quick iteration, then convert to plugin when ready to share.

---

## Quickstart

### Prerequisites

- Claude Code installed (v1.0.33+)

### Create Your First Plugin

**Step 1: Create directory**

```bash
mkdir my-first-plugin
```

**Step 2: Create manifest**

```bash
mkdir my-first-plugin/.claude-plugin
```

Create `my-first-plugin/.claude-plugin/plugin.json`:

```json
{
  "name": "my-first-plugin",
  "description": "A greeting plugin to learn the basics",
  "version": "1.0.0",
  "author": {
    "name": "Your Name"
  }
}
```

**Step 3: Add a skill**

```bash
mkdir -p my-first-plugin/skills/hello
```

Create `my-first-plugin/skills/hello/SKILL.md`:

```yaml
---
description: Greet the user with a friendly message
disable-model-invocation: true
---

Greet the user warmly and ask how you can help them today.
```

**Step 4: Test**

```bash
claude --plugin-dir ./my-first-plugin
```

Then in Claude Code:

```
/my-first-plugin:hello
```

**Step 5: Add arguments**

Update SKILL.md to use `$ARGUMENTS`:

```yaml
---
description: Greet the user with a personalized message
---

Greet the user named "$ARGUMENTS" warmly.
```

Usage: `/my-first-plugin:hello Alex`

---

## Plugin Structure Overview

| Directory | Location | Purpose |
|:----------|:---------|:--------|
| `.claude-plugin/` | Plugin root | Contains `plugin.json` manifest (optional) |
| `skills/` | Plugin root | Agent Skills with `SKILL.md` files (preferred) |
| `commands/` | Plugin root | Legacy slash commands as markdown files |
| `agents/` | Plugin root | Custom agent definitions |
| `hooks/` | Plugin root | Event handlers in `hooks.json` |
| `settings.json` | Plugin root | Default settings (agent key) |
| `.mcp.json` | Plugin root | MCP server configurations |
| `.lsp.json` | Plugin root | LSP server configurations |

**Common mistake**: Don't put `commands/`, `agents/`, `skills/`, or `hooks/` inside `.claude-plugin/`. Only `plugin.json` goes there.

---

## Develop More Complex Plugins

### Add Skills

Skills are the preferred component type. Claude auto-invokes based on task context.

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json
└── skills/
    └── code-review/
        └── SKILL.md
```

SKILL.md needs frontmatter with description:

```yaml
---
name: code-review
description: Reviews code for best practices. Use when reviewing code or checking PRs.
---

When reviewing code, check for:
1. Code organization and structure
2. Error handling
3. Security concerns
4. Test coverage
```

### Add LSP Servers

For languages not covered by official marketplace plugins. Add `.lsp.json`:

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

Users must install the language server binary separately.

### Ship Default Settings

`settings.json` at plugin root. Currently only `agent` key supported:

```json
{
  "agent": "security-reviewer"
}
```

Activates a plugin's custom agent as the main thread.

### Add Hooks

Create `hooks/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh"
          }
        ]
      }
    ]
  }
}
```

Three hook types: `command` (shell), `prompt` (LLM), `agent` (agentic verifier).

### Add MCP Servers

Create `.mcp.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python3",
      "args": ["${CLAUDE_PLUGIN_ROOT}/servers/server.py"],
      "env": {
        "PROJECT_DIR": "${CWD}"
      }
    }
  }
}
```

---

## Test Locally

```bash
# Test without installing
claude --plugin-dir ./my-plugin

# Multiple plugins
claude --plugin-dir ./plugin-one --plugin-dir ./plugin-two
```

Restart Claude Code after making changes.

Test components:
- Skills: `/plugin-name:skill-name`
- Agents: Check `/agents`
- Hooks: Verify triggers
- Debug: `claude --debug` or `/debug`

---

## Convert Standalone to Plugin

### Migration Steps

1. **Create plugin structure**:

```bash
mkdir -p my-plugin/.claude-plugin
```

Create `my-plugin/.claude-plugin/plugin.json`:

```json
{
  "name": "my-plugin",
  "description": "Migrated from standalone configuration",
  "version": "1.0.0"
}
```

2. **Copy existing files**:

```bash
cp -r .claude/commands my-plugin/
cp -r .claude/agents my-plugin/
cp -r .claude/skills my-plugin/
```

3. **Migrate hooks**: Copy `hooks` object from `.claude/settings.json` to `my-plugin/hooks/hooks.json`.

4. **Test**:

```bash
claude --plugin-dir ./my-plugin
```

### What Changes

| Standalone | Plugin |
|:-----------|:-------|
| One project only | Shareable via marketplaces |
| `/skill-name` | `/plugin-name:skill-name` |
| Files in `.claude/` | Files in plugin directory |
| Hooks in `settings.json` | Hooks in `hooks/hooks.json` |
| Manual copy to share | Install with `/plugin install` |

---

## Share Plugins

1. **Documentation**: Include README.md
2. **Version**: Use semantic versioning in plugin.json
3. **Marketplace**: Distribute through plugin marketplaces
4. **Test**: Have team members test before wider distribution

---

## Next Steps

- [Discover and Install Plugins](https://code.claude.com/docs/en/discover-plugins)
- [Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [Plugins Reference](https://code.claude.com/docs/en/plugins-reference)
- [Skills](https://code.claude.com/docs/en/skills)
- [Subagents](https://code.claude.com/docs/en/sub-agents)
- [Hooks](https://code.claude.com/docs/en/hooks)
- [MCP](https://code.claude.com/docs/en/mcp)
