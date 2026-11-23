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
  livro?: string;
  tom?: string;
  obs?: string;
  paginas: Pagina[];
};

export type Secao = {
  id: 'hinos' | 'hinoscifra' | 'canticos' | 'caderninho' | 'salmos' | 'palavra' | 'lavras';
  titulo: string;
  subtitulo: string;
  ordem: 'numero' | 'alfabeto';
  itens: Item[];
  arquivos?: ArquivoPdf[];
};

export type ArquivoPdf = { nome: string; url: string; paginas?: number | null; bytes?: number | null };

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

const BIBLIA = ['Gênesis','Êxodo','Levítico','Números','Deuteronômio','Josué','Juízes','Rute','1 Samuel','2 Samuel','1 Reis','2 Reis','1 Crônicas','2 Crônicas','Esdras','Neemias','Ester','Jó','Salmos','Provérbios','Eclesiastes','Cantares','Isaías','Jeremias','Lamentações','Ezequiel','Daniel','Oseias','Joel','Amós','Obadias','Jonas','Miqueias','Naum','Habacuque','Sofonias','Ageu','Zacarias','Malaquias','Mateus','Marcos','Lucas','João','Atos','Romanos','1 Coríntios','2 Coríntios','Gálatas','Efésios','Filipenses','Colossenses','1 Tessalonicenses','2 Tessalonicenses','1 Timóteo','2 Timóteo','Tito','Filemom','Hebreus','Tiago','1 Pedro','2 Pedro','1 João','2 João','3 João','Judas','Apocalipse'];

export function slugLivro(nome: string): string {
  return normalizar(nome).replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

export type LivroCartao = { nome: string; slug: string; para: string; itens: Item[]; capa: 'salmos' | 'palavra' };

/** Um cartão por livro da Bíblia (Salmos incluso), na ordem da Bíblia. Livro novo = cartão novo. */
export function livrosDaPalavra(catalogo: Catalogo): LivroCartao[] {
  const mapa = new Map<string, Item[]>();
  for (const it of catalogo.secoes.find((s) => s.id === 'palavra')?.itens ?? []) {
    const nome = it.livro || 'Outros';
    mapa.set(nome, [...(mapa.get(nome) ?? []), it]);
  }
  const salmos = catalogo.secoes.find((s) => s.id === 'salmos')?.itens ?? [];
  const lista: LivroCartao[] = [{ nome: 'Salmos', slug: 'salmos', para: '/salmos', itens: salmos, capa: 'salmos' }];
  for (const [nome, itens] of mapa) lista.push({ nome, slug: slugLivro(nome), para: `/livro/${slugLivro(nome)}`, itens, capa: 'palavra' });
  const pos = (n: string) => (BIBLIA.indexOf(n) < 0 ? 999 : BIBLIA.indexOf(n));
  return lista.sort((a, b) => pos(a.nome) - pos(b.nome) || a.nome.localeCompare(b.nome, 'pt-BR'));
}

/** Para onde volta quem está lendo uma música (a lista em que ela aparece). */
export function rotaLista(secaoId: string, item?: Item): string {
  if (secaoId === 'palavra') return `/livro/${slugLivro(item?.livro || 'Outros')}`;
  return `/${secaoId}`;
}

export function rotuloItem(secao: Secao, item: Item): string {
  if (item.rotulo) return secao.id === 'salmos' ? `Salmo ${item.rotulo}` : item.rotulo;
  if (secao.id === 'salmos') return `Salmo ${item.num}`;
  if (secao.id === 'palavra') return '♪';
  if (secao.id === 'hinos' || secao.id === 'hinoscifra' || secao.id === 'caderninho') return String(item.num);
  if (secao.id === 'lavras') return item.num ? String(item.num) : '♪';
  return item.titulo;
}

export function rotuloCompleto(secao: Secao, item: Item): string {
  const base = rotuloItem(secao, item);
  return item.versiculos ? `${base}:${item.versiculos}` : base;
}
