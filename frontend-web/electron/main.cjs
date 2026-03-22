const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const http = require('http');
const fs = require('fs');
const path = require('path');
const net = require('net');
const { spawn } = require('child_process');
const { URL } = require('url');

const HOST = '127.0.0.1';
const DEFAULT_BACKEND_PORT = 8123;
const DEFAULT_FRONTEND_PORT = 5173;
const DEV_SERVER_START_RETRY_LIMIT = 6;
const FRONTEND_DIR = path.resolve(__dirname, '..');
const ROOT_DIR = path.resolve(FRONTEND_DIR, '..');
const IS_DEV_MODE = !app.isPackaged && process.argv.includes('--dev');

// Electron/Windows 默认可能启用 overlay scrollbars（滚动条仅在滚动时短暂出现）。
// 桌面端设置面板需要“可见且可拖拽”的滚动条以保证可操作性。
app.commandLine.appendSwitch('disable-features', 'OverlayScrollbar,OverlayScrollbars');

const runtime = {
  backendPort: DEFAULT_BACKEND_PORT,
  frontendPort: DEFAULT_FRONTEND_PORT,
  appUrl: '',
  backendProcess: null,
  frontendProcess: null,
  staticServer: null,
  shuttingDown: false,
  cleanedUp: false,
};

const MIME_TYPES = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.wasm': 'application/wasm',
};

function log(scope, message, ...args) {
  console.log(`[electron:${scope}] ${message}`, ...args);
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getBackendDir() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'backend')
    : path.join(ROOT_DIR, 'backend');
}

function getDistDir() {
  return app.isPackaged
    ? path.join(app.getAppPath(), 'dist')
    : path.join(FRONTEND_DIR, 'dist');
}

function getStorageDir() {
  return path.join(app.getPath('userData'), 'storage');
}

function getNpmCommand() {
  return process.platform === 'win32' ? 'npm.cmd' : 'npm';
}

function getNodeCommand() {
  return process.platform === 'win32' ? 'node.exe' : 'node';
}

function getLocalToolBin(toolName) {
  const binName = process.platform === 'win32' ? `${toolName}.cmd` : toolName;
  const toolPath = path.join(FRONTEND_DIR, 'node_modules', '.bin', binName);
  return fs.existsSync(toolPath) ? toolPath : null;
}

function getViteJsEntry() {
  const viteEntry = path.join(FRONTEND_DIR, 'node_modules', 'vite', 'bin', 'vite.js');
  return fs.existsSync(viteEntry) ? viteEntry : null;
}

function hasLocalVite() {
  return Boolean(getLocalToolBin('vite'));
}

function getNodePackageVersion(packageName) {
  const packageJsonPath = path.join(
    FRONTEND_DIR,
    'node_modules',
    ...packageName.split('/'),
    'package.json',
  );

  try {
    if (!fs.existsSync(packageJsonPath)) {
      return null;
    }
    const raw = fs.readFileSync(packageJsonPath, 'utf-8');
    return JSON.parse(raw).version || null;
  } catch {
    return null;
  }
}

function extractMissingModuleName(output) {
  const patterns = [
    /Cannot find module ['"]([^'"]+)['"]/,
    /Cannot find module ([^ \r\n]+)/,
  ];

  for (const pattern of patterns) {
    const match = output.match(pattern);
    if (match?.[1]) {
      return match[1].trim().replace(/[.,:;]+$/, '');
    }
  }

  return null;
}

function resolveRuntimePackageSpec(packageName) {
  let version = null;

  if (packageName.startsWith('@rollup/rollup-')) {
    version = getNodePackageVersion('rollup');
  } else if (packageName.startsWith('@esbuild/')) {
    version = getNodePackageVersion('esbuild');
  }

  return version ? `${packageName}@${version}` : packageName;
}

