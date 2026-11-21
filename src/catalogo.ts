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
  id: 'hinos' | 'canticos' | 'caderninho' | 'salmos' | 'palavra' | 'lavras';
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

/** "Impressão digital" da lista de músicas carregada (para saber se chegou versão nova). */
export let assinaturaAtual = '';
export function assinar(texto: string): string {
  let h = 5381;
  for (let i = 0; i < texto.length; i++) h = ((h << 5) + h + texto.charCodeAt(i)) | 0;
  return String(h) + ':' + texto.length;
}
export function idsDoCatalogo(c: Catalogo): string[] {
  return c.secoes.flatMap((s) => s.itens.map((i) => i.id));
}

export function carregarCatalogo(): Promise<Catalogo> {
  if (!cache) {
    cache = fetch(caminho('/data/catalogo.json'), { cache: 'no-cache' })
      .then((r) => {
        if (!r.ok) throw new Error('Falha ao carregar o catálogo');
        return r.text();
      })
      .then((texto) => {
        assinaturaAtual = assinar(texto);
        const c = JSON.parse(texto) as Catalogo;
        try {
          localStorage.setItem('hinario-ids', JSON.stringify(idsDoCatalogo(c)));
        } catch {
          /* ok */
        }
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
  if (secao.id === 'hinos' || secao.id === 'caderninho') return String(item.num);
  if (secao.id === 'lavras') return item.num ? String(item.num) : '♪';
  return item.titulo;
}

export function rotuloCompleto(secao: Secao, item: Item): string {
  const base = rotuloItem(secao, item);
  return item.versiculos ? `${base}:${item.versiculos}` : base;
}
