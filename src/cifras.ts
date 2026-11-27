import { caminho } from './ambiente';
import { Tom, Transpositor, criarTranspositor, estimarTom, lerTom, prefereBemol } from './tom';

/**
 * Onde está cada cifra dentro de uma folha (em pixels da imagem ou em pontos da página do PDF):
 * [x, linha de base, largura, tamanho da letra, texto, cor do papel?, cor da tinta?, sobe?, desce?]
 * "sobe" e "desce": quanto a cifra original passa para cima e para baixo da linha de base
 * (só vem quando foge do comum: expoentes, índices, letras recortadas de fotos).
 * Texto "?" = cifra que existe na folha mas não foi possível ler: fica marcada, sem trocar.
 */
export type Cifra = [number, number, number, number, string, (string | 0)?, (string | 0)?, number?, number?];

export type FolhaCifras = {
  w: number;
  h: number;
  /** letra parecida com a da folha: s = sem serifa estreita, a = sem serifa, t = Times, m = máquina de escrever */
  f?: 's' | 'a' | 't' | 'm';
  /** 1 = a folha usa letra normal (sem negrito) nas cifras */
  n?: 1;
  /** tom, quando a própria folha informa */
  k?: string;
  /** 1 = foto fora de foco: a leitura das cifras pode ter falhas */
  q?: 1;
  c: Cifra[];
};

type Arquivo = { v: number; folhas: Record<string, FolhaCifras> };

const guardados = new Map<string, Promise<Record<string, FolhaCifras>>>();

/** Cifras de uma seção (ou de um PDF): baixa uma vez e guarda; sem internet usa a cópia salva pelo app. */
export function carregarCifras(nome: string): Promise<Record<string, FolhaCifras>> {
  let p = guardados.get(nome);
  if (!p) {
    p = fetch(caminho(`/data/cifras/${nome}.json`))
      .then((r) => (r.ok ? (r.json() as Promise<Arquivo>) : Promise.reject(new Error('sem cifras'))))
      .then((j) => j.folhas ?? {})
      .catch(() => {
        guardados.delete(nome); // tenta de novo na próxima vez
        return {} as Record<string, FolhaCifras>;
      });
    guardados.set(nome, p);
  }
  return p;
}

export const FONTES: Record<NonNullable<FolhaCifras['f']>, string> = {
  s: '"Roboto Condensed", "Arial Narrow", "Helvetica Neue", Arial, sans-serif',
  a: 'Inter, "Helvetica Neue", Arial, sans-serif',
  t: '"Times New Roman", Times, "Liberation Serif", serif',
  m: '"Roboto Mono", ui-monospace, Menlo, Consolas, monospace',
};

/** Cor das cifras já no novo tom: azul, para ficar claro o que o aplicativo trocou. */
export const COR_TRANSPOSTA = '#0b3fb3';

let pincel: CanvasRenderingContext2D | null | undefined;
const larguras = new Map<string, number>();

/** Largura do texto (em "tamanhos de letra") na fonte pedida. */
export function medir(txt: string, fonte: string, peso = 700): number {
  const chave = peso + fonte + '|' + txt;
  const ja = larguras.get(chave);
  if (ja !== undefined) return ja;
  if (pincel === undefined) {
    try {
      pincel = document.createElement('canvas').getContext('2d');
    } catch {
      pincel = null;
    }
  }
  let w = txt.length * 0.56;
  if (pincel) {
    pincel.font = `${peso} 100px ${fonte}`;
    w = pincel.measureText(txt).width / 100;
  }
  larguras.set(chave, w);
  return w;
}

/** As fontes das cifras chegaram? (até lá as larguras são aproximadas) */
export function fontesProntas(): Promise<void> {
  const f = (document as Document & { fonts?: FontFaceSet }).fonts;
  if (!f) return Promise.resolve();
  return Promise.all([f.load('700 20px "Roboto Condensed"'), f.load('700 20px Inter')])
    .then(() => {
      larguras.clear();
    })
    .catch(() => undefined);
}

export type CifraPronta = {
  txt: string;
  x: number;
  base: number;
  fs: number;
  tinta: string;
  /** retângulo que cobre a cifra original */
  rx: number;
  ry: number;
  rw: number;
  rh: number;
  fundo: string;
  /** largura forçada (aperta as letras quando a cifra nova é mais comprida que o espaço) */
  larg?: number;
  /** cifra que não foi possível ler: só recebe uma marca, continua como está na folha */
  ilegivel?: boolean;
};

const TEM_DESCIDA = /[()gjpqy,;/]/;
/** quanto as letras podem ser apertadas antes de a cifra empurrar a vizinha para a direita */
const APERTO = 0.8;
const APERTO_FIM = 0.58;

