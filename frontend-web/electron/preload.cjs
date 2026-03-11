const { contextBridge, ipcRenderer } = require('electron');

const bridge = {
  getBackendPort: () => ipcRenderer.invoke('afn:get-backend-port'),
  isElectron: true,
};

contextBridge.exposeInMainWorld('api', bridge);
contextBridge.exposeInMainWorld('electronAPI', bridge);
