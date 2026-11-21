# Hinário da Igreja — Especificação completa do aplicativo

Documento para replicar o app **exatamente** como está hoje (telas, estilos, dados, PDF, PWA e rotina de fotos).
Versão publicada: https://hinario-fql7afdj.manus.space

---

## 1. Objetivo

Aplicativo web instalável (PWA) para uma igreja consultar as músicas do culto a partir de **fotos das folhas do hinário**.
Cada seção tem uma lista em ordem e um leitor de páginas. Também gera **PDF** de cada seção, com todas as músicas em ordem, para compartilhar ou abrir no GoodNotes.

Seções (cards da tela inicial):

| id | Título | Subtítulo | Ordem |
|---|---|---|---|
| `hinos` | Hinos | Novo Cântico | número crescente |
| `canticos` | Cânticos espirituais | Ordem alfabética | alfabética (pelo título) |
| `salmos` | Salmos | Livro dos Salmos | número crescente |
| `lavras` | Músicas Lavras | Canções do retiro | alfabética |

Estado atual do acervo: **106 hinos**, **191 páginas** de imagem; cânticos, salmos e Lavras ainda vazios (aparecem como “Em breve”).

---

## 2. Stack

- Vite 5 + React 18 + TypeScript 5 (sem framework de UI, CSS próprio)
- `react-router-dom` 6 (BrowserRouter)
- `jspdf` 4 (carregado sob demanda, só quando o usuário exporta)
- PWA manual: `manifest.webmanifest` + service worker próprio (`public/sw.js`)
- Build estático (`dist`), com fallback SPA para todas as rotas

`package.json`:

```json
{
  "name": "hinario",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 3000",
    "build": "tsc -b && vite build",
    "preview": "vite preview --host 0.0.0.0 --port 3000"
  },
  "dependencies": {
    "jspdf": "^4.2.1",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2"
  },
  "devDependencies": {
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.2",
    "typescript": "^5.6.3",
    "vite": "^5.4.9"
  }
}
```

`vite.config.ts`:

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { host: '0.0.0.0', port: 3000, strictPort: true, allowedHosts: true },
  preview: { host: '0.0.0.0', port: 3000, strictPort: true, allowedHosts: true },
  build: { outDir: 'dist', assetsInlineLimit: 0 },
});
```

Observação: se o `pnpm install` reclamar de “Ignored build scripts: core-js”, criar `.npmrc` com `verify-deps-before-run=false` e em `pnpm-workspace.yaml` a seção `allowBuilds: { core-js: false, esbuild: true }`.

---

## 3. Estrutura de arquivos

```
hinario/
├─ index.html
├─ package.json
├─ vite.config.ts
├─ tsconfig.json / tsconfig.node.json
├─ app.config.ts                  # logo do projeto (só no ambiente Manus)
├─ dados/
│  └─ fonte.json                  # catálogo-fonte (o que é editado à mão)
├─ scripts/
│  └─ gerar_catalogo.py           # fonte.json -> public/data/catalogo.json
├─ public/
│  ├─ data/catalogo.json          # gerado
│  ├─ manifest.webmanifest
│  ├─ sw.js                       # service worker (cache offline)
│  ├─ manus-routes.json           # rotas do host (fallback SPA + no-cache)
│  └─ icons/icone-180.png, icone-192.png, icone-512.png, icone-maskable.png
└─ src/
   ├─ main.tsx                    # React root + proteção contra tela branca + registro do SW
   ├─ App.tsx                     # rotas, tela de lista da seção, página do leitor
   ├─ Inicio.tsx                  # tela inicial com os 4 cards
   ├─ Leitor.tsx                  # leitor de páginas (zoom, swipe, girar)
   ├─ catalogo.ts                 # tipos + carregamento + ordenação + rótulos
   ├─ exportarPdf.ts              # geração do PDF com capa
   └─ styles.css                  # tema “Hinário de Couro”