async function runFrontendNpmInstall(args) {
  const child = spawn(
    getNpmCommand(),
    args,
    {
      cwd: FRONTEND_DIR,
      env: {
        ...process.env,
        NODE_ENV: 'development',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    },
  );

  attachProcessLogging(child, 'npm');

  const spawnResult = await waitForChildSpawn(child);
  if (!spawnResult.ok) {
    throw spawnResult.error || new Error(`Failed to start npm ${args.join(' ')}`);
  }

  const result = await waitForChildExit(child);
  if (result.code !== 0) {
    throw new Error(`npm ${args.join(' ')} failed with exit code ${result.code}`);
  }
}

function getViteProbeCommand() {
  const viteEntry = getViteJsEntry();
  if (process.platform === 'win32' && viteEntry) {
    return [getNodeCommand(), viteEntry, '--version'];
  }

  const localVite = getLocalToolBin('vite');
  if (localVite) {
    return [localVite, '--version'];
  }

  if (viteEntry) {
    return [getNodeCommand(), viteEntry, '--version'];
  }

  return null;
}

async function probeViteRuntime() {
  const probeCommand = getViteProbeCommand();
  if (!probeCommand) {
    return { ok: false, output: 'Local Vite was not found.' };
  }

  const [command, ...args] = probeCommand;
  const child = spawn(
    command,
    args,
    {
      cwd: FRONTEND_DIR,
      env: {
        ...process.env,
        NODE_ENV: 'development',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    },
  );

  let stdout = '';
  let stderr = '';

  if (child.stdout) {
    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
    });
  }
  if (child.stderr) {
    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });
  }

  const spawnResult = await waitForChildSpawn(child);
  if (!spawnResult.ok) {
    return {
      ok: false,
      output: String(spawnResult.error || 'Failed to spawn the Vite probe process'),
    };
  }

  const result = await waitForChildExit(child);
  return {
    ok: result.code === 0,
    output: `${stdout}\n${stderr}`.trim(),
  };
}

async function ensureViteRuntimeDependencies() {
  const repairedModules = new Set();

  for (let attempt = 0; attempt < 3; attempt += 1) {
    const probeResult = await probeViteRuntime();
    if (probeResult.ok) {
      return;
    }

    const missingModule = extractMissingModuleName(probeResult.output || '');
    if (!missingModule || repairedModules.has(missingModule)) {
      const firstLine = (probeResult.output || '').split(/\r?\n/).find(Boolean);
      throw new Error(firstLine || 'Vite runtime self-check failed');
    }

    repairedModules.add(missingModule);
    if (missingModule.startsWith('@rollup/rollup-') || missingModule.startsWith('@esbuild/')) {
      log(
        'vite',
        `Detected missing optional platform runtime package ${missingModule}. ` +
          'This usually means npm omitted optionalDependencies. ' +
          'Running npm install --include=dev --include=optional.',
      );
      await runFrontendNpmInstall(['install', '--include=dev', '--include=optional']);
      continue;
    }

    const packageSpec = resolveRuntimePackageSpec(missingModule);
    log('vite', `Detected missing frontend runtime package ${missingModule}. Installing ${packageSpec}.`);
    await runFrontendNpmInstall(['install', '--no-save', '--no-package-lock', packageSpec]);
  }

  throw new Error('Vite runtime dependencies could not be repaired automatically');
}

function getPythonLaunchers() {
  const backendDir = getBackendDir();
  const candidates = [
    {
      label: 'backend/.venv',
      command: process.platform === 'win32'
        ? path.join(backendDir, '.venv', 'Scripts', 'python.exe')
        : path.join(backendDir, '.venv', 'bin', 'python'),
      prefixArgs: [],
    },
  ];

  if (process.env.PYTHON) {
    candidates.push({
      label: 'PYTHON',
      command: process.env.PYTHON,
      prefixArgs: [],
    });
  }

  if (process.platform === 'win32') {
    candidates.push(
      { label: 'python', command: 'python', prefixArgs: [] },
      { label: 'py', command: 'py', prefixArgs: ['-3'] },
    );
  } else {
    candidates.push(
      { label: 'python3', command: 'python3', prefixArgs: [] },
      { label: 'python', command: 'python', prefixArgs: [] },
    );
  }

  const unique = new Set();
  return candidates.filter((candidate) => {
    if (!candidate.command || unique.has(candidate.command)) {
      return false;
    }
    unique.add(candidate.command);
    return true;
  });
}

