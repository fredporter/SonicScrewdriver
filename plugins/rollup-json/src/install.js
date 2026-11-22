const fs = require('fs');
const path = require('path');

function addDevDependency(packageJsonPath, depName, depVersion = '^6.1.0') {
  if (!fs.existsSync(packageJsonPath)) {
    console.warn(`package.json not found at ${packageJsonPath}`);
    return false;
  }
  const pkg = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
  pkg.devDependencies = pkg.devDependencies || {};
  if (!pkg.devDependencies[depName]) {
    pkg.devDependencies[depName] = depVersion;
    fs.writeFileSync(packageJsonPath, JSON.stringify(pkg, null, 2) + '\n', 'utf8');
    console.log(`Added ${depName}@${depVersion} to devDependencies in ${packageJsonPath}`);
    return true;
  }
  console.log(`${depName} already present in devDependencies`);
  return false;
}

function patchRollupConfig(configPath) {
  if (!fs.existsSync(configPath)) {
    console.warn(`rollup.config.js not found at ${configPath}`);
    return false;
  }
  let content = fs.readFileSync(configPath, 'utf8');
  if (content.includes('@rollup/plugin-json')) {
    console.log('rollup.config.js already includes @rollup/plugin-json');
    return false;
  }

  const importStmt = "import json from '@rollup/plugin-json';\n";
  content = importStmt + content;

  // Insert json() into plugins array if present, otherwise create or append
  if (/plugins:\s*\[/.test(content)) {
    content = content.replace(/plugins:\s*\[([^\]]*)\]/, (_match, p1) => {
      const existing = p1.trim();
      const plugins = existing ? `json(), ${existing}` : 'json()';
      return `plugins: [${plugins}]`;
    });
  } else if (/export\s+default\s*\{/.test(content)) {
    content = content.replace(/export\s+default\s*\{/, 'export default {\n  plugins: [json()],');
  }

  fs.writeFileSync(configPath, content, 'utf8');
  console.log(`Patched ${configPath} with @rollup/plugin-json`);
  return true;
}

function install(targetDir = process.cwd()) {
  const pkgPath = path.join(targetDir, 'package.json');
  const configPath = path.join(targetDir, 'rollup.config.js');

  addDevDependency(pkgPath, '@rollup/plugin-json');
  patchRollupConfig(configPath);
}

function main() {
  const args = process.argv.slice(2);
  let targetDir = process.cwd();
  const targetIdx = args.indexOf('--target');
  if (targetIdx !== -1 && args[targetIdx + 1]) {
    targetDir = path.resolve(args[targetIdx + 1]);
  }
  install(targetDir);
}

if (require.main === module) {
  main();
}

module.exports = {
  install,
  addDevDependency,
  patchRollupConfig,
};
