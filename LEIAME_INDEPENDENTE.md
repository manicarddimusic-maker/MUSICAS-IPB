# Hinário — versão independente da Manus

- Todas as 187 páginas e as 3 capas dos cards estão em `public/midias/` (nada mais depende da Manus).
- Site comum (Railway, Vercel, qualquer servidor estático com fallback SPA): `pnpm install && pnpm build` → pasta `dist/`.
- Versão publicada na Claude (rotas por #hash, PDF pelo download da Claude): `pnpm build:artefato`.
- Para acrescentar músicas: coloque a foto em `public/midias/`, edite `dados/fonte.json` (caminho `/midias/arquivo.jpg`), rode `python3 scripts/gerar_catalogo.py` e faça o build.
- Não use mais `scripts/urls_absolutas.py` (ele apontava para o domínio da Manus).
