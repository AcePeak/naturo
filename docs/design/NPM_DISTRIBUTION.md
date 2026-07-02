# NPM Distribution Design — `npx naturo mcp`

## Goal

Allow users to use naturo via `npm install naturo` or `npx naturo` **without installing Python**.

## Approach: Thin Wrapper + Platform Binary (Recommended)

### Architecture

```
npm package (naturo)          ~5KB
  └── postinstall script
        └── Detect platform+arch
        └── Download matching binary from GitHub Releases
              ├── naturo-win-x64.exe     (~40-60MB)
              ├── naturo-linux-x64       (~40-60MB)
              └── naturo-macos-arm64     (~40-60MB)
```

### User Experience

```bash
# Install
npm install -g naturo
# Or one-time usage
npx naturo see
npx naturo mcp
```

### Precedents

| Tool | Approach | Package Size |
|------|----------|-------------|
| esbuild | npm thin wrapper + platform binary | ~9MB |
| turbo | npm thin wrapper + platform binary | ~20MB |
| playwright | npm + on-demand browser download | ~2MB + browsers |
| prisma | npm + on-demand engine binary download | ~5MB + engine |

### Implementation Steps

#### Step 1: Standalone Binary (Nuitka)

Use Nuitka to compile Python + naturo into a single-file executable:

```bash
nuitka --standalone --onefile \
  --include-package=naturo \
  --include-data-files=naturo_core.dll=naturo_core.dll \
  --output-filename=naturo.exe \
  naturo/__main__.py
```

CI matrix:
- Windows x64 (windows-latest)
- Linux x64 (ubuntu-latest)
- macOS arm64 (macos-latest)

Artifacts are uploaded to GitHub Release assets.

#### Step 2: npm Package

```
packages/naturo-npm/
  ├── package.json
  ├── bin/naturo.js          # CLI entry point
  ├── install.js             # postinstall download script
  └── lib/
      └── platform.js        # platform detection + download logic
```

**package.json:**
```json
{
  "name": "naturo",
  "version": "0.3.0",
  "description": "Windows desktop automation for AI agents",
  "bin": { "naturo": "bin/naturo.js" },
  "scripts": { "postinstall": "node install.js" },
  "os": ["win32", "linux", "darwin"],
  "cpu": ["x64", "arm64"]
}
```

**bin/naturo.js:**
```javascript
#!/usr/bin/env node
const { execFileSync } = require('child_process');
const path = require('path');
const binary = path.join(__dirname, '..', 'bin', process.platform === 'win32' ? 'naturo.exe' : 'naturo');
execFileSync(binary, process.argv.slice(2), { stdio: 'inherit' });
```

**install.js:**
```javascript
// 1. Detect platform + arch
// 2. Build download URL: https://github.com/AcePeak/naturo/releases/download/vX.Y.Z/naturo-{platform}-{arch}{.exe}
// 3. Download to bin/
// 4. chmod +x (non-Windows)
```

#### Step 3: MCP Scenario

```bash
# AI agent configuration
npx naturo mcp --transport stdio
# Or
npx naturo mcp --transport sse --port 8080
```

Zero-config MCP server startup — this is the core value proposition of the npm package.

### Alternatives Considered (Rejected)

#### ❌ Option B: Embed Python Inside npm Package

```
node_modules/naturo/
  python-3.12-embed/   (~15-40MB)
  naturo/              (Python source)
```

Rejected because:
- Large package size (slow npm install)
- Python Embedded doesn't work well on Linux/macOS
- Updating Python source requires republishing the npm package
- Permission and path issues are common

#### ❌ Option C: npm Wrapper Requiring Python

Rejected because:
- Poor user experience ("please install Python first")
- Python version compatibility issues pushed onto users
- Violates the "zero dependencies" goal

### Version Synchronization

- npm version numbers stay in sync with PyPI version numbers
- GitHub Releases include:
  - PyPI package (automatic)
  - npm package (manual or CI)
  - Platform binaries (CI-built)

### Size Optimization

Default Nuitka output can be 60-100MB. Optimization strategies:
- `--lto=yes` (Link-Time Optimization)
- Exclude unnecessary standard library modules
- UPX compression (optional, but may trigger antivirus false positives)
- Target: **<50MB per platform**

### Dependency Matrix

| Install Method | Requires Python | Requires Node | Requires Compiler |
|----------------|:--------------:|:------------:|:-----------------:|
| `pip install naturo` | ✅ ≥3.10 | ❌ | ❌ |
| `npx naturo` | ❌ | ✅ ≥16 | ❌ |
| GitHub Release download | ❌ | ❌ | ❌ |

### Timeline

- v0.4.0: Standalone binary (Nuitka CI) + GitHub Release
- v0.4.0: npm package + postinstall download
- v0.5.0: Optimize package size, add auto-update mechanism
