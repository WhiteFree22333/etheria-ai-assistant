/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface Window {
  pywebview?: {
    api: Record<string, (...args: any[]) => Promise<any>>
  }
  __vueApp?: any
}
