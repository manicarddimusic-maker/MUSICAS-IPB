import { caminho } from './ambiente';
import { Tom, Transpositor, criarTranspositor, estimarTom, lerTom, prefereBemol } from './tom';

/**
 * Onde está cada cifra dentro de uma folha (em pixels da imagem ou em pontos da página do PDF):
 * [x, linha de base, largura, tamanho da letra, texto, cor do papel?, cor da tinta?, sobe?, desce?]
 * "sobe" e "desce": quanto a cifra original passa para cima e para baixo da linha de base
 * (só vem quando foge do comum: expoentes, índices, letras recortadas de fotos).
 * Texto "?" = cifra que existe na folha mas não foi possível ler: fica marcada, sem trocar.
 */
export type Cifra = [number, number, number, number, string, (string | 0 | null)?, (string | 0)?, number?, number?];

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
  /** foto tirada deitada: as posições estão na folha girada (90, 180 ou 270 graus no sentido horário) */
  r?: 90 | 180 | 270;
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
  const larguraUtil = folha.r === 90 || folha.r === 270 ? folha.h : folha.w;
  // linhas: cifras com a mesma linha de base, da esquerda para a direita
  // "borrachas": entradas sem texto só cobrem um pedaço da folha (letra da caneta, riscos) quando o tom muda
  for (let i = 0; i < lista.length; i++) {
    if (lista[i][4] !== '') continue;
    const [x, base, w, fs, , fundo, , sobe, desce] = lista[i];
    const cima = sobe || fs;
    prontas[i] = { txt: '', x, base, fs, tinta: COR_TRANSPOSTA, rx: x - 1, ry: base - cima - 1, rw: w + 2, rh: cima + (desce || 0) + 2, fundo: fundo ? '#' + fundo : '#ffffff' };
  }
  const ordem = lista
    .map((_, i) => i)
    .filter((i) => lista[i][4] !== '')
    .sort((a, b) => lista[a][1] - lista[b][1] || lista[a][0] - lista[b][0]);
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
      const limite = ultimo ? larguraUtil - fs * 0.1 : lista[linha[k + 1]][0] - folga;
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

// O tom fica guardado por música. Uma folha que é outra versão da música (outra melodia, outro tom)
// guarda o seu à parte: "folha" é o nome do arquivo dela.
const chaveTom = (secaoId: string, itemId: string, folha?: string) => `hinario-tom:${secaoId}:${itemId}${folha ? ':' + folha : ''}`;

/** Quantos semitons a pessoa deixou esta música (fica guardado no aparelho). */
export function lerSemitons(secaoId: string, itemId: string, folha?: string): number {
  try {
    const n = Number(localStorage.getItem(chaveTom(secaoId, itemId, folha)));
    return Number.isFinite(n) ? Math.max(-6, Math.min(6, Math.round(n))) : 0;
  } catch {
    return 0;
  }
}

export function guardarSemitons(secaoId: string, itemId: string, n: number, folha?: string) {
  try {
    if (n === 0) localStorage.removeItem(chaveTom(secaoId, itemId, folha));
    else localStorage.setItem(chaveTom(secaoId, itemId, folha), String(n));
  } catch {
    /* sem armazenamento */
  }
}

/** Matriz (a, b, c, d, e, f — a mesma do SVG e do canvas) que leva as posições da folha girada de volta para a imagem original. */
export function matrizDaFolha(folha: FolhaCifras): [number, number, number, number, number, number] | null {
  if (folha.r === 90) return [0, -1, 1, 0, 0, folha.h];
  if (folha.r === 270) return [0, 1, -1, 0, folha.w, 0];
  if (folha.r === 180) return [-1, 0, 0, -1, folha.w, folha.h];
  return null;
}

/** Transformação (SVG) que leva as posições da folha girada de volta para a imagem original. */
export function giroDaFolha(folha: FolhaCifras): string | undefined {
  const m = matrizDaFolha(folha);
  return m ? `matrix(${m.join(',')})` : undefined;
}

/* ---------- as cifras no tom escolhido, desenhadas em canvas (editor, folha anotada, PDF) ---------- */

/** Desenha, por cima da imagem já posta no canvas (W × H), a camada de cifras de uma folha. */
export type Camada = (ctx: CanvasRenderingContext2D, W: number, H: number) => void;

