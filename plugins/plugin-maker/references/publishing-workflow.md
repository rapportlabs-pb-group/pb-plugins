# Publishing Workflow Guide

Step-by-step guide for publishing a plugin to the PB marketplace.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| `gh` | GitHub CLI for auth + PR | `brew install gh` |
| `git` | Version control | `brew install git` |
| `jq` | JSON processing | `brew install jq` |
| `python3` | Run publish script | Pre-installed on macOS |
| `rsync` | File copying | Pre-installed on macOS |

### GitHub Setup (One-Time)

```bash
# 1. Install GitHub CLI
brew install gh

# 2. Authenticate
gh auth login
# Choose: GitHub.com -> HTTPS -> Login with browser

# 3. Verify
gh auth status
```

## Publishing Steps

### Step 1: Ensure Plugin is Ready (~2 min)

Your plugin must have:
- [ ] `.claude-plugin/plugin.json` with name, version, description
- [ ] At least one skill in `skills/` or command in `commands/`
- [ ] `README.md` with installation and usage instructions
- [ ] `.gitignore` covering secrets and dev files

### Step 2: Run Secrets Scan (~1 min)

**This is mandatory.** The publish script will refuse to continue if secrets are found.

```bash
/plugin-maker:check-secrets
```

Or run the script directly:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_secrets.py" ./my-plugin
```

Fix any failures before proceeding. Common fixes:
- Remove `.env` files, add to `.gitignore`
- Replace hardcoded API keys with `${VARIABLE}` references
- Replace `/Users/yourname/` paths with `${CLAUDE_PLUGIN_ROOT}`

### Step 3: Test Locally (~3 min)

```bash
claude --plugin-dir ./my-plugin
```

Verify all skills and commands work as expected.

### Step 4: Publish (~2 min)

```bash
# Use the guided sub-skill (recommended)
/plugin-maker:publish
```

Or run the script directly:

```bash
# Dry run first (no network calls)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish_to_pb.py" ./my-plugin --dry-run

# Actual publish
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish_to_pb.py" ./my-plugin
```

The script will:
1. Verify prerequisites (gh, git, jq)
2. Run secrets scan (hard gate)
3. Validate plugin structure
4. Clone pb-plugins repo
5. Copy your plugin (excluding secrets)
6. Update marketplace.json
7. Create a PR

### Step 5: Wait for Review (~varies)

After the PR is created:
1. Check PR status: `gh pr status`
2. CI validation runs automatically
3. A maintainer will review and merge

### Step 6: Announce Installation (~1 min)

After merge, users can install with:
```bash
/plugin marketplace add rapportlabs-pb-group/pb-plugins
/plugin install my-plugin@pb-plugins
```

## Updating an Existing Plugin

```bash
# Use the guided sub-skill
/plugin-maker:publish

# Or run directly with version bump
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/publish_to_pb.py" ./my-plugin --version-bump patch
```

Version bump options: `patch` (1.0.0 -> 1.0.1), `minor` (1.0.0 -> 1.1.0), `major` (1.0.0 -> 2.0.0)

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `gh: command not found` | GitHub CLI not installed | `brew install gh` |
| `jq: command not found` | jq not installed | `brew install jq` |
| `gh auth status` fails | Not authenticated | `gh auth login` |
| Secrets scan fails | Sensitive files detected | Remove files or add to .gitignore |
| "Permission denied" on push | Not an org member | Script auto-forks. Check fork permissions. |
| Validation fails | Missing plugin.json fields | Add required fields (name, version, description) |
| "Plugin already exists" | Duplicate name | Use `--version-bump` for updates |
| PR creation fails | Branch already exists | Delete remote branch: `git push origin --delete add/my-plugin` |
