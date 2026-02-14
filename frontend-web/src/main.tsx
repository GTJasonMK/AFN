import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

/**
 * Web 版在浏览器运行时没有桌面端 Bridge（Electron/pywebview 等）。
 * 为避免代码直接访问 `window.api.getBackendPort()` 造成白屏，这里提供最小兜底实现：
 * - Bridge 已存在：不覆盖
 * - Bridge 不存在：返回固定端口（默认 8123，可用 VITE_BACKEND_PORT 覆盖）
 */
function ensureBackendPortBridge() {
  const raw = (import.meta as any)?.env?.VITE_BACKEND_PORT
  const envPort = Number(raw)
  const defaultPort = Number.isFinite(envPort) && envPort > 0 ? envPort : 8123

  const ensure = (target: any) => {
    if (!target || typeof target !== 'object') return
    if (typeof target.getBackendPort !== 'function') {
      target.getBackendPort = async () => defaultPort
    }
  }

  const w = window as any

  // Electron 常见：contextBridge.exposeInMainWorld('api', ...)
  if (!w.api || typeof w.api !== 'object') w.api = {}
  ensure(w.api)

  // 兼容部分实现：contextBridge.exposeInMainWorld('electronAPI', ...)
  if (!w.electronAPI || typeof w.electronAPI !== 'object') w.electronAPI = {}
  ensure(w.electronAPI)

  // pywebview：window.pywebview.api
  if (!w.pywebview || typeof w.pywebview !== 'object') w.pywebview = {}
  if (!w.pywebview.api || typeof w.pywebview.api !== 'object') w.pywebview.api = {}
  ensure(w.pywebview.api)
}

ensureBackendPortBridge()

const appElement = import.meta.env.DEV ? (
  <App />
) : (
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

ReactDOM.createRoot(document.getElementById('root')!).render(appElement)