function attachProcessLogging(child, scope, outputBuffer = null) {
  const handleChunk = (chunk) => {
    const text = String(chunk).trim();
    if (!text) {
      return;
    }

    if (outputBuffer) {
      outputBuffer.push(text);
    }
    log(scope, text);
  };

  if (child.stdout) {
    child.stdout.on('data', handleChunk);
  }
  if (child.stderr) {
    child.stderr.on('data', handleChunk);
  }
}

function monitorCriticalProcess(child, label) {
  child.on('exit', (code, signal) => {
    if (runtime.shuttingDown) return;
    const detail = `exitCode=${code ?? 'null'} signal=${signal ?? 'null'}`;
    dialog.showErrorBox(`${label} exited`, `${label} stopped unexpectedly. The app will now close.\n${detail}`);
    app.quit();
  });
}

function waitForChildSpawn(child, timeoutMs = 1500) {
  return new Promise((resolve) => {
    let settled = false;

    const finish = (result) => {
      if (settled) return;
      settled = true;
      child.off('spawn', handleSpawn);
      child.off('error', handleError);
      clearTimeout(timer);
      resolve(result);
    };

    const handleSpawn = () => finish({ ok: true });
    const handleError = (error) => finish({ ok: false, error });
    const timer = setTimeout(() => finish({ ok: true }), timeoutMs);

    child.once('spawn', handleSpawn);
    child.once('error', handleError);
  });
}

function waitForChildExit(child) {
  return new Promise((resolve) => {
    if (!child || child.exitCode !== null) {
      resolve({ code: child?.exitCode ?? 0, signal: null });
      return;
    }

    child.once('exit', (code, signal) => {
      resolve({ code: code ?? 0, signal: signal ?? null });
    });
  });
}

function terminateChildProcess(child) {
  if (!child || child.killed || child.exitCode !== null) {
    return;
  }

  try {
    if (process.platform === 'win32') {
      const killer = spawn('taskkill', ['/pid', String(child.pid), '/t', '/f'], {
        stdio: 'ignore',
        windowsHide: true,
      });
      killer.on('error', () => {
        try {
          child.kill();
        } catch {
          // ignore
        }
      });
      return;
    }
    child.kill('SIGTERM');
  } catch {
    // ignore
  }
}

function closeServer(server) {
  return new Promise((resolve) => {
    if (!server) {
      resolve();
      return;
    }
    server.close(() => resolve());
  });
}

function canListenOnHost(port, host) {
  return new Promise((resolve) => {
    const server = net.createServer();

    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close(() => resolve(true));
    });

    server.listen(port, host);
  });
}

async function isPortFree(port) {
  const hostsToProbe = [HOST, '0.0.0.0'];

  for (const host of hostsToProbe) {
    if (!await canListenOnHost(port, host)) {
      return false;
    }
  }

  return true;
}

async function findAvailablePort(preferredPort, excludePorts = new Set()) {
  const isAllowed = async (port) => !excludePorts.has(port) && await isPortFree(port);

  if (await isAllowed(preferredPort)) {
    return preferredPort;
  }

  for (let port = preferredPort + 1; port <= preferredPort + 200; port += 1) {
    if (await isAllowed(port)) {
      return port;
    }
  }

  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, HOST, () => {
      const address = server.address();
      const port = typeof address === 'object' && address ? address.port : preferredPort;
      server.close(() => resolve(port));
    });
  });
}

function httpProbe(targetUrl) {
  return new Promise((resolve) => {
    const req = http.get(targetUrl, { timeout: 2000 }, (res) => {
      res.resume();
      resolve(res.statusCode === 200);
    });

    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
    req.on('error', () => resolve(false));
  });
}

