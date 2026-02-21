---
name: reorder-setup
description: "Use when setting up the reorder system for first time - configures credentials and clasp"
user_invocable: true
---

# /reorder-setup

First-time setup for PB Reorder System.

## Prerequisites

- Node.js installed
- Google Cloud project with BigQuery access
- Google Apps Script API enabled

## Steps

1. Install clasp globally:
   ```bash
   npm install -g @google/clasp
   ```

2. Login to clasp:
   ```bash
   clasp login
   ```

3. Place your service account JSON in `credentials/service-account.json`

4. Configure each brand's `.clasp.json` in `apps_scripts/{brand}/`:
   ```json
   {
     "scriptId": "YOUR_SCRIPT_ID",
     "rootDir": "."
   }
   ```

5. Verify BigQuery access:
   ```bash
   bq query --use_legacy_sql=false "SELECT 1"
   ```

## Brand Script IDs

Each brand needs its own Google Apps Script project. Create scripts at
https://script.google.com and copy the script IDs into `.clasp.json`.
