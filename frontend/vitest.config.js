import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  test: {
    // Node по умолчанию: чистые модули не должны платить за поднятие DOM на каждый файл.
    // Тесты разметки просят jsdom сами — строкой `@vitest-environment jsdom` в начале файла.
    environment: 'node',
    include: ['src/**/*.spec.js'],
  },
})
