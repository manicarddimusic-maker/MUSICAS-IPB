import type { jsPDF as JsPDFTipo } from 'jspdf';
import { Item, Secao, rotuloItem } from './catalogo';
import { ARTEFATO } from './ambiente';

const VERDE: [number, number, number] = [47, 68, 54];
const DOURADO: [number, number, number] = [201, 162, 39];
const PAPEL: [number, number, number] = [247, 242, 230];

/** Baixa a imagem e reduz para caber bem no PDF (mantém legibilidade e tamanho de arquivo razoável). */
async function imagemParaPdf(url: string): Promise<{ dados: string; larg: number; alt: number }> {
  const resp = await fetch(url, { cache: 'force-cache' });
  if (!resp.ok) throw new Error('Falha ao baixar ' + url);
  const blob = await resp.blob();
  const bitmap = await createImageBitmap(blob);
  const maxLado = 1500;
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
  return { dados: canvas.toDataURL('image/jpeg', 0.85), larg, alt };
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
      if (dados) {
        doc.addImage(dados, 'JPEG', x, y, w, h, undefined, 'FAST');
      } else {
        doc.setTextColor(120, 120, 120);
        doc.setFontSize(12);
        doc.text('Não foi possível incluir esta página.', PL / 2, PA / 2, { align: 'center' });
      }
      const rotulo = rotuloItem(secao, item);
      const legenda = secao.id === 'hinos' || secao.id === 'hinoscifra' ? `Hino ${rotulo}${item.titulo ? ' – ' + item.titulo : ''}` : `${rotulo}${item.titulo ? ' – ' + item.titulo : ''}`;
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      doc.setTextColor(120, 120, 120);
      doc.text(legenda, PL / 2, PA - 5, { align: 'center' });
      feitos += 1;
      aoProgredir?.(feitos, total);
      await new Promise((r) => setTimeout(r, 0));
    }
  }
  return doc.output('blob');
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
