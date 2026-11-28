import type { jsPDF as JsPDFTipo } from 'jspdf';
import { Item, Pagina, Secao, rotuloItem } from './catalogo';
import { ARTEFATO } from './ambiente';
import { CamadaPapel, FolhaDef, Traco, pintarBase, prepararBase } from './anotacoes';

const VERDE: [number, number, number] = [47, 68, 54];
const DOURADO: [number, number, number] = [201, 162, 39];
const PAPEL: [number, number, number] = [247, 242, 230];

/** Baixa a imagem e reduz para caber bem no PDF (mantém legibilidade e tamanho de arquivo razoável). */
type ImagemPdf = { dados: string; larg: number; alt: number };

async function imagemParaPdf(url: string, maxLado = 1500, qualidade = 0.85): Promise<ImagemPdf> {
  const resp = await fetch(url, { cache: 'force-cache' });
  if (!resp.ok) throw new Error('Falha ao baixar ' + url);
  const blob = await resp.blob();
  const bitmap = await createImageBitmap(blob);
  const escala = Math.min(1, maxLado / Math.max(bitmap.width, bitmap.height));
  const larg = Math.round(bitmap.width * escala);
  const alt = Math.round(bitmap.height * escala);
  const canvas = document.createElement('canvas');
  canvas.width = larg;
  canvas.height = alt;
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, larg, alt);
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(bitmap, 0, 0, larg, alt);
  bitmap.close?.();
  return { dados: canvas.toDataURL('image/jpeg', qualidade), larg, alt };
}

function capa(doc: JsPDFTipo, secao: Secao, total: number) {
  const L = doc.internal.pageSize.getWidth();
  const A = doc.internal.pageSize.getHeight();
  doc.setFillColor(...VERDE);
  doc.rect(0, 0, L, A, 'F');
  doc.setDrawColor(...DOURADO);
  doc.setLineWidth(0.8);
  doc.rect(10, 10, L - 20, A - 20);
  doc.setLineWidth(0.25);
  doc.rect(13, 13, L - 26, A - 26);

  doc.setTextColor(...DOURADO);
  doc.setFont('times', 'bold');
  doc.setFontSize(20);
  doc.text('HINÁRIO DA IGREJA', L / 2, A * 0.30, { align: 'center' });

  doc.setFontSize(46);
  doc.setTextColor(...PAPEL);
  doc.text(secao.titulo.toUpperCase(), L / 2, A * 0.44, { align: 'center' });

  doc.setDrawColor(...DOURADO);
  doc.setLineWidth(0.5);
  doc.line(L / 2 - 30, A * 0.49, L / 2 + 30, A * 0.49);

  doc.setFont('times', 'italic');
  doc.setFontSize(15);
  doc.setTextColor(...PAPEL);
  doc.text(secao.subtitulo, L / 2, A * 0.55, { align: 'center' });

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(11);
  doc.setTextColor(...DOURADO);
  doc.text(`${total} ${total === 1 ? 'música' : 'músicas'}`, L / 2, A * 0.63, { align: 'center' });

  const hoje = new Date().toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
  doc.setFontSize(10);
  doc.text(hoje, L / 2, A * 0.86, { align: 'center' });
}

/** Uma folha por página do PDF (em pé ou deitada, conforme o formato da imagem), com a legenda embaixo. */
function paginaDaFolha(doc: JsPDFTipo, img: ImagemPdf | null, legenda: string) {
  const larg = img?.larg ?? 1;
  const alt = img?.alt ?? 1;
  const paisagem = larg > alt;
  const [PL, PA] = paisagem ? [297, 210] : [210, 297];
  doc.addPage([PL, PA], paisagem ? 'landscape' : 'portrait');
  const margem = paisagem ? 4 : 8;
  const rodape = paisagem ? 7 : 9;
  const dispL = PL - margem * 2;
  const dispA = PA - margem * 2 - rodape;
  const escala = Math.min(dispL / larg, dispA / alt);
  const w = larg * escala;
  const h = alt * escala;
  const x = (PL - w) / 2;
  const y = margem + (dispA - h) / 2;
  doc.setFillColor(255, 255, 255);
  doc.rect(0, 0, PL, PA, 'F');
  if (img) {
    doc.addImage(img.dados, 'JPEG', x, y, w, h, undefined, 'FAST');
  } else {
    doc.setTextColor(120, 120, 120);
    doc.setFontSize(12);
    doc.text('Não foi possível incluir esta página.', PL / 2, PA / 2, { align: 'center' });
  }
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(120, 120, 120);
  doc.text(legenda, PL / 2, PA - 5, { align: 'center' });
}

/** "Hino 9 – Aleluia ao Deus Trino" (legenda de cada página). */
function legendaDoItem(secao: Secao, item: Item): string {
  const rotulo = rotuloItem(secao, item);
  return secao.id === 'hinos' || secao.id === 'hinoscifra' ? `Hino ${rotulo}${item.titulo ? ' – ' + item.titulo : ''}` : `${rotulo}${item.titulo ? ' – ' + item.titulo : ''}`;
}

