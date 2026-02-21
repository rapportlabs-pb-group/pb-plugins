#!/usr/bin/env python3
"""
Secrets Scanner for Plugin Distribution

Scans a plugin directory for sensitive information before distribution.

Usage:
    python3 check_secrets.py [plugin-path]
    python3 check_secrets.py .                      # Scan current directory
    python3 check_secrets.py --json .               # Machine-readable output
    python3 check_secrets.py --strict .             # Exit 1 on warnings too

Checks:
    1. Sensitive file patterns (.env, credentials/, *.key, etc.)
    2. Hardcoded secrets in code (API keys, tokens, etc.)
    3. Hardcoded user paths (/Users/xxx/.claude/, /home/xxx/.claude/)
    4. .gitignore configuration validation
"""

from __future__ import annotations

import argparse
import json as json_mod
import re
import sys
from pathlib import Path

# --- Sensitive file patterns ---

SENSITIVE_FILE_PATTERNS = [
    # Environment variables
    ".env", ".env.*", "*.env",
    # Credential directories
    "credentials/", "secrets/", "keys/", "auth/", "private/",
    # Key files
    "*.key", "*.pem", "*.p12", "*.pfx", "*.crt",
    "*_key.json", "*_token.json", "*_credentials.json",
    "service_account*.json", "client_secret*.json",
    # Cloud provider
    "gcloud-*.json", "*-sa.json", "*-service-account.json",
    # Bot tokens
    "slack_token*", "slack_bot*", "discord_token*", "bot_token*",
    # Databases
    "*.sqlite", "*.db",
    # SSH / GPG
    "id_rsa*", "id_ed25519*", "*.gpg",
    # Development files
    "CLAUDE.md",
]

# --- Content regex patterns ---

