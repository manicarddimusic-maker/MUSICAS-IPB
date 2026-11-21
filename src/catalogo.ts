import { caminho } from './ambiente';

export type Pagina = {
  img: string;
  alt: string;
  tom?: string;
};

export type Item = {
  id: string;
  num?: number;
  rotulo?: string;
  versiculos?: string;
  titulo: string;
  tom?: string;
  obs?: string;
  paginas: Pagina[];
};

export type Secao = {
  id: 'hinos' | 'canticos' | 'salmos' | 'palavra' | 'lavras';
  titulo: string;
  subtitulo: string;
  ordem: 'numero' | 'alfabeto';
  itens: Item[];
};

export type Catalogo = {
  geradoEm: string;
  secoes: Secao[];
};

let cache: Promise<Catalogo> | null = null;

export function carregarCatalogo(): Promise<Catalogo> {
  if (!cache) {
    cache = fetch(caminho('/data/catalogo.json'), { cache: 'no-cache' })
      .then((r) => {
        if (!r.ok) throw new Error('Falha ao carregar o catálogo');
        return r.json() as Promise<Catalogo>;
      })
      .then((c) => {
        for (const sec of c.secoes) for (const it of sec.itens) for (const pg of it.paginas) pg.img = caminho(pg.img);
        return c;
      })
      .catch((e) => {
        cache = null;
        throw e;
      });
  }
  return cache;
}

export function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

export function ordenarItens(secao: Secao): Item[] {
  const itens = [...secao.itens];
  if (secao.ordem === 'numero') {
    const primeiro = (i: Item) => parseInt(i.versiculos ?? '0', 10) || 0;
    itens.sort((a, b) => (a.num ?? 0) - (b.num ?? 0) || primeiro(a) - primeiro(b) || a.titulo.localeCompare(b.titulo, 'pt-BR'));
  } else {
    itens.sort((a, b) => normalizar(a.titulo).localeCompare(normalizar(b.titulo), 'pt-BR'));
  }
  return itens;
}

export function rotuloItem(secao: Secao, item: Item): string {
  if (item.rotulo) return secao.id === 'salmos' ? `Salmo ${item.rotulo}` : item.rotulo;
  if (secao.id === 'salmos') return `Salmo ${item.num}`;
  if (secao.id === 'palavra') return '♪';
  if (secao.id === 'hinos') return String(item.num);
  if (secao.id === 'lavras') return item.num ? String(item.num) : '♪';
  return item.titulo;
}

export function rotuloCompleto(secao: Secao, item: Item): string {
  const base = rotuloItem(secao, item);
  return item.versiculos ? `${base}:${item.versiculos}` : base;
}
