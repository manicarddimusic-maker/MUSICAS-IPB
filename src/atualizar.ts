import { Catalogo, assinar, assinaturaAtual, idsDoCatalogo } from './catalogo';

export type ResultadoAtualizar = { recarregar: boolean; novas: number };

const CHAVE_MSG = 'hinario-msg-atualizado';

/** Mensagem guardada para mostrar logo depois da página recarregar. */
export function lerMensagemAtualizacao(): string | null {
  try {
    const m = sessionStorage.getItem(CHAVE_MSG);
    if (m) sessionStorage.removeItem(CHAVE_MSG);
    return m;
  } catch {
    return null;
  }
}

function guardarMensagem(m: string) {
  try {
    sessionStorage.setItem(CHAVE_MSG, m);
  } catch {
    /* ok */
  }
}

/**
 * Pergunta ao servidor (sem usar nada guardado) se já existe versão nova do aplicativo ou da lista de músicas.
 * Devolve false quando está sem internet ou quando não deu para saber.
 */
export async function existeVersaoNova(): Promise<boolean> {
  if (!navigator.onLine) return false;
  try {
    const sw = await fetch('/sw.js?v=' + Date.now(), { cache: 'no-store' });
    if (sw.ok) {
      const v = /const VERSAO = '([^']+)'/.exec(await sw.text())?.[1];
      if (v && typeof __VERSAO__ === 'string' && v !== __VERSAO__) return true;
    }
    const cat = await fetch('/data/catalogo.json?v=' + Date.now(), { cache: 'no-store' });
    if (cat.ok && assinaturaAtual && assinar(await cat.text()) !== assinaturaAtual) return true;
  } catch {
    /* sem rede: não avisa */
  }
  return false;
}

function esperar(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * Busca a última versão: aplicativo (service worker) e lista de músicas.
 * Não baixa de novo as folhas já salvas — as novas são baixadas depois pelo aviso "Baixar novas".
 */
export async function atualizarApp(): Promise<ResultadoAtualizar> {
  if (!navigator.onLine) throw new Error('Sem internet agora. Conecte-se ao Wi-Fi e tente de novo.');

  // 1) lista de músicas mais recente (passa pelo service worker, que guarda a cópia nova)
  const r = await fetch('/data/catalogo.json', { cache: 'reload' });
  if (!r.ok) throw new Error('Não foi possível falar com o servidor. Tente de novo.');
  const texto = await r.text();
  const mudouLista = assinar(texto) !== assinaturaAtual;
  let novas = 0;
  if (mudouLista) {
    try {
      const antes = new Set<string>(JSON.parse(localStorage.getItem('hinario-ids') || '[]'));
      novas = idsDoCatalogo(JSON.parse(texto) as Catalogo).filter((id) => !antes.has(id)).length;
    } catch {
      /* ok */
    }
  }

  // 2) arquivos do aplicativo (service worker)
  let mudouApp = false;
  if ('serviceWorker' in navigator) {
    const reg = await navigator.serviceWorker.getRegistration();
    if (reg) {
      await reg.update().catch(() => {});
      const novo = reg.installing || reg.waiting;
      if (novo) {
        mudouApp = true;
        for (let i = 0; i < 60 && novo.state !== 'activated' && novo.state !== 'redundant'; i++) await esperar(250);
      }
    }
  }

  if (mudouLista || mudouApp) {
    guardarMensagem(
      novas > 0
        ? `Atualizado ✓ — ${novas} ${novas === 1 ? 'música nova' : 'músicas novas'}.`
        : 'Atualizado ✓ — versão mais recente instalada.',
    );
    return { recarregar: true, novas };
  }
  return { recarregar: false, novas: 0 };
}
