import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { readFileSync } from 'node:fs';

// versão do aplicativo = a mesma do service worker (public/sw.js)
const VERSAO_APP = /const VERSAO = '([^']+)'/.exec(readFileSync('public/sw.js', 'utf8'))?.[1] ?? 'dev';

// modo "artefato" = versão publicada dentro da Claude (caminhos relativos)
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  define: { __VERSAO__: JSON.stringify(VERSAO_APP) },
  base: mode === 'artefato' ? './' : '/',
  server: { host: '0.0.0.0', port: 3000, strictPort: true, allowedHosts: true },
  preview: { host: '0.0.0.0', port: 3000, strictPort: true, allowedHosts: true },
  build: { outDir: 'dist', assetsInlineLimit: 0 },
}));
