# .mcp.json Schema Reference

MCP (Model Context Protocol) server configuration file for plugins.

## Basic Structure

```json
{
  "mcpServers": {
    "server-name": {
      "command": "string",
      "args": ["array", "of", "strings"],
      "env": {
        "KEY": "value"
      }
    }
  }
}
```

## Environment Variables

| Variable | Description |
|:---------|:------------|
| `${CLAUDE_PLUGIN_ROOT}` | Plugin installation path |
| `${CWD}` | User's current working directory |

## Examples

### Python MCP Server

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python3",
      "args": ["${CLAUDE_PLUGIN_ROOT}/servers/server.py"],
      "env": {
        "PYTHONPATH": "${CLAUDE_PLUGIN_ROOT}",
        "PROJECT_DIR": "${CWD}"
      }
    }
  }
}
```

### Node.js MCP Server

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/servers/server.js"],
      "env": {
        "NODE_ENV": "production"
      }
    }
  }
}
```

### npx Server (External Package)

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### With Working Directory

```json
{
  "mcpServers": {
    "plugin-api-client": {
      "command": "npx",
      "args": ["@company/mcp-server", "--plugin-mode"],
      "cwd": "${CLAUDE_PLUGIN_ROOT}"
    }
  }
}
```

## Path Rules

- Plugin scripts use `${CLAUDE_PLUGIN_ROOT}`
- User data/credentials use `${CWD}`

```json
{
  "mcpServers": {
    "data-processor": {
      "command": "python3",
      "args": [
        "${CLAUDE_PLUGIN_ROOT}/servers/processor.py",
        "--config", "${CWD}/config.json",
        "--output", "${CWD}/output"
      ]
    }
  }
}
```

## Integration Behavior

- Plugin MCP servers start automatically when the plugin is enabled
- Servers appear as standard MCP tools in Claude's toolkit
- Can be configured independently of user MCP servers
- Server capabilities integrate seamlessly with Claude's existing tools

## Inline in plugin.json

MCP servers can also be defined inline in plugin.json instead of a separate file:

```json
{
  "name": "my-plugin",
  "mcpServers": {
    "my-server": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"]
    }
  }
}
```
