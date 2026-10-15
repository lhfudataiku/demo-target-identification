import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import dkuWebapp from '@dataiku/vite-plugin-dku-webapp'
import { defineConfig } from 'vite'

export default defineConfig({
  // dkuWebapp() (build only) emits dist/dss-main.js, the DSS webapp JS entry that
  // loads the bundle through dataiku.getWebAppBackendUrl(), and reduces
  // dist/index.html to body markup. dss_webapp/deploy.sh uses both as the
  // webapp's js and html parameters (see webapp/DEPLOYMENT.md).
  plugins: [vue(), tailwindcss(), dkuWebapp()],

  // base: './' makes all built asset paths relative — required for the DSS
  // iframe embedding where the app is served from a non-root path.
  base: './',

  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      // Proxy /api calls to the FastAPI backend in local dev.
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },

  // @dataiku/ea-ui-kit and bs-blueprint ship raw .vue/.ts sources: pre-bundling
  // them duplicates reka-ui's injection context in dev. Their runtime deps are
  // pre-bundled instead.
  optimizeDeps: {
    exclude: ['@dataiku/ea-ui-kit', 'bs-blueprint'],
    include: [
      'reka-ui',
      '@vueuse/core',
      'class-variance-authority',
      'clsx',
      'tailwind-merge',
      '@tanstack/vue-table',
      'vee-validate',
      'vue-sonner',
      'embla-carousel-vue',
      'vaul-vue',
      '@internationalized/date',
      'vue-input-otp',
    ],
  },

  build: {
    outDir: 'dist',
    // DSS project libraries are text-only: inline the kit's font files as data URIs.
    assetsInlineLimit: 32 * 1024,
    // Single-bundle output — code splitting breaks DSS resource loading.
    rollupOptions: {
      output: {
        entryFileNames: 'assets/index.js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/index.[ext]',
      },
    },
  },

  resolve: {
    // Keep a single Vue instance (reka-ui and friends list vue as a peer dep).
    dedupe: ['vue', 'vue-router'],
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
