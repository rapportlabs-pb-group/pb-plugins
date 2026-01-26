#!/bin/bash
# Create a new plugin from template

set -e

if [ -z "$1" ]; then
  echo "Usage: ./scripts/create-plugin.sh <plugin-name>"
  echo "Example: ./scripts/create-plugin.sh my-awesome-plugin"
  exit 1
fi

PLUGIN_NAME="$1"
PLUGIN_DIR="plugins/$PLUGIN_NAME"

if [ -d "$PLUGIN_DIR" ]; then
  echo "❌ Plugin '$PLUGIN_NAME' already exists"
  exit 1
fi

echo "📦 Creating plugin: $PLUGIN_NAME"

# Create directory structure
mkdir -p "$PLUGIN_DIR/.claude-plugin"
mkdir -p "$PLUGIN_DIR/commands"

# Create plugin.json
cat > "$PLUGIN_DIR/.claude-plugin/plugin.json" << EOF
{
  "name": "$PLUGIN_NAME",
  "version": "1.0.0",
  "description": "TODO: 플러그인 설명을 입력하세요",
  "author": {
    "name": "TODO: 작성자 이름"
  },
  "commands": ["./commands/"],
  "keywords": [],
  "dependencies": [],
  "requirements": {}
}
EOF

# Create default command
cat > "$PLUGIN_DIR/commands/main.md" << 'EOF'
---
description: "메인 명령어 설명"
---

# Main Command

TODO: 명령어 구현 내용을 작성하세요.

## Usage

```
/<plugin-name>:main
```
EOF

# Create README
cat > "$PLUGIN_DIR/README.md" << EOF
# $PLUGIN_NAME

TODO: 플러그인 설명을 입력하세요.

## Installation

\`\`\`bash
/plugin install $PLUGIN_NAME@pb-plugins
\`\`\`

## Commands

| Command | Description |
|---------|-------------|
| main | 메인 명령어 |

## Usage

\`\`\`
/$PLUGIN_NAME:main
\`\`\`
EOF

echo "✅ Plugin created at $PLUGIN_DIR"
echo ""
echo "Next steps:"
echo "  1. Edit $PLUGIN_DIR/.claude-plugin/plugin.json"
echo "  2. Add commands in $PLUGIN_DIR/commands/"
echo "  3. Update $PLUGIN_DIR/README.md"
echo "  4. Add to .claude-plugin/marketplace.json"
echo "  5. Create a PR"
