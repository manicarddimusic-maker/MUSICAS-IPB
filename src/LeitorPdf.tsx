import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { BotaoVoltar, MenuIr } from './Navegar';
import { caminho } from './ambiente';
import type { Catalogo } from './catalogo';

type Pagina = {
  getViewport: (o: { scale: number }) => { width: number; height: number };
  render: (o: { canvasContext: CanvasRenderingContext2D; viewport: unknown }) => { promise: Promise<void>; cancel: () => void };
};
type Doc = { numPages: number; getPage: (n: number) => Promise<Pagina>; destroy?: () => void };

async function abrirPdf(url: string): Promise<Doc> {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
  const worker = (await import('pdfjs-dist/legacy/build/pdf.worker.min.mjs?url')).default;
  pdfjs.GlobalWorkerOptions.workerSrc = worker;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error('Não consegui abrir o arquivo.');
  const dados = new Uint8Array(await resp.arrayBuffer());
  return (await pdfjs.getDocument({ data: dados }).promise) as unknown as Doc;
}

const ZMIN = 1;
const ZMAX = 6;

export function LeitorPdf({ catalogo }: { catalogo: Catalogo }) {
  const { n: nArq } = useParams();
  const secao = catalogo.secoes.find((s) => s.id === 'lavras');
  const arq = secao?.arquivos?.[Number(nArq)];
  const chave = `pdf-pagina:${arq?.url ?? ''}`;

  const [doc, setDoc] = useState<Doc | null>(null);
  const [erro, setErro] = useState('');
  const [pag, setPag] = useState(() => Math.max(1, Number(localStorage.getItem(chave) || 1)));
  const [zoom, setZoomEstado] = useState(1);

  const palco = useRef<HTMLDivElement>(null);
  const tela = useRef<HTMLCanvasElement>(null);
  const vista = useRef({ z: 1, x: 0, y: 0 });
  const tam = useRef({ w: 0, h: 0 }); // tamanho (css) da folha ajustada ao palco
  const tarefa = useRef<{ cancel: () => void } | null>(null);
  const nitidez = useRef<number | undefined>(undefined);
  const ponteiros = useRef(new Map<number, { x: number; y: number }>());
  const gesto = useRef<{ d0: number; z0: number; x: number; y: number; vx: number; vy: number; t: number; moveu: boolean } | null>(null);
  const ultimoToque = useRef(0);

  useEffect(() => {
    if (!arq) return;
    let vivo = true;
    let aberto: Doc | null = null;
    abrirPdf(caminho(arq.url))
      .then((d) => {
        aberto = d;
        if (!vivo) return d.destroy?.();
        setDoc(d);
        setPag((p) => Math.min(Math.max(1, p), d.numPages));
      })
      .catch(() => vivo && setErro('Não consegui abrir este PDF. Confira a internet (ou baixe as músicas no aparelho para abrir sem internet).'));
    return () => {
      vivo = false;
      aberto?.destroy?.();
    };
  }, [arq]);

  const limitar = useCallback((x: number, y: number, z: number) => {
    const p = palco.current;
    if (!p) return { x: 0, y: 0 };
    const mx = Math.max(0, (tam.current.w * z - p.clientWidth) / 2);
    const my = Math.max(0, (tam.current.h * z - p.clientHeight) / 2);
    return { x: Math.min(mx, Math.max(-mx, x)), y: Math.min(my, Math.max(-my, y)) };
  }, []);

  const aplicar = useCallback(() => {
    const c = tela.current;
    if (!c) return;
    const v = vista.current;
    c.style.transform = `translate(${v.x}px, ${v.y}px) scale(${v.z})`;
  }, []);

  // desenha a página inteira ajustada ao palco, com a nitidez pedida (mais nítida quando há zoom)
  const desenhar = useCallback(
    async (n: number) => {
      const p = palco.current;
      const c = tela.current;
      if (!doc || !p || !c) return;
      const pagina = await doc.getPage(n);
      const base = pagina.getViewport({ scale: 1 });
      const ajuste = Math.min(p.clientWidth / base.width, p.clientHeight / base.height);
      tam.current = { w: base.width * ajuste, h: base.height * ajuste };
      const dpr = Math.min(window.devicePixelRatio || 1, 3);
      let escala = ajuste * dpr * Math.max(1, vista.current.z);
      const maior = Math.max(base.width, base.height) * escala;
      if (maior > 4096) escala *= 4096 / maior;
      const vp = pagina.getViewport({ scale: escala });
      const fora = document.createElement('canvas');
      fora.width = Math.floor(vp.width);
      fora.height = Math.floor(vp.height);
      const ctx = fora.getContext('2d');
      if (!ctx) return;
      tarefa.current?.cancel();
      const t = pagina.render({ canvasContext: ctx, viewport: vp });
      tarefa.current = t;
      try {
        await t.promise;
      } catch {
        return; // cancelado por outro desenho
      }
      c.width = fora.width;
      c.height = fora.height;
      c.getContext('2d')?.drawImage(fora, 0, 0);
      c.style.width = `${tam.current.w}px`;
      c.style.height = `${tam.current.h}px`;
      nitidez.current = vista.current.z;
      const lim = limitar(vista.current.x, vista.current.y, vista.current.z);
      vista.current = { ...vista.current, ...lim };
      aplicar();
    },
    [doc, limitar, aplicar],
  );

  // troca de página: volta ao ajuste inicial
  useEffect(() => {
    if (!doc) return;
    vista.current = { z: 1, x: 0, y: 0 };
    setZoomEstado(1);
    void desenhar(pag);
    try {
      localStorage.setItem(chave, String(pag));
    } catch {
      /* ignora */
    }
  }, [doc, pag, desenhar, chave]);

  // girar o aparelho / mudar o tamanho da janela
  useEffect(() => {
    const aoRedimensionar = () => void desenhar(pag);
    window.addEventListener('resize', aoRedimensionar);
    return () => window.removeEventListener('resize', aoRedimensionar);
  }, [desenhar, pag]);

  // depois de mexer no zoom, refaz a página mais nítida
  const timer = useRef<number | undefined>(undefined);
  const refinar = useCallback(() => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      if (nitidez.current === undefined || Math.abs((nitidez.current ?? 1) - vista.current.z) > 0.2) void desenhar(pag);
    }, 220);
  }, [desenhar, pag]);

  const definirZoom = useCallback(
    (z: number, cx = 0, cy = 0) => {
      const v = vista.current;
      const novo = Math.min(ZMAX, Math.max(ZMIN, z));
      const k = novo / v.z;
      // mantém o ponto (cx, cy) — relativo ao centro do palco — parado na tela
      const lim = novo === 1 ? { x: 0, y: 0 } : limitar(cx - (cx - v.x) * k, cy - (cy - v.y) * k, novo);
      vista.current = { z: novo, x: lim.x, y: lim.y };
      setZoomEstado(novo);
      aplicar();
      refinar();
    },
    [aplicar, limitar, refinar],
  );

  const total = doc?.numPages ?? 0;
  const irPara = useCallback((n: number) => setPag((p) => Math.min(Math.max(1, n), total || p)), [total]);

  function centro(e: { clientX: number; clientY: number }) {
    const r = palco.current!.getBoundingClientRect();
    return { x: e.clientX - r.left - r.width / 2, y: e.clientY - r.top - r.height / 2 };
  }

  function aoPressionar(e: React.PointerEvent) {
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    ponteiros.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const v = vista.current;
    if (ponteiros.current.size === 2) {
      const [a, b] = [...ponteiros.current.values()];
      gesto.current = { d0: Math.hypot(a.x - b.x, a.y - b.y) || 1, z0: v.z, x: 0, y: 0, vx: v.x, vy: v.y, t: Date.now(), moveu: true };
    } else {
      gesto.current = { d0: 0, z0: v.z, x: e.clientX, y: e.clientY, vx: v.x, vy: v.y, t: Date.now(), moveu: false };
    }
  }

  function aoMover(e: React.PointerEvent) {
    if (!ponteiros.current.has(e.pointerId) || !gesto.current) return;
    ponteiros.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const g = gesto.current;
    if (ponteiros.current.size >= 2) {
      const [a, b] = [...ponteiros.current.values()];
      const d = Math.hypot(a.x - b.x, a.y - b.y) || 1;
      const c = centro({ clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2 });
      definirZoom(g.z0 * (d / g.d0), c.x, c.y);
    } else if (vista.current.z > 1) {
      const dx = e.clientX - g.x;
      const dy = e.clientY - g.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) g.moveu = true;
      const lim = limitar(g.vx + dx, g.vy + dy, vista.current.z);
      vista.current = { ...vista.current, ...lim };
      aplicar();
    } else if (Math.abs(e.clientX - g.x) + Math.abs(e.clientY - g.y) > 6) {
      g.moveu = true;
    }
  }

  function aoSoltar(e: React.PointerEvent) {
    const g = gesto.current;
    ponteiros.current.delete(e.pointerId);
    if (!g) return;
    if (ponteiros.current.size > 0) {
      // sobrou um dedo depois da pinça: recomeça o arrasto dele
      const [r] = [...ponteiros.current.values()];
      gesto.current = { ...g, d0: 0, x: r.x, y: r.y, vx: vista.current.x, vy: vista.current.y };
      return;
    }
    gesto.current = null;
    const dx = e.clientX - g.x;
    const dy = e.clientY - g.y;
    const agora = Date.now();
    if (g.d0 === 0 && !g.moveu) {
      // toque rápido: duplo toque alterna entre ajustar e ampliar
      if (agora - ultimoToque.current < 320) {
        const c = centro(e);
        if (vista.current.z > 1.05) definirZoom(1);
        else definirZoom(2.5, c.x, c.y);
        ultimoToque.current = 0;
      } else ultimoToque.current = agora;
    } else if (g.d0 === 0 && vista.current.z <= 1.05 && Math.abs(dx) > 60 && Math.abs(dy) < 90 && agora - g.t < 700) {
      irPara(pag + (dx < 0 ? 1 : -1)); // arrastar para o lado vira a página
    }
  }

  // roda do mouse / pinça do trackpad
  useEffect(() => {
    const p = palco.current;
    if (!p) return;
    const roda = (e: WheelEvent) => {
      e.preventDefault();
      const c = centro(e);
      if (e.ctrlKey || e.metaKey) definirZoom(vista.current.z * Math.exp(-e.deltaY * 0.01), c.x, c.y);
      else if (vista.current.z > 1) {
        const lim = limitar(vista.current.x - e.deltaX, vista.current.y - e.deltaY, vista.current.z);
        vista.current = { ...vista.current, ...lim };
        aplicar();
      }
    };
    p.addEventListener('wheel', roda, { passive: false });
    return () => p.removeEventListener('wheel', roda);
  }, [definirZoom, limitar, aplicar, doc]);

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'PageDown') irPara(pag + 1);
      else if (e.key === 'ArrowLeft' || e.key === 'PageUp') irPara(pag - 1);
      else if (e.key === '+' || e.key === '=') definirZoom(vista.current.z * 1.5);
      else if (e.key === '-') definirZoom(vista.current.z / 1.5);
      else if (e.key === '0') definirZoom(1);
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [pag, irPara, definirZoom]);

  function perguntarPagina() {
    const r = window.prompt(`Ir para a página (1 a ${total}):`, String(pag));
    const n = Number(r);
    if (r && Number.isFinite(n)) irPara(Math.round(n));
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
      <div
        className="pdf-palco"
        ref={palco}
        onPointerDown={aoPressionar}
        onPointerMove={aoMover}
        onPointerUp={aoSoltar}
        onPointerCancel={aoSoltar}
      >
        {erro && <p className="pdf-erro">{erro}</p>}
        {!doc && !erro && <p className="pdf-carregando">Abrindo o PDF…</p>}
        <canvas ref={tela} className="pdf-tela" />
      </div>
      {doc && (
        <div className="pdf-barra" role="toolbar" aria-label="Controles do PDF">
          <button onClick={() => irPara(pag - 1)} disabled={pag <= 1} aria-label="Página anterior">
            ‹
          </button>
          <button className="pdf-pagina-btn" onClick={perguntarPagina} aria-label="Ir para uma página">
            {pag} de {total}
          </button>
          <button onClick={() => irPara(pag + 1)} disabled={pag >= total} aria-label="Próxima página">
            ›
          </button>
          <span className="pdf-sep" aria-hidden="true" />
          <button onClick={() => definirZoom(vista.current.z / 1.5)} disabled={zoom <= ZMIN} aria-label="Diminuir o zoom">
            −
          </button>
          <button className="pdf-zoom-btn" onClick={() => definirZoom(1)} aria-label="Ajustar a folha na tela">
            {zoom <= 1.01 ? 'Ajustar' : `${Math.round(zoom * 10) / 10}×`}
          </button>
          <button onClick={() => definirZoom(vista.current.z * 1.5)} disabled={zoom >= ZMAX} aria-label="Aumentar o zoom">
            +
          </button>
        </div>
      )}
    </div>
  );
}
