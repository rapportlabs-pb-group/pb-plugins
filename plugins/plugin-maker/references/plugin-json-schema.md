# plugin.json Schema Reference

## Location

`.claude-plugin/plugin.json` (inside `.claude-plugin/` directory at plugin root)

**The manifest is optional.** If omitted, Claude Code auto-discovers components in default locations and derives the plugin name from the directory name.

## Required Fields

```json
{
  "name": "string"  // Plugin name (required if manifest exists). Kebab-case, no spaces.
}
```

The `name` is used for namespacing: `plugin-name:skill-name`.

## Metadata Fields

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Plugin description",
  "author": {
    "name": "Author Name",
    "email": "author@example.com",
    "url": "https://github.com/author"
  },
  "homepage": "https://docs.example.com/plugin",
  "repository": "https://github.com/user/repo",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"]
}
```

## Component Path Fields

```json
{
  "commands": ["./custom/commands/special.md"],
  "agents": "./custom/agents/",
  "skills": "./custom/skills/",
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json"
}
```

### Type Details

| Field | Type | Description |
|:------|:-----|:------------|
| `commands` | string\|array | Additional command files/directories |
| `agents` | string\|array | Additional agent files |
| `skills` | string\|array | Additional skill directories |
| `hooks` | string\|array\|object | Hook config paths or inline config |
| `mcpServers` | string\|array\|object | MCP config paths or inline config |
| `outputStyles` | string\|array | Output style files/directories |
| `lspServers` | string\|array\|object | LSP server configs |

## Full Example

```json
{
  "name": "enterprise-tools",
  "version": "2.1.0",
  "description": "Enterprise workflow automation tools",
  "author": {
    "name": "DevTools Team",
    "email": "dev@company.com"
  },
  "homepage": "https://docs.company.com/plugins",
  "repository": "https://github.com/company/enterprise-tools",
  "license": "MIT",
  "keywords": ["enterprise", "workflow", "automation"],
  "skills": "./skills/",
  "agents": "./agents/",
  "hooks": "./hooks/hooks.json",
  "mcpServers": "./.mcp.json",
  "lspServers": "./.lsp.json",
  "outputStyles": "./styles/"
}
```

## Path Rules

- Custom paths **supplement** default directories (don't replace them)
- All paths must be relative and start with `./`
- Multiple paths can be specified as arrays

## Validation

- `name`: Required. Lowercase letters, numbers, hyphens only. No spaces.
- `version`: Semver format recommended (`x.y.z`). **Must bump for updates** (cache won't refresh otherwise).
- `description`: Brief, under 100 characters recommended.
- If `version` is also set in marketplace entry, `plugin.json` takes priority.