/** Gera o PDF da seção inteira (na ordem da lista) e devolve o arquivo como Blob. */
export async function gerarPdfSecao(
  secao: Secao,
  itens: Item[],
  aoProgredir?: (feitos: number, total: number) => void,
): Promise<Blob> {
  const { jsPDF } = await import('jspdf');
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4', compress: true });
  capa(doc, secao, itens.length);

  let feitos = 0;
  const total = itens.reduce((s, i) => s + i.paginas.length, 0);
  aoProgredir?.(0, total);

  for (const item of itens) {
    for (const pagina of item.paginas) {
      let dados: string | null = null;
      let larg = 1;
      let alt = 1;
      try {
        const img = await imagemParaPdf(pagina.img);
        dados = img.dados;
        larg = img.larg;
        alt = img.alt;
      } catch {
        dados = null;
      }
      paginaDaFolha(doc, dados ? { dados, larg, alt } : null, legendaDoItem(secao, item));
      feitos += 1;
      aoProgredir?.(feitos, total);
      await new Promise((r) => setTimeout(r, 0));
    }
  }
  return doc.output('blob');
}

/** Uma folha da música a incluir no PDF, já com o que deve aparecer nela. */
export type FolhaParaPdf = {
  pagina: Pagina;
  /** anotações a desenhar por cima (vazio = folha sem anotações) */
  tracos?: Traco[];
  /** cifras no tom escolhido (vazio = tom original) */
  camada?: CamadaPapel;
  /** nome do tom, para a legenda (ex.: "D") */
  tom?: string;
};

const LADO_MAXIMO_MUSICA = 2400;

/** A folha como vai para o PDF: a imagem, as cifras no tom escolhido e as anotações por cima. */
async function folhaParaPdf(f: FolhaParaPdf): Promise<ImagemPdf> {
  if (!f.camada && !f.tracos?.length) return imagemParaPdf(f.pagina.img, LADO_MAXIMO_MUSICA, 0.92);
  const def: FolhaDef = { src: f.pagina.img, tracos: [] };
  const base = await prepararBase(def);
  pintarBase(base, def, f.tracos ?? [], f.camada);
  const k = Math.min(1, LADO_MAXIMO_MUSICA / Math.max(base.W, base.H));
  let tela = base.canvas;
  if (k < 1) {
    tela = document.createElement('canvas');
    tela.width = Math.round(base.W * k);
    tela.height = Math.round(base.H * k);
    const c = tela.getContext('2d')!;
    c.imageSmoothingQuality = 'high';
    c.drawImage(base.canvas, 0, 0, tela.width, tela.height);
  }
  return { dados: tela.toDataURL('image/jpeg', 0.92), larg: tela.width, alt: tela.height };
}

/** PDF de uma música só: todas as folhas dela, na ordem em que aparecem, sem capa. */
export async function gerarPdfMusica(
  secao: Secao,
  item: Item,
  folhas: FolhaParaPdf[],
  aoProgredir?: (feitos: number, total: number) => void,
): Promise<Blob> {
  const { jsPDF } = await import('jspdf');
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4', compress: true });
  const base = legendaDoItem(secao, item);
  aoProgredir?.(0, folhas.length);
  let feitos = 0;
  for (const f of folhas) {
    let img: ImagemPdf | null = null;
    try {
      img = await folhaParaPdf(f);
    } catch {
      img = null;
    }
    const legenda = base + (f.pagina.nome ? ` (${f.pagina.nome})` : '') + (f.tom ? ` · Tom: ${f.tom}` : '');
    paginaDaFolha(doc, img, legenda);
    feitos += 1;
    aoProgredir?.(feitos, folhas.length);
    await new Promise((r) => setTimeout(r, 0));
  }
  doc.deletePage(1); // a página em branco que o jsPDF cria ao começar
  return doc.output('blob');
}

/** "Novo Cântico - 9 - Aleluia ao Deus Trino.pdf" */
export function nomeArquivoPdfMusica(secao: Secao, item: Item): string {
  const rotulo = rotuloItem(secao, item);
  const partes = [secao.titulo, rotulo !== item.titulo ? rotulo : '', item.titulo].filter(Boolean);
  return partes.join(' - ').replace(/[\\/:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim() + '.pdf';
}

export function nomeArquivoPdf(secao: Secao): string {
  return `Hinário - ${secao.titulo}.pdf`;
}

type Downloads = { save: (o: { filename: string; data: unknown }) => Promise<unknown> };

/** No site comum baixa direto; dentro da Claude usa o recurso de download da própria Claude. */
export async function baixarBlob(blob: Blob, nome: string): Promise<void> {
  if (ARTEFATO) {
    const claude = (window as unknown as { claude?: { use: (n: string) => Promise<Downloads | null> } }).claude;
    const dl = claude ? await claude.use('downloads') : null;
    if (!dl) throw new Error('Neste modo o download não está disponível. Abra o hinário pelo link do site para exportar o PDF.');
    try {
      await dl.save({ filename: nome, data: blob });
    } catch {
      await dl.save({ filename: nome, data: new Uint8Array(await blob.arrayBuffer()) });
    }
    return;
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nome;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
