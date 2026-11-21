# Plano — Hinário da Igreja (app web instalável)

## Objetivo

Um app (site instalável no celular, tablet e computador) para achar rápido a música do culto. Três seções:
**Hinos** (Novo Cântico, ordem crescente de número), **Cânticos espirituais** (ordem alfabética pelo título) e
**Salmos** (ordem crescente de número). Cada música abre as páginas fotografadas, com zoom e navegação entre
páginas. O conteúdo é atualizado pelo próprio Manus sempre que o usuário manda novas fotos: a música entra na
ordem certa e ganha seu atalho de número (ou de título) automaticamente.

## Requisitos confirmados pelo usuário

- Tela inicial com as três seções; tocar numa seção abre a lista completa na ordem dela.
- Em Hinos e Salmos, um campo para digitar o número e ir direto à música; a lista fica em ordem crescente.
- Em Cânticos espirituais, a lista fica em ordem alfabética pelo título.
- Uma música pode ter várias fotos (versões, tons diferentes, fotos repetidas): **todas** aparecem, agrupadas na mesma entrada.
- Folhas com mais de uma música são desmembradas: cada música vira página própria.
- Fotos sem número legível: perguntar ao usuário qual é o número.
- Funcionar instalado no aparelho e sem internet (PWA + cache das páginas já abertas).
- Mais hinos podem ser acrescentados depois; o app se reorganiza sozinho.

## Como funciona

- **Dados**: `dados/fonte.json` lista cada música (número, título, imagens). `scripts/gerar_catalogo.py` gera
  `public/data/catalogo.json`, que é o que o app lê. Acrescentar uma música = acrescentar um item e rodar o script.
- **Imagens**: fotos tratadas (endireitadas, recortadas, com iluminação e nitidez melhoradas, até 2200 px) sobem
  para o armazenamento do projeto (`manus-upload-file --webdev`) e o catálogo guarda o caminho `/manus-storage/...`.
- **Front-end**: React + TypeScript + Vite, sem servidor nem banco. Rotas: `/`, `/:secao`, `/:secao/:item`.
- **Offline/instalação**: `manifest.webmanifest` + `sw.js` (cache do app, do catálogo e das imagens já vistas).
- **Publicação**: build estático (`dist`) com fallback de SPA para as rotas.

## Estrutura

```
dados/fonte.json            lista das músicas (fonte da verdade)
scripts/gerar_catalogo.py   gera public/data/catalogo.json
public/data/catalogo.json   catálogo lido pelo app
public/manifest.webmanifest, public/sw.js, public/icons/
src/App.tsx                 rotas e telas de lista
src/Inicio.tsx              tela inicial com as três capas
src/Leitor.tsx              leitor com zoom, swipe e navegação
src/catalogo.ts             tipos, ordenação e carga do catálogo
src/styles.css              identidade visual
```

## Design — "Hinário de Couro"

- **Movimento**: encadernação clássica de hinário, couro e dourado envelhecido.
- **Princípios**: reverência sem peso, leitura em luz baixa (contraste alto), números grandes e fáceis de tocar, pouca coisa na tela.
- **Cores**: verde-oliva profundo (#2F4436) como couro, dourado envelhecido (#C9A227) para filetes e números, papel creme (#F7F2E6) nas listas.
- **Layout**: capa com ornamento central e três cartões de retrato, não uma grade de recursos; listas como índice de livro.
- **Elementos assinatura**: filete dourado com cruz, cartões com véu escuro e capa fotográfica, número em selo de papel.
- **Interação**: toque abre; no leitor, deslizar troca de página e pinça/double-tap amplia.
- **Animação**: entrada suave dos cartões em cascata; transições curtas, nada chamativo.
- **Tipografia**: Libre Baskerville nos títulos (voz de hinário), Inter nos textos e controles.
- **Essência**: o hinário da igreja no bolso, feito para achar o hino em segundos — reverente, direto, acolhedor.
- **Voz**: "Músicas do nosso culto", "Ir para o hino número…".
- **Marca**: monograma dourado de cruz sobre couro verde.
