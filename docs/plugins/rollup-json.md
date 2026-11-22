# Rollup JSON Plugin

## Overview
`agus/rollup-json-plugin` is a **Sonic Screwdriver library plugin** that manages the `@rollup/plugin-json` dependency for any workspace. It can be added to a project via the Sonic CLI, which will:

1. Install `@rollup/plugin-json@^6.1.0` as a dev‑dependency.
2. Locate the nearest `rollup.config.js` (if one exists) and automatically inject the import statement and `json()` entry into the `plugins` array.

This keeps the JSON handling logic separate from core repositories like **uCore** or **uCode**, allowing projects to opt‑in when needed.

## Installation
```bash
# From any directory inside the repository
sonic plugin add agus/rollup-json-plugin --target /path/to/your/workspace
```
The command will:
* Run `npm i -D @rollup/plugin-json@^6.1.0` in the target workspace.
* Patch `rollup.config.js` (if present) to include:
  ```js
  import json from '@rollup/plugin-json';
  // …
  plugins: [json(), /* other plugins */]
  ```

## Usage in a Sonic workflow
Add a step to your workflow that ensures the plugin is present before building:
```yaml
- name: Ensure Rollup JSON plugin
  run: |
    sonic plugin add agus/rollup-json-plugin --target .
```

## Development
The plugin entry point is `src/install.js`. It is a small Node script that can be executed directly:
```bash
node src/install.js --target /path/to/workspace
```
Feel free to modify the script to support additional flags (e.g., `--skip-config`).

## Testing
A unit test lives under `tests/install.test.js`. It creates a temporary workspace, runs the installer, and asserts that:
* `package.json` contains `@rollup/plugin-json` in `devDependencies`.
* `rollup.config.js` (if present) includes the import and `json()` plugin.

Run the test with:
```bash
npm test --prefix plugins/rollup-json
```

---
*Generated on 2026‑11‑21.*