```

---

## 4. Modelo de dados

### 4.1 `dados/fonte.json` (editado à mão)

```json
{
  "hinos": [
    { "num": 61, "titulo": "Ações de Gratidão",
      "paginas": ["/manus-storage/h061a_c954ad59.jpg", "/manus-storage/h061b_add708ba.jpg"] }
  ],
  "canticos": [
    { "titulo": "Nome do cântico", "paginas": ["https://.../imagem.jpg"] }
  ],
  "salmos": [
    { "num": 23, "titulo": "O Senhor é meu pastor", "paginas": ["https://.../imagem.jpg"] }
  ],
  "lavras": [
    { "titulo": "Nome da música", "paginas": ["https://.../imagem.jpg"] }
  ]
}
```

- `paginas` aceita string ou objeto `{ "img": "...", "tom": "..." }` (o `tom` vira legenda).
- Hinos e salmos usam `num`; cânticos e Lavras usam só `titulo`.
- As imagens hoje ficam no armazenamento do Manus (`/manus-storage/...`). Em outra hospedagem, basta trocar as URLs (podem ser absolutas).

### 4.2 `public/data/catalogo.json` (gerado por `scripts/gerar_catalogo.py`)

```json
{
  "geradoEm": "2026-11-21",
  "secoes": [
    {
      "id": "hinos",
      "titulo": "Hinos",
      "subtitulo": "Novo Cântico",
      "ordem": "numero",
      "itens": [
        {
          "id": "hino-61",
          "num": 61,
          "titulo": "Ações de Gratidão",
          "paginas": [{ "img": "/manus-storage/h061a_...jpg", "alt": "Hino 61 — Ações de Gratidão — página 1" }]
        }
      ]
    }
  ]
}
```

Regras do gerador:

- `id` = `hino-{num}` | `salmo-{num}` | `cantico-{slug}` | `lavras-{slug}` (slug sem acento, minúsculo, hífens).
- `alt` = `Hino {num} — {titulo} — página {i}` (mesma lógica para salmo/cântico).
- As seções são sempre as quatro, nesta ordem: hinos, cânticos, salmos, lavras.

Execução: `python3 scripts/gerar_catalogo.py`.

---

## 5. Telas e comportamento

### 5.1 Tela inicial (`/` — `Inicio.tsx`)

- Fundo escuro verde com textura; ornamento “✝” entre duas linhas douradas.
- Texto: eyebrow “Hinário da Igreja”; título “Músicas do nosso culto”; subtítulo “Hinos, cânticos espirituais, salmos e músicas Lavras”.
- Grade de 4 cards (`cartao`): imagem de fundo + véu escuro em degradê + subtítulo dourado em maiúsculas espaçadas + título em serifada + linha de info (“106 músicas · por número” ou “Em breve”).
- Cada card entra com animação `surgir` escalonada (`animationDelay: i * 90ms`).
- Rodapé: botão “Instalar no aparelho” (evento `beforeinstallprompt`) ou dica “No celular ou tablet, use ‘Adicionar à tela de início’”.
- Capas dos cards: imagens fixas em `/manus-storage/async-images/...` (hinos, cânticos, salmos) e o card Lavras reutiliza a capa de cânticos com filtro `hue-rotate(140deg)` e véu mais quente.

### 5.2 Lista da seção (`/{secaoId}` — `SecaoPage` em `App.tsx`)

- Cabeçalho fixo (sticky) verde: botão voltar “‹”, subtítulo em caixa alta, título, contador em pílula.
- **Botão “Exportar PDF (todas em ordem)”** logo abaixo do cabeçalho, com barra de progresso (“Gerando PDF… 34/191”).
- Barra de busca fixa:
  - seções numéricas: campo “Ir para o hino número…” + botão “Ir” (Enter também); salta para o número exato ou para o próximo maior.
  - seções alfabéticas: campo “Buscar cântico pelo nome…” (filtra ao digitar).
- Lista ordenada: número/rótulo em pílula, título, e selo “N págs” quando o item tem mais de uma página.
- Vazio: “Ainda não há músicas nesta seção.” ou “Nada encontrado com esse número ou nome.”

Ordenação: numérica (`num` crescente, desempate por título) ou alfabética sem acentos.

### 5.3 Leitor (`/{secaoId}/{itemId}` — `Leitor.tsx`)

Tela cheia, fundo quase preto.

- Barra superior: voltar, rótulo + título, número e “página atual/total”.
- Área da folha:
  - imagem sempre **inteira** (`object-fit: contain`, `max-width/max-height: 100%`);
  - **pinça** para zoom (1×–5×) e arrastar quando ampliado;
  - **duplo toque/clique** alterna zoom 1×/2×;
  - **toque** na metade esquerda volta página/anterior, na direita avança (só com zoom 1×; movimento > 12 px cancela para não navegar durante a rolagem);
  - setas ‹ › nas laterais quando há mais de uma página;
  - teclado: ← → trocam de página, Esc volta à lista;
  - botão **⟳ “Girar a folha”** (canto inferior direito, sempre visível com zoom 1×): gira a página 90° ocupando a tela inteira, sem cortar (`width = altura da área`, `height = largura da área`, `object-fit: contain`); toca de novo e volta. O toque no botão não navega (`stopPropagation`).
  - O giro **não** é automático: as folhas abrem como na foto.
- Navegação inferior: item anterior / posição / próximo item.

### 5.4 Exportar PDF (`src/exportarPdf.ts`)

- Gera na hora, no próprio aparelho, com `jsPDF` importado dinamicamente.
- **Capa**: fundo verde `#2f4436`, moldura dupla dourada, “HINÁRIO DA IGREJA” em dourado, título da seção em caixa alta (serifada), filete, subtítulo em itálico, “N músicas”, data em português.
- **Uma página por imagem**, na ordem da lista:
  - A4 paisagem quando a foto é mais larga que alta (margem 4 mm), A4 retrato caso contrário (margem 8 mm);
  - imagem centralizada com `contain` (nunca corta);
  - legenda discreta no rodapé: “Hino 61 – Ações de Gratidão” (ou “Salmo 23 – …”, ou o título nas seções alfabéticas).
