/// <reference types="vite/client" />

// 统一在此扩展 Web 侧环境变量类型，避免各处出现 `import.meta.env` 的 TS 报错。
// 说明：值在 Vite 构建期注入，运行时不可变。

// Axios 扩展：为请求配置增加 `silent` 字段（用于关闭全局 toast）。
import 'axios';

declare module 'axios' {
  export interface AxiosRequestConfig {
    silent?: boolean;
  }
}

interface ImportMetaEnv {
  readonly VITE_BACKEND_PORT?: string;
  readonly VITE_WEB_PORT?: string;
  readonly VITE_BACKEND_HOST?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