async function waitForHttpReady(targetUrl, timeoutMs = 45000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await httpProbe(targetUrl)) {
      return true;
    }
    await delay(400);
  }
  return false;
}

function waitForChildHttpReady(child, targetUrl, timeoutMs = 45000) {
  return new Promise((resolve) => {
    let settled = false;

    const finish = (result) => {
      if (settled) {
        return;
      }

      settled = true;
      child.off('exit', handleExit);
      resolve(result);
    };

    const handleExit = (code, signal) => {
      finish({
        ready: false,
        reason: 'exit',
        code: code ?? 0,
        signal: signal ?? null,
      });
    };

    child.once('exit', handleExit);

    (async () => {
      const start = Date.now();
      while (!settled && Date.now() - start < timeoutMs) {
        if (await httpProbe(targetUrl)) {
          await delay(250);
          if (!settled && child.exitCode === null) {
            finish({ ready: true, reason: 'ready' });
            return;
          }
        }

        if (settled) {
          return;
        }

        await delay(400);
      }

      finish({ ready: false, reason: 'timeout' });
    })();
  });
}

function isPortConflictError(output, port) {
  const patterns = [
    new RegExp(`Port\\s+${port}\\s+is already in use`, 'i'),
    /\bEADDRINUSE\b/i,
    /\baddress already in use\b/i,
  ];

  return patterns.some((pattern) => pattern.test(output));
}

async function startBackend(backendPort) {
  const backendDir = getBackendDir();
  if (!fs.existsSync(backendDir)) {
    throw new Error(`Backend directory was not found: ${backendDir}`);
  }

  const storageDir = getStorageDir();
  fs.mkdirSync(storageDir, { recursive: true });

  const env = {
    ...process.env,
    AFN_DESKTOP_EDITION: 'Electron',
    AFN_STORAGE_DIR: storageDir,
    PYTHONIOENCODING: 'utf-8',
    PYTHONUNBUFFERED: '1',
  };

  const backendArgs = [
    '-m',
    'uvicorn',
    'app.main:app',
    '--host',
    HOST,
    '--port',
    String(backendPort),
  ];

  let lastError = null;

  for (const launcher of getPythonLaunchers()) {
    if (path.isAbsolute(launcher.command) && !fs.existsSync(launcher.command)) {
      continue;
    }

    log('backend', `Trying backend launcher: ${launcher.label}`);
    const child = spawn(
      launcher.command,
      [...launcher.prefixArgs, ...backendArgs],
      {
        cwd: backendDir,
        env,
        stdio: ['ignore', 'pipe', 'pipe'],
        windowsHide: true,
      },
    );

    attachProcessLogging(child, 'backend');

    const spawnResult = await waitForChildSpawn(child);
    if (!spawnResult.ok) {
      lastError = spawnResult.error;
      continue;
    }

    runtime.backendProcess = child;

    const ready = await waitForHttpReady(`http://${HOST}:${backendPort}/health`, 45000);
    if (ready) {
      monitorCriticalProcess(child, 'AFN Backend');
      log('backend', `Backend is ready: http://${HOST}:${backendPort}`);
      return;
    }

    lastError = new Error(`Backend did not become ready in time (${launcher.label})`);
    terminateChildProcess(child);
    runtime.backendProcess = null;
  }

  throw lastError || new Error('Backend startup failed');
}

async function ensureViteDevDependency() {
  if (!hasLocalVite()) {
    if (process.platform === 'win32' && getViteJsEntry()) {
      log('vite', 'Detected vite.js but vite.cmd is missing on Windows. Repairing frontend dependencies.');
    } else {
      log('vite', 'No platform-ready local Vite executable was found. Repairing frontend dependencies.');
    }

    await runFrontendNpmInstall(['install', '--include=dev', '--include=optional']);

    if (!hasLocalVite()) {
      throw new Error('npm install finished, but a platform-ready Vite executable is still missing');
    }
  }

  await ensureViteRuntimeDependencies();
}