- Imagens rebaixadas para no máximo 1500 px no maior lado, JPEG 0,85, antes de entrar no PDF (mantém o arquivo em ~50 MB para 192 páginas).
- Nome do arquivo: `Hinário - {Título da seção}.pdf`, baixado com `Blob` + link temporário.

---

## 6. Design system (“Hinário de Couro”)

```css
:root {
  --oliva: #2f4436;
  --oliva-escuro: #1d2a22;
  --oliva-claro: #3d5747;
  --dourado: #c9a227;
  --dourado-claro: #e3c766;
  --papel: #f7f2e6;
  --papel-2: #efe7d6;
  --tinta: #2a2a24;
  --tinta-suave: #6b6656;
  --vinho: #6d2b32;
  --azul: #243b55;
  --sombra: 0 18px 40px rgba(0, 0, 0, 0.35);
  --serif: 'Libre Baskerville', Georgia, 'Times New Roman', serif;
  --sans: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
```

- Fontes via Google Fonts no `index.html`: Libre Baskerville (400/700, itálico) e Inter (400/500/600).
- Cantos arredondados generosos (14–20 px), bordas douradas translúcidas, sombras suaves.
- Cabeçalhos verdes com borda inferior dourada; listas sobre papel `#f7f2e6`; texto principal `#2a2a24`.
- Cards: `min-height: clamp(190px, 30vw, 300px)`, `border-radius: 20px`, hover eleva 4 px e amplia a imagem.
- Animações: `surgir` (fade + subida) nos cards; transições de 0,2–0,35 s.

---

## 7. PWA e offline

`public/manifest.webmanifest`: nome “Hinário da Igreja”, `short_name` “Hinário”, `display: standalone`, `theme_color #2f4436`, `background_color #1d2a22`, ícones 192/512/maskable.

`public/sw.js` (versão atual `hinario-v4`):

- Pré-cache: `/`, `/index.html`, `/manifest.webmanifest`, `/data/catalogo.json`, ícones.
- Páginas: rede primeiro, cache como reserva.
- `catalogo.json`: rede primeiro (sempre atualizado), cache offline.
- Imagens (`/manus-storage/...`): cache primeiro, depois rede.
- Demais arquivos: cache primeiro com atualização em segundo plano.
- Trocar `VERSAO` a cada publicação relevante limpa caches antigos.

