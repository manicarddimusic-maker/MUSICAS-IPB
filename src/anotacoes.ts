/** Anotações (caneta, marca-texto, texto…) guardadas só neste aparelho, em traços editáveis. */

export type Ferramenta = 'caneta' | 'marca' | 'corretivo' | 'borracha' | 'texto';

export type Traco =
  | { t: 'caneta' | 'marca' | 'corretivo'; c: string; w: number; p: [number, number, number][] }
  | { t: 'texto'; c: string; s: number; x: number; y: number; txt: string };

export type FundoBranco = 'branca' | 'linhas' | 'pauta';

/** Uma folha editável: uma foto existente (src) ou uma folha em branco. Coordenadas dos traços em "largura = 1". */
export type FolhaDef = {
  src?: string;
  branco?: { w: number; h: number; fundo: FundoBranco };
  tracos: Traco[];
};

const BANCO = 'hinario-anotacoes';

function abrir(): Promise<IDBDatabase> {
  return new Promise((ok, erro) => {
    const r = indexedDB.open(BANCO, 1);
    r.onupgradeneeded = () => {
      const db = r.result;
      if (!db.objectStoreNames.contains('anot')) db.createObjectStore('anot', { keyPath: 'key' });
      if (!db.objectStoreNames.contains('rasc')) db.createObjectStore('rasc', { keyPath: 'id' });
    };
    r.onsuccess = () => ok(r.result);
    r.onerror = () => erro(r.error);
  });
}

async function tx<T>(loja: 'anot' | 'rasc', modo: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await abrir();
  return new Promise((ok, erro) => {
    const t = db.transaction(loja, modo);
    const rq = fn(t.objectStore(loja));
    t.oncomplete = () => {
      db.close();
      ok(rq.result);
    };
    t.onerror = () => {
      db.close();
      erro(t.error);
    };
    t.onabort = () => {
      db.close();
      erro(t.error);
    };
  });
}

export type Anot = { key: string; tracos: Traco[]; flat: Blob; em: number };

export const lerAnot = (key: string) => tx<Anot | undefined>('anot', 'readonly', (s) => s.get(key));
export const gravarAnot = (a: Anot) => tx('anot', 'readwrite', (s) => s.put(a));
export const apagarAnot = (key: string) => tx('anot', 'readwrite', (s) => s.delete(key));
export const todasAnot = () => tx<Anot[]>('anot', 'readonly', (s) => s.getAll());

export type Rascunho = {
  id: string;
  titulo: string;
  criado: number;
  em: number;
  origem?: string;
  folhas: FolhaDef[];
  miniatura?: Blob;
};

export const listarRascunhos = async () => (await tx<Rascunho[]>('rasc', 'readonly', (s) => s.getAll())).sort((a, b) => b.em - a.em);
export const lerRascunho = (id: string) => tx<Rascunho | undefined>('rasc', 'readonly', (s) => s.get(id));
export const gravarRascunho = (r: Rascunho) => tx('rasc', 'readwrite', (s) => s.put(r));
export const apagarRascunho = (id: string) => tx('rasc', 'readwrite', (s) => s.delete(id));

export const novoId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

/* ---------- desenho ---------- */

export function carregarImagem(src: string): Promise<HTMLImageElement> {
  return new Promise((ok, erro) => {
    const im = new Image();
    im.onload = () => ok(im);
    im.onerror = () => erro(new Error('Não foi possível abrir a folha (sem internet e ainda não salva neste aparelho).'));
    im.src = src;
  });
}

/** Cor do papel da foto (o "corretivo" usa essa cor para sumir com o que estava impresso). */
export function corDoPapel(im: HTMLImageElement): string {
  const c = document.createElement('canvas');
  c.width = 48;
  c.height = 48;
  const x = c.getContext('2d', { willReadFrequently: true })!;
  x.drawImage(im, 0, 0, 48, 48);
  const d = x.getImageData(0, 0, 48, 48).data;
  const l: { v: number; r: number; g: number; b: number }[] = [];
  for (let i = 0; i < d.length; i += 4) l.push({ v: d[i] * 0.3 + d[i + 1] * 0.59 + d[i + 2] * 0.11, r: d[i], g: d[i + 1], b: d[i + 2] });
  l.sort((a, b) => b.v - a.v);
  const top = l.slice(0, Math.max(8, Math.floor(l.length * 0.25)));
  const m = (k: 'r' | 'g' | 'b') => Math.round(top.reduce((s, p) => s + p[k], 0) / top.length);
  return `rgb(${m('r')},${m('g')},${m('b')})`;
}

export function desenharFundoBranco(ctx: CanvasRenderingContext2D, w: number, h: number, fundo: FundoBranco) {
  ctx.fillStyle = '#fffefa';
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = 'rgba(70,90,120,0.35)';
  ctx.lineWidth = Math.max(1, w / 1000);
  if (fundo === 'linhas') {
    const passo = w / 24;
    for (let y = passo * 2; y < h - passo / 2; y += passo) {
      ctx.beginPath();
      ctx.moveTo(w * 0.05, y);
      ctx.lineTo(w * 0.95, y);
      ctx.stroke();
    }
  } else if (fundo === 'pauta') {
    const e = w / 90; // espaço entre linhas da pauta
    const alt = e * 4;
    const grupo = alt + e * 7;
    for (let y0 = w * 0.08; y0 + alt < h - w * 0.04; y0 += grupo) {
      for (let k = 0; k < 5; k++) {
        ctx.beginPath();
        ctx.moveTo(w * 0.06, y0 + k * e);
        ctx.lineTo(w * 0.94, y0 + k * e);
        ctx.stroke();
      }
    }
  }
}

