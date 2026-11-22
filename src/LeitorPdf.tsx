import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { BotaoVoltar, MenuIr } from './Navegar';
import { caminho } from './ambiente';
import type { Catalogo } from './catalogo';

type Doc = {
  numPages: number;
  getPage: (n: number) => Promise<{
    getViewport: (o: { scale: number }) => { width: number; height: number };
    render: (o: { canvasContext: CanvasRenderingContext2D; viewport: unknown }) => { promise: Promise<void>; cancel: () => void };
  }>;
};

async function abrirPdf(url: string): Promise<Doc> {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const worker = (await import('pdfjs-dist/legacy/build/pdf.worker.min.mjs?url')).default;
  pdfjs.GlobalWorkerOptions.workerSrc = worker;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error('Não consegui abrir o arquivo.');
  const dados = new Uint8Array(await resp.arrayBuffer());
  return (await pdfjs.getDocument({ data: dados }).promise) as unknown as Doc;
}

function Folha({ doc, n, proporcao }: { doc: Doc; n: number; proporcao: number }) {
  const caixa = useRef<HTMLDivElement>(null);
  const tela = useRef<HTMLCanvasElement>(null);
  const tarefa = useRef<{ cancel: () => void } | null>(null);
  const visivel = useRef(false);
  const [altura, setAltura] = useState<number | null>(null);

  useEffect(() => {
    const el = caixa.current;
    if (!el) return;
    let vivo = true;
    async function desenhar() {
      const c = tela.current;
      if (!c || !el) return;
      const pagina = await doc.getPage(n);
      if (!vivo || !visivel.current) return;
      const largura = el.clientWidth;
      const base = pagina.getViewport({ scale: 1 });
      const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
      const escala = (largura / base.width) * dpr;
      const vp = pagina.getViewport({ scale: escala });
      c.width = Math.floor(vp.width);
      c.height = Math.floor(vp.height);
      c.style.width = '100%';
      setAltura((largura * base.height) / base.width);
      const ctx = c.getContext('2d');
      if (!ctx) return;
      tarefa.current?.cancel();
      const t = pagina.render({ canvasContext: ctx, viewport: vp });
      tarefa.current = t;
      try {
        await t.promise;
      } catch {
        /* cancelado */
      }
    }
    function limpar() {
      tarefa.current?.cancel();
      const c = tela.current;
      if (c) {
        c.width = 1;
        c.height = 1;
      }
    }
    const obs = new IntersectionObserver(
      (es) => {
        for (const e of es) {
          visivel.current = e.isIntersecting;
          if (e.isIntersecting) void desenhar();
          else limpar();
        }
      },
      { rootMargin: '120% 0px' },
    );
    obs.observe(el);
    return () => {
      vivo = false;
      obs.disconnect();
      tarefa.current?.cancel();
    };
  }, [doc, n]);

  return (
    <div className="pdf-folha" data-pagina={n} ref={caixa} style={{ height: altura ?? undefined, aspectRatio: altura ? undefined : String(proporcao) }}>
      <canvas ref={tela} />
    </div>
  );
}

export function LeitorPdf({ catalogo }: { catalogo: Catalogo }) {
  const { n } = useParams();
  const secao = catalogo.secoes.find((s) => s.id === 'lavras');
  const arq = secao?.arquivos?.[Number(n)];
  const [doc, setDoc] = useState<Doc | null>(null);
  const [proporcao, setProporcao] = useState(0.707);
  const [erro, setErro] = useState('');
  const [atual, setAtual] = useState(1);
  const rolagem = useRef<HTMLDivElement>(null);
  const chave = `pdf-pagina:${arq?.url ?? ''}`;

  useEffect(() => {
    if (!arq) return;
    let vivo = true;
    abrirPdf(caminho(arq.url))
      .then(async (d) => {
        const p1 = await d.getPage(1);
        const v = p1.getViewport({ scale: 1 });
        if (!vivo) return;
        setProporcao(v.width / v.height);
        setDoc(d);
      })
      .catch(() => vivo && setErro('Não consegui abrir este PDF. Confira a internet (ou baixe as músicas no aparelho para abrir sem internet).'));
    return () => {
      vivo = false;
    };
  }, [arq]);

  // volta exatamente para a página onde a pessoa estava
  useEffect(() => {
    if (!doc) return;
    const salva = Number(localStorage.getItem(chave) || 1);
    if (salva > 1) {
      requestAnimationFrame(() => {
        const alvo = rolagem.current?.querySelector(`[data-pagina="${salva}"]`);
        alvo?.scrollIntoView({ block: 'start' });
      });
    }
  }, [doc, chave]);

  function aoRolar() {
    const r = rolagem.current;
    if (!r) return;
    const topo = r.getBoundingClientRect().top;
    const folhas = r.querySelectorAll<HTMLElement>('.pdf-folha');
    let p = 1;
    for (const f of Array.from(folhas)) {
      if (f.getBoundingClientRect().top - topo <= r.clientHeight * 0.4) p = Number(f.dataset.pagina);
      else break;
    }
    setAtual(p);
    try {
      localStorage.setItem(chave, String(p));
    } catch {
      /* ignora */
    }
  }

  if (!secao || !arq) {
    return (
      <div className="aviso">
        <h1>PDF não encontrado</h1>
        <Link className="botao" to="/lavras/arquivos-pdf">
          Voltar aos arquivos PDF
        </Link>
      </div>
    );
  }

  return (
    <div className="pagina pagina-pdf">
      <header className="topo topo-lavras">
        <BotaoVoltar fallback="/lavras/arquivos-pdf" />
        <div>
          <p className="topo-sub">Arquivos PDF</p>
          <h1>{arq.nome}</h1>
        </div>
        <MenuIr />
      </header>
      <div className="pdf-rolagem" ref={rolagem} onScroll={aoRolar}>
        {erro && <p className="pdf-erro">{erro}</p>}
        {!doc && !erro && <p className="pdf-carregando">Abrindo o PDF…</p>}
        {doc && Array.from({ length: doc.numPages }, (_, i) => <Folha key={i} doc={doc} n={i + 1} proporcao={proporcao} />)}
      </div>
      {doc && (
        <div className="pdf-contador" aria-live="polite">
          {atual} de {doc.numPages}
        </div>
      )}
    </div>
  );
}