function getViteDevCommand(frontendPort) {
  const viteArgs = ['--host', HOST, '--port', String(frontendPort), '--strictPort'];
  const viteEntry = getViteJsEntry();
  if (process.platform === 'win32' && viteEntry) {
    return [getNodeCommand(), viteEntry, ...viteArgs];
  }

  const localVite = getLocalToolBin('vite');
  if (localVite) {
    return [localVite, ...viteArgs];
  }

  if (viteEntry) {
    return [getNodeCommand(), viteEntry, ...viteArgs];
  }

  throw new Error('Local Vite was not found. Run npm install --include=dev --include=optional first.');
}

async function startViteServer(preferredFrontendPort, backendPort) {
  await ensureViteDevDependency();

  const excludedPorts = new Set([backendPort]);
  let candidatePort = preferredFrontendPort;
  let lastError = null;

  for (let attempt = 1; attempt <= DEV_SERVER_START_RETRY_LIMIT; attempt += 1) {
    candidatePort = await findAvailablePort(candidatePort, excludedPorts);
    excludedPorts.add(candidatePort);

    const [command, ...args] = getViteDevCommand(candidatePort);
    const outputBuffer = [];
    const child = spawn(
      command,
      args,
      {
        cwd: FRONTEND_DIR,
        env: {
          ...process.env,
          VITE_BACKEND_HOST: HOST,
          VITE_BACKEND_PORT: String(backendPort),
          VITE_WEB_PORT: String(candidatePort),
          NODE_ENV: 'development',
        },
        stdio: ['ignore', 'pipe', 'pipe'],
        windowsHide: true,
      },
    );

    attachProcessLogging(child, 'vite', outputBuffer);

    const spawnResult = await waitForChildSpawn(child);
    if (!spawnResult.ok) {
      throw spawnResult.error || new Error('Failed to start the Vite frontend service');
    }

    runtime.frontendProcess = child;

    const readyState = await waitForChildHttpReady(
      child,
      `http://${HOST}:${candidatePort}`,
      45000,
    );

    if (readyState.ready) {
      monitorCriticalProcess(child, 'Vite Frontend Service');
      log('vite', `Frontend dev server is ready: http://${HOST}:${candidatePort}`);
      return candidatePort;
    }

    runtime.frontendProcess = null;
    const combinedOutput = outputBuffer.join('\n');
    const isPortConflict = readyState.reason === 'exit'
      && isPortConflictError(combinedOutput, candidatePort);

    if (isPortConflict && attempt < DEV_SERVER_START_RETRY_LIMIT) {
      log(
        'vite',
        `Port ${candidatePort} became unavailable during startup. Retrying with another port (${attempt}/${DEV_SERVER_START_RETRY_LIMIT}).`,
      );
      lastError = new Error(`Port ${candidatePort} is already in use`);
      continue;
    }

    if (readyState.reason === 'timeout') {
      terminateChildProcess(child);
      throw new Error(`The Vite frontend service did not become ready in time (port ${candidatePort})`);
    }

    const failureDetail = combinedOutput
      .split(/\r?\n/)
      .map((line) => line.trim())
      .find(Boolean);
    const exitDetail = readyState.reason === 'exit'
      ? `exitCode=${readyState.code} signal=${readyState.signal ?? 'null'}`
      : readyState.reason;
    throw new Error(
      failureDetail
        ? `Vite frontend startup failed on port ${candidatePort}: ${failureDetail} (${exitDetail})`
        : `Vite frontend startup failed on port ${candidatePort} (${exitDetail})`,
    );
  }

  throw lastError || new Error('Vite frontend service could not acquire a free port');
}

function proxyToBackend(req, res, backendPort) {
  const proxyReq = http.request(
    {
      host: HOST,
      port: backendPort,
      method: req.method,
      path: req.url,
      headers: {
        ...req.headers,
        host: `${HOST}:${backendPort}`,
      },
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    },
  );

  proxyReq.on('error', (error) => {
    log('proxy', `Proxy request failed: ${error.message}`);
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    }
    res.end(JSON.stringify({ detail: 'Backend proxy request failed' }));
  });

  req.pipe(proxyReq);
}