`main.tsx` protege contra tela branca: recarrega sozinho uma vez se um módulo não carregar (arquivo antigo em cache) e mostra “Algo deu errado… Recarregar” em caso de erro de renderização.

---

## 8. Rotina das fotos (como o acervo é montado)

Regras do cliente, que o agente segue a cada lote:

1. **Nada pode ser cortado**: a folha inteira precisa aparecer. O tratamento só remove mesa/fundo escuro.
2. Endireitar (pequena rotação por detecção de linhas), tirar sombra, melhorar contraste e nitidez.
3. Fotos deitadas são giradas para ficar em pé; fotos de duas páginas do livro ficam inteiras, em paisagem.
4. Folha com dois ou três hinos é desmembrada em páginas individuais.
5. Fotos repetidas ou em tons diferentes entram todas.
6. Hino sem número: perguntar ao usuário.
7. Numeração lida visualmente (OCR automático erra); conferência em folhas de contato.
8. Saída: JPEG até 2400 px no maior lado, qualidade 87–90.

Script de tratamento (`pipeline.py`, fora do app): `python3 pipeline.py <pasta_entrada> <pasta_saida> --max 2400` → grava as imagens tratadas + `info.json` com o giro aplicado.

---

## 9. Como acrescentar músicas depois

1. Tratar as fotos com o pipeline (ou manualmente, mantendo a folha inteira).
2. Subir as imagens para o armazenamento (no Manus: `manus-upload-file --webdev arquivo.jpg`, que devolve `/manus-storage/...`). Em outra hospedagem: colocar em `public/midias/` e usar `/midias/arquivo.jpg`.
3. Editar `dados/fonte.json`: se o número já existir, acrescentar a URL em `paginas`; se não, criar um item novo (a ordem e a busca por número se ajustam sozinhas).
4. `python3 scripts/gerar_catalogo.py`
5. `pnpm build` e publicar.

---

## 10. Como rodar

```bash
pnpm install
pnpm dev      # http://localhost:3000
pnpm build    # gera dist/
```

Hospedagem: qualquer servidor estático com fallback SPA (todas as rotas → `index.html`) e `sw.js` servido na raiz. No Manus, `public/manus-routes.json` declara esse fallback e o `no-cache` para `/data/*`.

---

## 11. Histórico do acervo

- Lote 1 (14 fotos, hinos 21–382) e lote 2 (144 fotos JPEG, IMG_6346–IMG_6490) → 153 páginas.
- Correções de leitura: IMG_6349 é o hino 161 (não 143); IMG_6399/6445/6449 são o hino 61; “Brilho Celeste” sem número entrou no 114; a folha manuscrita “A Vinda do Senhor” é a 2ª página do hino 292.
- Folhas de duas páginas: hinos 12 (e 32 na mesma folha), 42, 113 e 299.
- Bordas completadas: hino 3 (acorde final “A” cortado à direita) e hino 63, 2ª parte (título raspado no topo).

---

## 12. Prompt sugerido para o Claude Code

> Você vai manter este projeto: um PWA em Vite + React + TypeScript chamado “Hinário da Igreja”. Ele mostra quatro seções (Hinos, Cânticos espirituais, Salmos, Músicas Lavras) a partir de fotos de folhas de hinário. O catálogo é gerado por `scripts/gerar_catalogo.py` a partir de `dados/fonte.json`. Cada seção tem lista ordenada, busca por número/nome e um botão que gera um PDF com capa e todas as músicas em ordem (jsPDF, sob demanda). O leitor mostra a folha inteira (sem cortar), com pinça, duplo toque, setas, swipe de toque nas laterais e um botão ⟳ que gira a página para ocupar a tela. Nunca corte conteúdo das fotos, mantenha o tema “Hinário de Couro” (verde #2f4436, dourado #c9a227, papel #f7f2e6, Libre Baskerville + Inter) e siga a especificação em ESPECIFICACAO_HINARIO.md.