SECRET_PATTERNS = [
    # API Keys
    (r'["\']?api[_-]?key["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "API Key"),
    (r'["\']?apikey["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "API Key"),

    # Tokens
    (r'["\']?token["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "Token"),
    (r'["\']?access[_-]?token["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "Access Token"),
    (r'["\']?refresh[_-]?token["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "Refresh Token"),
    (r'["\']?auth[_-]?token["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-]{20,}["\']', "Auth Token"),

    # Slack
    (r'xoxb-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{20,}', "Slack Bot Token"),
    (r'xoxp-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{20,}', "Slack User Token"),
    (r'xoxa-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{20,}', "Slack App Token"),
    (r'xoxs-[0-9]{10,}-[0-9]{10,}-[a-zA-Z0-9]{20,}', "Slack Session Token"),
    (r'https://hooks\.slack\.com/services/[A-Z0-9]+/[A-Z0-9]+/[a-zA-Z0-9]+', "Slack Webhook"),

    # Discord
    (r'[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27}', "Discord Bot Token"),
    (r'https://discord(app)?\.com/api/webhooks/[0-9]+/[a-zA-Z0-9_-]+', "Discord Webhook"),

    # AWS
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'["\']?aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\'][a-zA-Z0-9/+=]{40}["\']', "AWS Secret Key"),

    # GCP
    (r'["\']?private[_-]?key["\']?\s*[:=]\s*["\']-----BEGIN', "GCP Private Key"),
    (r'"type"\s*:\s*"service_account"', "GCP Service Account JSON"),
    (r'"client_email"\s*:\s*"[^"]+@[^"]+\.iam\.gserviceaccount\.com"', "GCP Service Account"),

    # Azure
    (r'AccountKey=[A-Za-z0-9+/=]{86,}', "Azure Storage Account Key"),

    # Generic Secrets
    (r'["\']?password["\']?\s*[:=]\s*["\'][^"\']{8,}["\']', "Password"),
    (r'["\']?secret["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-]{16,}["\']', "Secret"),
    (r'["\']?private[_-]?key["\']?\s*[:=]\s*["\'][a-zA-Z0-9_\-/+=]{20,}["\']', "Private Key"),

    # Database URLs with credentials
    (r'(mysql|postgresql|mongodb|redis)://[^"\'\s]+:[^"\'\s]+@', "Database URL with credentials"),

    # Webhook URLs
    (r'https://[a-z]+\.webhook\.office\.com/[^\s"\']+', "Microsoft Webhook"),
]

# --- Hardcoded user path patterns ---

USER_PATH_PATTERNS = [
    (r'/Users/[a-zA-Z0-9_.-]+/\.claude/', "Hardcoded macOS user path"),
    (r'/home/[a-zA-Z0-9_.-]+/\.claude/', "Hardcoded Linux user path"),
    (r'C:\\Users\\[a-zA-Z0-9_.-]+\\\.claude\\', "Hardcoded Windows user path"),
    (r'/Users/[a-zA-Z0-9_.-]+/Library/', "Hardcoded macOS Library path"),
    (r'/home/[a-zA-Z0-9_.-]+/\.config/', "Hardcoded Linux config path"),
    (r'~/\.claude/', "Hardcoded home-relative .claude path (use ${CLAUDE_PLUGIN_ROOT})"),
]

# --- Exclusions ---

EXCLUDE_EXTENSIONS = {'.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.jpg', '.png', '.gif', '.ico', '.woff', '.woff2', '.ttf'}
EXCLUDE_DIRS = {'__pycache__', '.git', 'node_modules', '.venv', 'venv', '.plugin-state'}

PLACEHOLDER_MARKERS = ['your_', 'xxx', 'example', 'placeholder', 'changeme', 'todo', 'fixme', '<your', '${', 'env.', 'process.env']

CODE_EXTENSIONS = {'.py', '.js', '.ts', '.json', '.yml', '.yaml', '.sh', '.md', '.txt', '.cfg', '.ini', '.toml', '.env'}


def match_pattern(filename: str, pattern: str) -> bool:
    """Check if filename matches a glob pattern."""
    import fnmatch
    return fnmatch.fnmatch(filename.lower(), pattern.lower())


def find_sensitive_files(plugin_path: Path) -> list[tuple[Path, str]]:
    """Scan for sensitive files and directories."""
    findings = []

    for item in plugin_path.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in item.parts):
            continue

        if item.is_dir():
            for pattern in SENSITIVE_FILE_PATTERNS:
                if pattern.endswith("/") and match_pattern(item.name + "/", pattern):
                    findings.append((item, f"Sensitive directory: {pattern}"))
                    break
        else:
            if item.suffix in EXCLUDE_EXTENSIONS:
                continue
            for pattern in SENSITIVE_FILE_PATTERNS:
                if not pattern.endswith("/") and match_pattern(item.name, pattern):
                    findings.append((item, f"Sensitive file: {pattern}"))
                    break

    return findings


def _is_comment_line(line: str, in_block_comment: bool) -> tuple[bool, bool]:
    """Check if line is a comment. Returns (is_comment, still_in_block_comment)."""
    stripped = line.strip()

    # Block comment end
    if in_block_comment:
        if '*/' in stripped or '-->' in stripped or '"""' in stripped or "'''" in stripped:
            return True, False
        return True, True

    # Single-line comments
    if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('<!--'):
        return True, False

    # Block comment start
    if stripped.startswith('/*') or stripped.startswith('"""') or stripped.startswith("'''"):
        # Single-line block comment like /* ... */
        if '*/' in stripped or stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
            return True, False
        return True, True

    return False, False


def scan_file_content(file_path: Path) -> list[tuple[int, str, str]]:
    """Scan file contents for hardcoded secrets."""
    findings = []

    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        in_block = False

        for line_num, line in enumerate(lines, 1):
            is_comment, in_block = _is_comment_line(line, in_block)
            if is_comment:
                continue

            for pattern, secret_type in SECRET_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    if not any(p in line.lower() for p in PLACEHOLDER_MARKERS):
                        snippet = line.strip()[:100]
                        findings.append((line_num, secret_type, snippet))
                    break
    except Exception:
        pass

    return findings


def scan_user_paths(file_path: Path) -> list[tuple[int, str, str]]:
    """Scan file contents for hardcoded user paths."""
    findings = []

    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        in_block = False

        for line_num, line in enumerate(lines, 1):
            is_comment, in_block = _is_comment_line(line, in_block)
            if is_comment:
                continue

            for pattern, desc in USER_PATH_PATTERNS:
                if re.search(pattern, line):
                    if '${' not in line and '$HOME' not in line and '~/' not in line:
                        snippet = line.strip()[:100]
                        findings.append((line_num, desc, snippet))
                    break
    except Exception:
        pass

    return findings


def check_gitignore(plugin_path: Path) -> list[str]:
    """Validate .gitignore configuration."""
    warnings = []
    gitignore_path = plugin_path / ".gitignore"

    if not gitignore_path.exists():
        warnings.append("No .gitignore file found")
        return warnings

    content = gitignore_path.read_text()

    required_patterns = [
        (".env", "Environment variable files"),
        ("credentials", "Credential directories"),
        ("*.key", "Key files"),
        ("CLAUDE.md", "Claude development config"),
    ]

    for pattern, description in required_patterns:
        if pattern not in content:
            warnings.append(f"Missing '{pattern}' ({description}) in .gitignore")

    return warnings


def scan_plugin(plugin_path: Path) -> dict:
    """Run full plugin scan."""
    results = {
        "path": str(plugin_path),
        "sensitive_files": [],
        "hardcoded_secrets": [],
        "hardcoded_paths": [],
        "gitignore_warnings": [],
        "passed": True,
    }

    # Layer 1: Sensitive file detection
    sensitive_files = find_sensitive_files(plugin_path)
    results["sensitive_files"] = [(str(f), desc) for f, desc in sensitive_files]

    # Layer 2: Content scanning (secrets + user paths)
    for file_path in plugin_path.rglob("*"):
        if not file_path.is_file() or file_path.suffix not in CODE_EXTENSIONS:
            continue
        if any(part in EXCLUDE_DIRS for part in file_path.parts):
            continue

        # Hardcoded secrets
        for line_num, secret_type, snippet in scan_file_content(file_path):
            results["hardcoded_secrets"].append({
                "file": str(file_path.relative_to(plugin_path)),
                "line": line_num,
                "type": secret_type,
                "snippet": snippet,
            })

        # Hardcoded user paths
        for line_num, path_type, snippet in scan_user_paths(file_path):
            results["hardcoded_paths"].append({
                "file": str(file_path.relative_to(plugin_path)),
                "line": line_num,
                "type": path_type,
                "snippet": snippet,
            })

    # Layer 3: .gitignore validation
    results["gitignore_warnings"] = check_gitignore(plugin_path)

    # Final verdict
    if results["sensitive_files"] or results["hardcoded_secrets"] or results["hardcoded_paths"]:
        results["passed"] = False

    return results


def print_results(results: dict) -> bool:
    """Print human-readable scan results."""
    print("\n" + "=" * 60)
    print("Secrets Scan Results")
    print("=" * 60)
    print(f"Path: {results['path']}\n")

    # Sensitive files
    if results["sensitive_files"]:
        print("[FAIL] Sensitive files detected")
        print("-" * 40)
        for file_path, desc in results["sensitive_files"]:
            print(f"  X {file_path}")
            print(f"    -> {desc}")
        print()
    else:
        print("[PASS] No sensitive files\n")

    # Hardcoded secrets
    if results["hardcoded_secrets"]:
        print("[FAIL] Hardcoded secrets detected")
        print("-" * 40)
        for secret in results["hardcoded_secrets"]:
            print(f"  X {secret['file']}:{secret['line']}")
            print(f"    -> {secret['type']}")
            s = secret['snippet']
            print(f"    -> {s[:60]}{'...' if len(s) > 60 else ''}")
        print()
    else:
        print("[PASS] No hardcoded secrets\n")

    # Hardcoded user paths
    if results["hardcoded_paths"]:
        print("[FAIL] Hardcoded user paths detected")
        print("-" * 40)
        for path_info in results["hardcoded_paths"]:
            print(f"  X {path_info['file']}:{path_info['line']}")
            print(f"    -> {path_info['type']}")
            print(f"    -> {path_info['snippet'][:60]}...")
        print()
    else:
        print("[PASS] No hardcoded user paths\n")

    # .gitignore warnings
    if results["gitignore_warnings"]:
        print("[WARN] .gitignore issues")
        print("-" * 40)
        for warning in results["gitignore_warnings"]:
            print(f"  ! {warning}")
        print()
    else:
        print("[PASS] .gitignore configured correctly\n")

    # Summary
    print("=" * 60)
    if results["passed"] and not results["gitignore_warnings"]:
        print("PASSED - Safe for distribution.")
    elif results["passed"]:
        print("WARNINGS found but distributable. Review warnings above.")
    else:
        print("FAILED - Fix issues before distribution.")
        print("\nRemediation:")
        print("  1. Remove sensitive files or add to .gitignore")
        print("  2. Replace hardcoded secrets with environment variables")
        print("  3. Replace hardcoded paths with ${CLAUDE_PLUGIN_ROOT} or ~")
        print("  4. Re-run check_secrets.py")
    print("=" * 60 + "\n")

    return results["passed"]


def main():
    parser = argparse.ArgumentParser(
        description="Scan plugin for secrets and sensitive information before distribution"
    )
    parser.add_argument(
        "plugin_path",
        nargs="?",
        default=".",
        help="Plugin directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on warnings too (not just failures)",
    )

    args = parser.parse_args()
    plugin_path = Path(args.plugin_path).resolve()

    if not plugin_path.exists():
        print(f"Error: Path not found: {plugin_path}", file=sys.stderr)
        sys.exit(1)

    if not plugin_path.is_dir():
        print(f"Error: Not a directory: {plugin_path}", file=sys.stderr)
        sys.exit(1)

    results = scan_plugin(plugin_path)

    if args.json_output:
        print(json_mod.dumps(results, indent=2, ensure_ascii=False))
    else:
        print_results(results)

    # Exit code
    if not results["passed"]:
        sys.exit(1)
    elif args.strict and results["gitignore_warnings"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