export const pesoDaFolha = (folha: FolhaCifras) => (folha.n ? 400 : 700);

/**
 * Calcula, para uma folha, o que desenhar por cima: tapa a cifra antiga e escreve a nova.
 * Quando a cifra nova é mais comprida (A vira Bb), primeiro aperta um pouco as letras;
 * se ainda não couber, empurra as cifras seguintes da mesma linha — como o texto de um site de cifras.
 */
export function planejar(folha: FolhaCifras, transpor: Transpositor): CifraPronta[] {
  const fonte = FONTES[folha.f ?? 's'];
  const peso = pesoDaFolha(folha);
  const lista = folha.c;
  const prontas: CifraPronta[] = new Array(lista.length);
  // linhas: cifras com a mesma linha de base, da esquerda para a direita
  const ordem = lista.map((_, i) => i).sort((a, b) => lista[a][1] - lista[b][1] || lista[a][0] - lista[b][0]);
  const linhas: number[][] = [];
  for (const i of ordem) {
    const ult = linhas[linhas.length - 1];
    if (ult && Math.abs(lista[ult[ult.length - 1]][1] - lista[i][1]) < lista[i][3] * 0.6) ult.push(i);
    else linhas.push([i]);
  }
  for (const linha of linhas) {
    linha.sort((a, b) => lista[a][0] - lista[b][0]);
    let cursor = -Infinity;
    for (let k = 0; k < linha.length; k++) {
      const i = linha[k];
      const [x, base, w, fs, original, fundo, , sobe, desceDado] = lista[i];
      const ilegivel = original === '?';
      const txt = ilegivel ? '' : transpor(original);
      const folga = fs * 0.24;
      const ultimo = k + 1 >= linha.length;
      const limite = ultimo ? folha.w - fs * 0.1 : lista[linha[k + 1]][0] - folga;
      const xi = ilegivel ? x : Math.max(x, cursor);
      const natural = ilegivel ? w : medir(txt, fonte, peso) * fs;
      const livre = Math.max(limite - xi, x + w - xi, fs * 0.4);
      let ocupa = natural;
      let larg: number | undefined;
      if (natural > livre) {
        ocupa = Math.max(livre, natural * (ultimo ? APERTO_FIM : APERTO));
        larg = ocupa;
      }
      cursor = xi + ocupa + folga;
      const cima = sobe || fs * 0.82;
      const baixo = desceDado || fs * (TEM_DESCIDA.test(original) ? 0.26 : 0.08);
      prontas[i] = {
        txt,
        x: xi,
        base,
        fs,
        tinta: COR_TRANSPOSTA,
        rx: x - fs * 0.07,
        ry: base - cima,
        rw: w + fs * 0.14,
        rh: cima + baixo,
        fundo: fundo ? '#' + fundo : '#ffffff',
        larg,
        ilegivel,
      };
    }
  }
  return prontas;
}

/** O tom de uma folha: o que está escrito nela, ou descoberto pelos acordes. */
export function tomDaFolha(escrito: string | undefined, folha: FolhaCifras | undefined, todas: FolhaCifras[]): Tom | null {
  const dito = lerTom(escrito) ?? lerTom(folha?.k);
  if (dito) return dito;
  const daFolha = folha ? folha.c.map((c) => c[4]) : [];
  if (daFolha.length >= 3) return estimarTom(daFolha);
  const tudo = todas.flatMap((f) => f.c.map((c) => c[4]));
  return tudo.length ? estimarTom(tudo) : null;
}

export function transpositorDaFolha(semitons: number, tom: Tom | null, folha: FolhaCifras | undefined): Transpositor {
  return criarTranspositor(semitons, tom, folha ? prefereBemol(folha.c.map((c) => c[4])) : false);
}

const chaveTom = (secaoId: string, itemId: string) => `hinario-tom:${secaoId}:${itemId}`;

/** Quantos semitons a pessoa deixou esta música (fica guardado no aparelho). */
export function lerSemitons(secaoId: string, itemId: string): number {
  try {
    const n = Number(localStorage.getItem(chaveTom(secaoId, itemId)));
    return Number.isFinite(n) ? Math.max(-6, Math.min(6, Math.round(n))) : 0;
  } catch {
    return 0;
  }
}

export function guardarSemitons(secaoId: string, itemId: string, n: number) {
  try {
    if (n === 0) localStorage.removeItem(chaveTom(secaoId, itemId));
    else localStorage.setItem(chaveTom(secaoId, itemId), String(n));
  } catch {
    /* sem armazenamento */
  }
}
