const { execSync } = require('child_process');
const { mkdtempSync, writeFileSync, readFileSync, rmSync } = require('fs');
const { join } = require('path');
const os = require('os');
const assert = require('node:assert');

// Support both node:test runner and Jest
let describeFn = globalThis.describe;
let testFn = globalThis.test || globalThis.it;
let beforeFn = globalThis.beforeAll || globalThis.before;
let afterFn = globalThis.afterAll || globalThis.after;

if (!describeFn) {
  const nodeTest = require('node:test');
  describeFn = nodeTest.describe;
  testFn = nodeTest.test;
  beforeFn = nodeTest.before;
  afterFn = nodeTest.after;
}

describeFn('rollup-json-plugin installer', () => {
  const tempDir = mkdtempSync(join(os.tmpdir(), 'rollup-json-test-'));
  const workspace = join(tempDir, 'workspace');
  const configPath = join(workspace, 'rollup.config.js');

  beforeFn(() => {
    execSync('mkdir -p ' + workspace);
    writeFileSync(join(workspace, 'package.json'), JSON.stringify({ name: 'temp', version: '0.0.0' }, null, 2));
    writeFileSync(configPath, 'export default { plugins: [] };\n');
    // Run installer script
    const installScript = join(__dirname, '../src/install.js');
    execSync(`node "${installScript}" --target "${workspace}"`, { stdio: 'inherit' });
  });

  afterFn(() => {
    rmSync(tempDir, { recursive: true, force: true });
  });

  testFn('adds @rollup/plugin-json to devDependencies', () => {
    const pkg = JSON.parse(readFileSync(join(workspace, 'package.json'), 'utf8'));
    assert.strictEqual(pkg.devDependencies?.['@rollup/plugin-json'], '^6.1.0');
  });

  testFn('updates rollup.config.js with import and plugin', () => {
    const content = readFileSync(configPath, 'utf8');
    assert.match(content, /import\s+json\s+from\s+['"]@rollup\/plugin-json['"]/);
    assert.match(content, /plugins:\s*\[.*json\(\)/);
  });
});