/** As letras das cifras desta folha já chegaram? Em canvas, sem elas o desenho sairia com letra trocada. */
export function fonteDasCifras(folha: FolhaCifras): Promise<void> {
  const f = (document as Document & { fonts?: FontFaceSet }).fonts;
  if (!f) return Promise.resolve();
  return f
    .load(`${pesoDaFolha(folha)} 20px ${FONTES[folha.f ?? 's']}`)
    .then(() => {
      larguras.clear();
    })
    .catch(() => undefined);
}

/** Mesmo desenho do CifrasSobre (SVG): tapa a cifra original com a cor do papel e escreve a nova, no mesmo lugar e tamanho. */
export function pintarCifras(ctx: CanvasRenderingContext2D, folha: FolhaCifras, prontas: CifraPronta[], W: number, H: number) {
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  ctx.scale(W / folha.w, H / folha.h);
  const m = matrizDaFolha(folha);
  if (m) ctx.transform(...m);
  for (const c of prontas) {
    if (c.ilegivel) {
      ctx.fillStyle = 'rgba(214, 40, 40, 0.16)';
      ctx.strokeStyle = '#c62828';
      ctx.lineWidth = Math.max(1, c.fs * 0.06);
      ctx.beginPath();
      const r = c.fs * 0.12;
      if (typeof ctx.roundRect === 'function') ctx.roundRect(c.rx, c.ry, c.rw, c.rh, r);
      else ctx.rect(c.rx, c.ry, c.rw, c.rh);
      ctx.fill();
      ctx.stroke();
    } else {
      ctx.fillStyle = c.fundo;
      ctx.fillRect(c.rx, c.ry, c.rw, c.rh);
    }
  }
  const fonte = FONTES[folha.f ?? 's'];
  const peso = pesoDaFolha(folha);
  ctx.textBaseline = 'alphabetic';
  ctx.textAlign = 'left';
  for (const c of prontas) {
    if (c.ilegivel || !c.txt) continue;
    ctx.font = `${peso} ${c.fs}px ${fonte}`;
    ctx.fillStyle = c.tinta;
    if (c.larg) {
      // cifra nova mais comprida que o espaço: aperta as letras até caber (igual ao textLength do SVG)
      const natural = ctx.measureText(c.txt).width;
      ctx.save();
      ctx.translate(c.x, c.base);
      ctx.scale(natural ? c.larg / natural : 1, 1);
      ctx.fillText(c.txt, 0, 0);
      ctx.restore();
    } else {
      ctx.fillText(c.txt, c.x, c.base);
    }
  }
  ctx.restore();
}

/** A camada de cifras de uma folha num tom: já mede e planeja tudo; chame depois de fonteDasCifras. */
export function camadaDeCifras(folha: FolhaCifras, transpor: Transpositor): Camada {
  const prontas = planejar(folha, transpor);
  return (ctx, W, H) => pintarCifras(ctx, folha, prontas, W, H);
}

/** Tudo o que se precisa saber do tom de uma folha: as cifras dela, o tom original e como trocar. */
export type SituacaoTom = {
  folha?: FolhaCifras;
  tomOriginal: Tom | null;
  transpor: Transpositor;
  /** a folha tem cifras que o aplicativo sabe trocar */
  temCifras: boolean;
  /** quantas cifras o aplicativo não conseguiu ler */
  ilegiveis: number;
  /** a foto está fora de foco: a leitura pode ter falhas */
  duvidosa: boolean;
};

export function situacaoDoTom(
  cifras: Record<string, FolhaCifras> | null | undefined,
  paginas: { img: string; tom?: string }[],
  i: number,
  tomDoItem: string | undefined,
  semitons: number,
): SituacaoTom {
  const p = paginas[i];
  const folha = p ? cifras?.[p.img] : undefined;
  const todas = cifras ? paginas.map((q) => cifras[q.img]).filter((f): f is FolhaCifras => !!f) : [];
  const tomOriginal = tomDaFolha(p?.tom ?? tomDoItem, folha, todas);
  return {
    folha,
    tomOriginal,
    transpor: transpositorDaFolha(semitons, tomOriginal, folha),
    temCifras: !!folha && folha.c.some((c) => c[4] !== '?' && c[4] !== ''),
    ilegiveis: folha ? folha.c.filter((c) => c[4] === '?').length : 0,
    duvidosa: folha?.q === 1,
  };
}
