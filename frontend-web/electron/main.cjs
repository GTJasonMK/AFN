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
const FRONTEND_DIR = path.resolve(__dirname, '..');
const ROOT_DIR = path.resolve(FRONTEND_DIR, '..');
const IS_DEV_MODE = !app.isPackaged && process.argv.includes('--dev');

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

function attachProcessLogging(child, scope) {
  if (child.stdout) {
    child.stdout.on('data', (chunk) => {
      const text = String(chunk).trim();
      if (text) log(scope, text);
    });
  }
  if (child.stderr) {
    child.stderr.on('data', (chunk) => {
      const text = String(chunk).trim();
      if (text) log(scope, text);
    });
  }
}

function monitorCriticalProcess(child, label) {
  child.on('exit', (code, signal) => {
    if (runtime.shuttingDown) return;
    const detail = `退出码=${code ?? 'null'} 信号=${signal ?? 'null'}`;
    dialog.showErrorBox(`${label} 已退出`, `${label} 运行中断，应用即将关闭。\n${detail}`);
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

function isPortFree(port) {
  return new Promise((resolve) => {
    const server = net.createServer();

    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close(() => resolve(true));
    });

    server.listen(port, HOST);
  });
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

async function startBackend(backendPort) {
  const backendDir = getBackendDir();
  if (!fs.existsSync(backendDir)) {
    throw new Error(`未找到 backend 目录: ${backendDir}`);
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

    log('backend', `尝试使用 ${launcher.label} 启动后端`);
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
      monitorCriticalProcess(child, 'AFN 后端');
      log('backend', `后端已就绪: http://${HOST}:${backendPort}`);
      return;
    }

    lastError = new Error(`后端未在预期时间内就绪（${launcher.label}）`);
    terminateChildProcess(child);
    runtime.backendProcess = null;
  }

  throw lastError || new Error('后端启动失败');
}

async function startViteServer(frontendPort, backendPort) {
  const child = spawn(
    getNpmCommand(),
    ['run', 'dev', '--', '--host', HOST, '--port', String(frontendPort), '--strictPort'],
    {
      cwd: FRONTEND_DIR,
      env: {
        ...process.env,
        VITE_BACKEND_HOST: HOST,
        VITE_BACKEND_PORT: String(backendPort),
        VITE_WEB_PORT: String(frontendPort),
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    },
  );

  attachProcessLogging(child, 'vite');
  runtime.frontendProcess = child;

  const ready = await waitForHttpReady(`http://${HOST}:${frontendPort}`, 45000);
  if (!ready) {
    terminateChildProcess(child);
    runtime.frontendProcess = null;
    throw new Error('Vite 前端服务未在预期时间内就绪');
  }

  monitorCriticalProcess(child, 'Vite 前端服务');
  log('vite', `前端开发服务已就绪: http://${HOST}:${frontendPort}`);
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
    log('proxy', `代理请求失败: ${error.message}`);
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    }
    res.end(JSON.stringify({ detail: '后端代理请求失败' }));
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
        res.end('前端入口文件读取失败');
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
    res.end('禁止访问');
    return;
  }

  fs.stat(resolvedFile, (error, stats) => {
    if (error || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('文件不存在');
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
    throw new Error('未找到 dist/index.html，请先运行 npm run build');
  }

  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url || '/', `http://${HOST}`).pathname;
    if (pathname === '/health' || pathname.startsWith('/api')) {
      proxyToBackend(req, res, backendPort);
      return;
    }

    serveStaticFile(req, res, distDir);
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(frontendPort, HOST, () => resolve());
  });

  runtime.staticServer = server;
  log('static', `静态服务已就绪: http://${HOST}:${frontendPort}`);
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
  runtime.frontendPort = await findAvailablePort(
    DEFAULT_FRONTEND_PORT,
    new Set([runtime.backendPort]),
  );

  await startBackend(runtime.backendPort);

  if (IS_DEV_MODE) {
    await startViteServer(runtime.frontendPort, runtime.backendPort);
  } else {
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
    dialog.showErrorBox('AFN Electron 启动失败', String(error?.message || error));
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
