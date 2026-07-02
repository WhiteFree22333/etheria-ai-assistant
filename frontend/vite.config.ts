import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// outDir 相对路径，Vite 会自动从项目根解析
export default defineConfig({
  plugins: [vue()],
  root: '.',
  base: './',
  build: {
    outDir: '../ui/static',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    strictPort: true,
  },
})
