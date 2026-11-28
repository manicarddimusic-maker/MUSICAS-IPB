import { useEffect, useMemo, useState } from 'react';
import { Item, Pagina, Secao, chaveTomDaFolha } from './catalogo';
import type { Traco } from './anotacoes';
import { FolhaCifras, camadaDeCifras, fonteDasCifras, lerSemitons, situacaoDoTom } from './cifras';
import { nomeTom, tomTransposto } from './tom';
import { FolhaParaPdf, baixarBlob, gerarPdfMusica, nomeArquivoPdfMusica } from './exportarPdf';

type Props = {
  secao: Secao;
  item: Item;
  /** as folhas na ordem em que o leitor mostra */
  paginas: Pagina[];
  /** cifras reconhecidas (null enquanto carregam) */
  cifras: Record<string, FolhaCifras> | null;
  /** anotações salvas, por caminho de imagem */
  anotTracos: Record<string, Traco[]>;
  aoFechar: () => void;
};

type Estado = { fase: 'gerando'; feitos: number; total: number } | { fase: 'pronto'; blob: Blob; nome: string } | { fase: 'erro'; msg: string };

const tamanho = (b: number) => (b >= 1e6 ? `${(b / 1e6).toFixed(1).replace('.', ',')} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

/** Painel "PDF desta música": gera o PDF só desta música (no tom escolhido e com as anotações) e deixa compartilhar ou baixar. */
export default function PdfMusica({ secao, item, paginas, cifras, anotTracos, aoFechar }: Props) {
  // o tom que cada folha está mostrando agora
  const tons = useMemo(() => paginas.map((p) => lerSemitons(secao.id, item.id, chaveTomDaFolha(p))), [paginas, secao.id, item.id]);
  const situacoes = useMemo(() => paginas.map((_, i) => situacaoDoTom(cifras, paginas, i, item.tom, tons[i])), [cifras, paginas, item.tom, tons]);
  const comTrocaDeTom = paginas.map((_, i) => tons[i] !== 0 && situacoes[i].temCifras);
  const semCifrasLidas = paginas.some((_, i) => tons[i] !== 0 && cifras && !situacoes[i].temCifras);
  const temTom = comTrocaDeTom.some(Boolean);
  const temNotas = paginas.some((p) => (anotTracos[p.img]?.length ?? 0) > 0);

  const [comTom, setComTom] = useState(true);
  const [comNotas, setComNotas] = useState(true);
  const [estado, setEstado] = useState<Estado>({ fase: 'gerando', feitos: 0, total: paginas.length });
  const [tentativa, setTentativa] = useState(0);
  const [msg, setMsg] = useState<string | null>(null);

  const aguardandoCifras = cifras === null && tons.some((n) => n !== 0);

  useEffect(() => {
    if (aguardandoCifras) return;
    let vivo = true;
    setEstado({ fase: 'gerando', feitos: 0, total: paginas.length });
    setMsg(null);
    (async () => {
      const folhas: FolhaParaPdf[] = [];
      for (let i = 0; i < paginas.length; i++) {
        const p = paginas[i];
        const f: FolhaParaPdf = { pagina: p };
        if (comNotas && anotTracos[p.img]?.length) f.tracos = anotTracos[p.img];
        const s = situacoes[i];
        if (comTom && comTrocaDeTom[i] && s.folha) {
          await fonteDasCifras(s.folha);
          f.camada = camadaDeCifras(s.folha, s.transpor);
          if (s.tomOriginal) f.tom = nomeTom(tomTransposto(s.tomOriginal, tons[i]));
        }
        folhas.push(f);
      }
      const blob = await gerarPdfMusica(secao, item, folhas, (feitos, total) => vivo && setEstado({ fase: 'gerando', feitos, total }));
      if (vivo) setEstado({ fase: 'pronto', blob, nome: nomeArquivoPdfMusica(secao, item) });
    })().catch((e: Error) => vivo && setEstado({ fase: 'erro', msg: e.message || 'Não foi possível gerar o PDF.' }));
    return () => {
      vivo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [comTom, comNotas, tentativa, aguardandoCifras, cifras]);

  const nav = navigator as Navigator & { canShare?: (d: ShareData) => boolean };
  const podeCompartilhar = typeof nav.share === 'function' && !!nav.canShare?.({ files: [new File([''], 'a.pdf', { type: 'application/pdf' })] });

  async function compartilhar() {
    if (estado.fase !== 'pronto') return;
    try {
      const arq = new File([estado.blob], estado.nome, { type: 'application/pdf' });
      await navigator.share({ files: [arq], title: estado.nome.replace(/\.pdf$/, '') });
      setMsg(null);
    } catch (e) {
      if ((e as Error).name !== 'AbortError') setMsg('Não deu para abrir o compartilhamento. Use “Baixar o PDF”.');
    }
  }

  async function baixar() {
    if (estado.fase !== 'pronto') return;
    try {
      await baixarBlob(estado.blob, estado.nome);
      setMsg('PDF baixado ✓');
    } catch (e) {
      setMsg((e as Error).message || 'Não foi possível baixar.');
    }
  }

  const resumoTons = paginas
    .map((_, i) => (comTrocaDeTom[i] && situacoes[i].tomOriginal ? nomeTom(tomTransposto(situacoes[i].tomOriginal!, tons[i])) : null))
    .filter((t, i, v): t is string => !!t && v.indexOf(t) === i)
    .join(' / ');

  return (
    <div className="pdf-musica-fundo" role="presentation" onPointerDown={aoFechar}>
      <div className="pdf-musica" role="dialog" aria-label="Exportar o PDF desta música" onPointerDown={(e) => e.stopPropagation()}>
        <header>
          <strong>PDF desta música</strong>
          <button className="painel-tom-fechar" onClick={aoFechar} aria-label="Fechar">
            ✕
          </button>
        </header>
        <p className="pdf-musica-nome">
          {item.titulo} · {paginas.length} {paginas.length === 1 ? 'folha' : 'folhas'}
        </p>
        {(temTom || temNotas) && (
          <div className="pdf-musica-opcoes">
            {temTom && (
              <label>
                <input type="checkbox" checked={comTom} onChange={(e) => setComTom(e.target.checked)} />
                <span>Cifras no tom escolhido{resumoTons ? ` (${resumoTons})` : ''}</span>
              </label>
            )}
            {temNotas && (
              <label>
                <input type="checkbox" checked={comNotas} onChange={(e) => setComNotas(e.target.checked)} />
                <span>Com as minhas anotações</span>
              </label>
            )}
          </div>
        )}
        {semCifrasLidas && <p className="pdf-musica-aviso">Em alguma folha o aplicativo não consegue trocar as cifras: ela vai no tom original.</p>}

        {aguardandoCifras ? (
          <p className="pdf-musica-estado" role="status">
            Carregando as cifras…
          </p>
        ) : estado.fase === 'gerando' ? (
          <p className="pdf-musica-estado" role="status">
            Gerando o PDF… folha {Math.min(estado.feitos + 1, estado.total)} de {estado.total}
          </p>
        ) : estado.fase === 'erro' ? (
          <>
            <p className="pdf-musica-estado erro" role="alert">
              {estado.msg}
            </p>
            <div className="pdf-musica-botoes">
              <button onClick={() => setTentativa((t) => t + 1)}>Tentar de novo</button>
            </div>
          </>
        ) : (
          <>
            <p className="pdf-musica-estado" role="status">
              PDF pronto · {tamanho(estado.blob.size)}
            </p>
            <div className="pdf-musica-botoes">
              {podeCompartilhar && (
                <button className="principal" onClick={compartilhar}>
                  ⇪ Compartilhar / Salvar em Arquivos
                </button>
              )}
              <button className={podeCompartilhar ? undefined : 'principal'} onClick={baixar}>
                ⬇ Baixar o PDF
              </button>
            </div>
          </>
        )}
        {msg && (
          <p className="pdf-musica-aviso" role="status">
            {msg}
          </p>
        )}
      </div>
    </div>
  );
}