function rastro(ctx: CanvasRenderingContext2D, p: [number, number, number][], W: number) {
  ctx.beginPath();
  if (p.length === 1) {
    ctx.moveTo(p[0][0] * W, p[0][1] * W);
    ctx.lineTo(p[0][0] * W + 0.01, p[0][1] * W);
    return;
  }
  ctx.moveTo(p[0][0] * W, p[0][1] * W);
  for (let i = 1; i < p.length - 1; i++) {
    const mx = ((p[i][0] + p[i + 1][0]) / 2) * W;
    const my = ((p[i][1] + p[i + 1][1]) / 2) * W;
    ctx.quadraticCurveTo(p[i][0] * W, p[i][1] * W, mx, my);
  }
  const u = p[p.length - 1];
  ctx.lineTo(u[0] * W, u[1] * W);
}

export function desenharTraco(ctx: CanvasRenderingContext2D, t: Traco, W: number, corPapel: string) {
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  if (t.t === 'texto') {
    ctx.fillStyle = t.c;
    ctx.textBaseline = 'top';
    ctx.font = `600 ${t.s * W}px "Inter", "Helvetica Neue", Arial, sans-serif`;
    t.txt.split('\n').forEach((linha, i) => ctx.fillText(linha, t.x * W, t.y * W + i * t.s * W * 1.2));
  } else if (t.t === 'marca') {
    ctx.globalCompositeOperation = 'multiply';
    ctx.globalAlpha = 0.55;
    ctx.strokeStyle = t.c;
    ctx.lineWidth = t.w * W;
    ctx.lineCap = 'butt';
    rastro(ctx, t.p, W);
    ctx.stroke();
  } else if (t.t === 'corretivo') {
    ctx.strokeStyle = corPapel;
    ctx.lineWidth = t.w * W;
    rastro(ctx, t.p, W);
    ctx.stroke();
  } else {
    ctx.strokeStyle = t.c;
    // largura varia com a pressão da caneta (Apple Pencil); com mouse/dedo fica constante
    const variavel = t.p.some((q) => Math.abs(q[2] - t.p[0][2]) > 0.02);
    if (!variavel || t.p.length < 3) {
      ctx.lineWidth = t.w * W * (0.45 + 1.1 * (t.p[0]?.[2] ?? 0.5));
      rastro(ctx, t.p, W);
      ctx.stroke();
    } else {
      for (let i = 1; i < t.p.length; i++) {
        const a = t.p[i - 1];
        const b = t.p[i];
        ctx.lineWidth = t.w * W * (0.35 + 1.3 * ((a[2] + b[2]) / 2));
        ctx.beginPath();
        ctx.moveTo(a[0] * W, a[1] * W);
        ctx.lineTo(b[0] * W, b[1] * W);
        ctx.stroke();
      }
    }
  }
  ctx.restore();
}

export type Base = { canvas: HTMLCanvasElement; W: number; H: number; papel: string; im?: HTMLImageElement };

/** Cria o "papel" (foto ou folha em branco) no tamanho original. */
export async function prepararBase(f: FolhaDef): Promise<Base> {
  const canvas = document.createElement('canvas');
  if (f.src) {
    const im = await carregarImagem(f.src);
    canvas.width = im.naturalWidth;
    canvas.height = im.naturalHeight;
    return { canvas, W: canvas.width, H: canvas.height, papel: corDoPapel(im), im };
  }
  const b = f.branco ?? { w: 1600, h: 2200, fundo: 'branca' as FundoBranco };
  canvas.width = b.w;
  canvas.height = b.h;
  return { canvas, W: b.w, H: b.h, papel: '#fffefa' };
}

export function pintarBase(base: Base, f: FolhaDef, tracos: Traco[]) {
  const ctx = base.canvas.getContext('2d')!;
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  if (base.im) ctx.drawImage(base.im, 0, 0);
  else desenharFundoBranco(ctx, base.W, base.H, f.branco?.fundo ?? 'branca');
  for (const t of tracos) desenharTraco(ctx, t, base.W, base.papel);
}

export function paraBlob(canvas: HTMLCanvasElement, tipo = 'image/jpeg', q = 0.92): Promise<Blob> {
  return new Promise((ok, erro) => canvas.toBlob((b) => (b ? ok(b) : erro(new Error('Não foi possível gerar a imagem.'))), tipo, q));
}

export async function achatar(f: FolhaDef, tracos: Traco[], maxLado = 0): Promise<Blob> {
  const base = await prepararBase(f);
  pintarBase(base, f, tracos);
  if (!maxLado || Math.max(base.W, base.H) <= maxLado) return paraBlob(base.canvas);
  const k = maxLado / Math.max(base.W, base.H);
  const c = document.createElement('canvas');
  c.width = Math.round(base.W * k);
  c.height = Math.round(base.H * k);
  c.getContext('2d')!.drawImage(base.canvas, 0, 0, c.width, c.height);
  return paraBlob(c, 'image/jpeg', 0.8);
}
