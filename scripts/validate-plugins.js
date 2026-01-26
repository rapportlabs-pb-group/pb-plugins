#!/usr/bin/env node
/**
 * Validates individual plugin structure and plugin.json
 */

const fs = require('fs');
const path = require('path');

const PLUGINS_DIR = path.join(__dirname, '..', 'plugins');

function validatePluginJson(pluginPath, pluginName) {
  const pluginJsonPath = path.join(pluginPath, '.claude-plugin', 'plugin.json');

  if (!fs.existsSync(pluginJsonPath)) {
    console.error(`❌ ${pluginName}: Missing .claude-plugin/plugin.json`);
    return false;
  }

  let pluginJson;
  try {
    pluginJson = JSON.parse(fs.readFileSync(pluginJsonPath, 'utf8'));
  } catch (e) {
    console.error(`❌ ${pluginName}: Invalid plugin.json - ${e.message}`);
    return false;
  }

  // Required fields
  const required = ['name', 'version', 'description'];
  for (const field of required) {
    if (!pluginJson[field]) {
      console.error(`❌ ${pluginName}: Missing required field '${field}' in plugin.json`);
      return false;
    }
  }

  // Name must match directory
  if (pluginJson.name !== pluginName) {
    console.error(`❌ ${pluginName}: plugin.json name '${pluginJson.name}' doesn't match directory`);
    return false;
  }

  // Version format check
  if (!/^\d+\.\d+\.\d+/.test(pluginJson.version)) {
    console.error(`❌ ${pluginName}: Invalid version format '${pluginJson.version}' (use semver)`);
    return false;
  }

  return true;
}

function validatePluginStructure(pluginPath, pluginName) {
  const commandsDir = path.join(pluginPath, 'commands');

  if (!fs.existsSync(commandsDir)) {
    console.error(`❌ ${pluginName}: Missing commands/ directory`);
    return false;
  }

  const commands = fs.readdirSync(commandsDir).filter(f => f.endsWith('.md'));
  if (commands.length === 0) {
    console.error(`❌ ${pluginName}: No command files (.md) in commands/`);
    return false;
  }

  // Check for forbidden files
  const forbidden = ['CLAUDE.md', '.env', 'credentials.json'];
  for (const file of forbidden) {
    if (fs.existsSync(path.join(pluginPath, file))) {
      console.error(`❌ ${pluginName}: Forbidden file found: ${file}`);
      return false;
    }
  }

  return true;
}

function main() {
  console.log('🔍 Validating plugins...\n');

  if (!fs.existsSync(PLUGINS_DIR)) {
    console.error('❌ plugins/ directory not found');
    process.exit(1);
  }

  const plugins = fs.readdirSync(PLUGINS_DIR).filter(f =>
    fs.statSync(path.join(PLUGINS_DIR, f)).isDirectory()
  );

  if (plugins.length === 0) {
    console.log('⚠️  No plugins found');
    process.exit(0);
  }

  let hasErrors = false;

  for (const pluginName of plugins) {
    const pluginPath = path.join(PLUGINS_DIR, pluginName);

    const jsonValid = validatePluginJson(pluginPath, pluginName);
    const structureValid = validatePluginStructure(pluginPath, pluginName);

    if (jsonValid && structureValid) {
      console.log(`✅ ${pluginName}`);
    } else {
      hasErrors = true;
    }
  }

  console.log(`\n${hasErrors ? '❌ Validation failed' : '✅ All plugins valid'}`);
  process.exit(hasErrors ? 1 : 0);
}

main();
