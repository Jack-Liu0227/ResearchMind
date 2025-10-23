/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_WS_URL?: string
  readonly VITE_API_PORT?: string
  readonly VITE_WS_PORT?: string
  readonly VITE_WS_PATH?: string
  readonly VITE_PROXY_PORT?: string
  readonly VITE_FRONTEND_PORT?: string
  readonly VITE_FRONTEND_HOST?: string
  readonly VITE_HMR_HOST?: string
  readonly VITE_HMR_PORT?: string
  readonly VITE_HMR_PROTOCOL?: string
  readonly VITE_ALLOWED_HOSTS?: string
  readonly VITE_APP_TITLE?: string
  readonly MODE: string
  readonly DEV: boolean
  readonly PROD: boolean
  readonly SSR: boolean
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