function serveStaticFile(req, res, distDir) {
  const requestUrl = new URL(req.url || '/', `http://${HOST}`);
  const pathname = decodeURIComponent(requestUrl.pathname);
  const distRoot = path.resolve(distDir);

  if (pathname === '/' || !path.extname(pathname)) {
    const indexFile = path.join(distRoot, 'index.html');
    fs.createReadStream(indexFile)
      .on('error', () => {
        res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end('Failed to read the frontend entry file');
      })
      .once('open', () => {
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      })
      .pipe(res);
    return;
  }

  const normalizedPath = pathname.replace(/^\/+/, '');
  const resolvedFile = path.resolve(distRoot, normalizedPath);
  if (!resolvedFile.startsWith(distRoot)) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('Access denied');
    return;
  }

  fs.stat(resolvedFile, (error, stats) => {
    if (error || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('File not found');
      return;
    }

    const ext = path.extname(resolvedFile).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': contentType });
    fs.createReadStream(resolvedFile).pipe(res);
  });
}

async function startStaticServer(frontendPort, backendPort) {
  const distDir = getDistDir();
  const indexFile = path.join(distDir, 'index.html');
  if (!fs.existsSync(indexFile)) {
    throw new Error('dist/index.html was not found. Run npm run build first.');
  }

  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url || '/', `http://${HOST}`).pathname;
    if (pathname === '/health' || pathname.startsWith('/api')) {
      proxyToBackend(req, res, backendPort);
      return;
    }

    serveStaticFile(req, res, distDir);
  });

  // 长连接/下载（SSE、模型下载等）可能超过 Node 默认 5 分钟请求超时，显式禁用以避免中途断流。
  server.requestTimeout = 0;

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(frontendPort, HOST, () => resolve());
  });

  runtime.staticServer = server;
  log('static', `Static server is ready: http://${HOST}:${frontendPort}`);
}

function createMainWindow() {
  const mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: '#f5f0e5',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.loadURL(runtime.appUrl);

  if (IS_DEV_MODE) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
}

async function bootstrap() {
  runtime.backendPort = await findAvailablePort(DEFAULT_BACKEND_PORT);

  await startBackend(runtime.backendPort);

  if (IS_DEV_MODE) {
    runtime.frontendPort = await startViteServer(DEFAULT_FRONTEND_PORT, runtime.backendPort);
  } else {
    runtime.frontendPort = await findAvailablePort(
      DEFAULT_FRONTEND_PORT,
      new Set([runtime.backendPort]),
    );
    await startStaticServer(runtime.frontendPort, runtime.backendPort);
  }

  runtime.appUrl = `http://${HOST}:${runtime.frontendPort}`;
  createMainWindow();
}

async function cleanup() {
  if (runtime.cleanedUp) {
    return;
  }

  runtime.shuttingDown = true;

  if (runtime.frontendProcess) {
    terminateChildProcess(runtime.frontendProcess);
    runtime.frontendProcess = null;
  }
  if (runtime.backendProcess) {
    terminateChildProcess(runtime.backendProcess);
    runtime.backendProcess = null;
  }
  if (runtime.staticServer) {
    await closeServer(runtime.staticServer);
    runtime.staticServer = null;
  }

  runtime.cleanedUp = true;
}

ipcMain.handle('afn:get-backend-port', () => runtime.backendPort);

app.whenReady()
  .then(bootstrap)
  .catch((error) => {
    log('bootstrap', `Startup failed: ${String(error?.message || error)}`);
    dialog.showErrorBox('AFN Electron startup failed', String(error?.message || error));
    app.quit();
  });

app.on('before-quit', () => {
  runtime.shuttingDown = true;
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0 && runtime.appUrl) {
    createMainWindow();
  }
});

app.on('will-quit', (event) => {
  if (runtime.cleanedUp) {
    return;
  }

  event.preventDefault();
  cleanup().finally(() => {
    app.exit(0);
  });
});
