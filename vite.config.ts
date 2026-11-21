import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// modo "artefato" = versão publicada dentro da Claude (caminhos relativos)
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'artefato' ? './' : '/',
  server: { host: '0.0.0.0', port: 3000, strictPort: true, allowedHosts: true },
  preview: { host: '0.0.0.0', port: 3000, strictPort: true, allowedHosts: true },
  build: { outDir: 'dist', assetsInlineLimit: 0 },
}));
