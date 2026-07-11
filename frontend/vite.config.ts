import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Docker Desktop + WSL2 bind mounts don't reliably propagate inotify
    // events for files edited from the Windows side (/mnt/c/...), so the
    // dev server's file watcher can silently miss changes without this.
    watch: {
      usePolling: true,
    },
  },
})
