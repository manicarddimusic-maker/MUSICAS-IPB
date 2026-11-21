import type { Catalogo } from './catalogo';

const MIDIAS = 'hinario-midias';

export function urlsDeFolhas(catalogo: Catalogo): string[] {
  const urls = new Set<string>();
  for (const s of catalogo.secoes) {
    for (const i of s.itens) for (const p of i.paginas) urls.add(p.img);
    for (const a of s.arquivos ?? []) urls.add(a.url);
  }
  return [...urls];
}

function chave(url: string): string {
  return new URL(url, location.href).pathname;
}

/** Quais folhas já estão guardadas neste aparelho. */
export async function folhasSalvas(urls: string[]): Promise<Set<string>> {
  if (!('caches' in window)) return new Set();
  const c = await caches.open(MIDIAS);
  const salvas = new Set((await c.keys()).map((r) => new URL(r.url).pathname));
  return new Set(urls.filter((u) => salvas.has(chave(u))));
}

/** Baixa e guarda as folhas que faltam (o service worker guarda no cache). */
export async function salvarTudo(
  urls: string[],
  aoProgredir: (feitas: number, total: number, falhas: number) => void,
  cancelado: () => boolean,
): Promise<{ falhas: number }> {
  try {
    await navigator.storage?.persist?.();
  } catch {
    /* ok */
  }
  const cache = await caches.open(MIDIAS);
  const ja = await folhasSalvas(urls);
  const faltam = urls.filter((u) => !ja.has(u));
  let feitas = urls.length - faltam.length;
  let falhas = 0;
  aoProgredir(feitas, urls.length, 0);
  let i = 0;
  async function trabalhador() {
    while (i < faltam.length && !cancelado()) {
      const url = faltam[i++];
      let ok = false;
      for (let t = 0; t < 3 && !ok && !cancelado(); t++) {
        try {
          const r = await fetch(url);
          if (r.ok) {
            await cache.put(url, r.clone());
            await r.blob();
            ok = true;
          }
        } catch {
          await new Promise((r) => setTimeout(r, 600 * (t + 1)));
        }
      }
      if (ok) feitas += 1;
      else falhas += 1;
      aoProgredir(feitas, urls.length, falhas);
    }
  }
  await Promise.all([trabalhador(), trabalhador(), trabalhador(), trabalhador()]);
  return { falhas };
}
