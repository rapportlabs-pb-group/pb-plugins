#!/usr/bin/env node
/**
 * Validates marketplace.json structure and content
 */

const fs = require('fs');
const path = require('path');

const MARKETPLACE_PATH = path.join(__dirname, '..', '.claude-plugin', 'marketplace.json');

function validateMarketplace() {
  console.log('📋 Validating marketplace.json...\n');

  if (!fs.existsSync(MARKETPLACE_PATH)) {
    console.error('❌ marketplace.json not found');
    process.exit(1);
  }

  let marketplace;
  try {
    const content = fs.readFileSync(MARKETPLACE_PATH, 'utf8');
    marketplace = JSON.parse(content);
  } catch (e) {
    console.error('❌ Invalid JSON:', e.message);
    process.exit(1);
  }

  // Required fields
  const requiredFields = ['name', 'owner', 'metadata', 'plugins'];
  for (const field of requiredFields) {
    if (!marketplace[field]) {
      console.error(`❌ Missing required field: ${field}`);
      process.exit(1);
    }
  }

  // Validate plugins array
  if (!Array.isArray(marketplace.plugins)) {
    console.error('❌ plugins must be an array');
    process.exit(1);
  }

  const pluginNames = new Set();
  for (const plugin of marketplace.plugins) {
    // Check required plugin fields
    if (!plugin.name || !plugin.source || !plugin.version) {
      console.error(`❌ Plugin missing required fields: ${JSON.stringify(plugin)}`);
      process.exit(1);
    }

    // Check for duplicates
    if (pluginNames.has(plugin.name)) {
      console.error(`❌ Duplicate plugin name: ${plugin.name}`);
      process.exit(1);
    }
    pluginNames.add(plugin.name);

    // Check source path exists
    const sourcePath = path.join(__dirname, '..', plugin.source);
    if (!fs.existsSync(sourcePath)) {
      console.error(`❌ Plugin source not found: ${plugin.source}`);
      process.exit(1);
    }

    console.log(`  ✅ ${plugin.name}@${plugin.version}`);
  }

  console.log(`\n✅ marketplace.json valid (${marketplace.plugins.length} plugins)`);
}

validateMarketplace();
