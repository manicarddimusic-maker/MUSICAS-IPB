import { memo, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { BotaoVoltar, MenuIr } from './Navegar';
import { caminho } from './ambiente';
import type { Catalogo } from './catalogo';
import CifrasSobre from './CifrasSobre';
import PainelTom from './PainelTom';
import { FolhaCifras, carregarCifras, fontesProntas, tomDaFolha, transpositorDaFolha } from './cifras';
import { nomeTom, tomTransposto } from './tom';

type CifrasPdf = Record<string, FolhaCifras>;
const SEM_TONS: Record<number, number> = {};

/** Camada das cifras no novo tom por cima de uma página do PDF. */
const SobrePagina = memo(function SobrePagina({
  folha,
  semitons,
  versao,
  className,
  style,
  aoMontar,
}: {
  folha: FolhaCifras;
  semitons: number;
  versao: number;
  className?: string;
  style?: React.CSSProperties;
  aoMontar?: (el: SVGSVGElement | null) => void;
}) {
  const transpor = useMemo(() => transpositorDaFolha(semitons, tomDaFolha(undefined, folha, []), folha), [semitons, folha]);
  return <CifrasSobre ref={aoMontar} folha={folha} transpor={transpor} versao={versao} className={className} style={style} />;
});

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
const ZMAX = 5;
const PASSO = 0.25;
const CHAVE_ZOOM = 'hinario-zoom';
const arredondar = (z: number) => Math.round(z * 4) / 4;
function lerZoomSalvo(): number {
  try {
    const z = Number(localStorage.getItem(CHAVE_ZOOM));
    return Number.isFinite(z) && z >= 1.03 ? Math.min(ZMAX, z) : 1;
  } catch {
    return 1;
  }
}

const FOLGA = 10; // espaço entre as folhas no modo "rolar"

/** Modo rolagem: todas as folhas uma embaixo da outra; é só arrastar para cima/baixo, como numa página da internet. */
function Rolagem({
  doc,
  pagInicial,
  zoom,
  aoMudarPagina,
  irRef,
  cifras,
  tons,
  versaoFontes,
}: {
  doc: Doc;
  pagInicial: number;
  zoom: number;
  aoMudarPagina: (n: number) => void;
  irRef: React.MutableRefObject<((n: number) => void) | null>;
  cifras: CifrasPdf | null;
  tons: Record<number, number>;
  versaoFontes: number;
}) {
  const cont = useRef<HTMLDivElement>(null);
  const [larg, setLarg] = useState(0);
  const [aspecto, setAspecto] = useState(1.414);
  const feitas = useRef(new Map<number, number>());
  const proximas = useRef(new Set<number>());
  const ocupado = useRef(false);
  const atual = useRef(pagInicial);
  const largPag = Math.max(160, (larg - 16) * zoom);
  const altPag = largPag * aspecto;
  const largRef = useRef(largPag);
  largRef.current = largPag;

  useEffect(() => {
    const el = cont.current;
    if (!el) return;
    const medir = () => setLarg(el.clientWidth);
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    void doc.getPage(1).then((pg) => {
      const b = pg.getViewport({ scale: 1 });
      if (b.width > 0) setAspecto(b.height / b.width);
    });
    return () => ro.disconnect();
  }, [doc]);

  const processar = useCallback(async () => {
    if (ocupado.current) return;
    ocupado.current = true;
    try {
      for (;;) {
        const alvo = [...proximas.current]
          .filter((n) => feitas.current.get(n) !== largRef.current)
          .sort((a, b) => Math.abs(a - atual.current) - Math.abs(b - atual.current))[0];
        if (alvo === undefined) break;
        const caixa = cont.current?.querySelector<HTMLDivElement>(`[data-n="${alvo}"]`);
        const canvas = caixa?.querySelector('canvas');
        if (!caixa || !canvas) {
          proximas.current.delete(alvo);
          continue;
        }
        const largura = largRef.current;
        const pagina = await doc.getPage(alvo);
        const base = pagina.getViewport({ scale: 1 });
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        let escala = (largura / base.width) * dpr;
        const maior = Math.max(base.width, base.height) * escala;
        if (maior > 4096) escala *= 4096 / maior;
        const vp = pagina.getViewport({ scale: escala });
        const fora = document.createElement('canvas');
        fora.width = Math.floor(vp.width);
        fora.height = Math.floor(vp.height);
        const ctx = fora.getContext('2d');
        if (!ctx) break;
        await pagina.render({ canvasContext: ctx, viewport: vp }).promise;
        if (largura !== largRef.current || !proximas.current.has(alvo)) continue; // mudou enquanto desenhava
        canvas.width = fora.width;
        canvas.height = fora.height;
        canvas.getContext('2d')?.drawImage(fora, 0, 0);
        feitas.current.set(alvo, largura);
      }
    } catch {
      /* próxima tentativa acontece ao rolar */
    } finally {
      ocupado.current = false;
    }
  }, [doc]);

  // desenha só as folhas perto da tela; as distantes são liberadas para não pesar a memória
  useEffect(() => {
    const el = cont.current;
    if (!el || !larg) return;
    const io = new IntersectionObserver(
      (ents) => {
        for (const e of ents) {
          const n = Number((e.target as HTMLElement).dataset.n);
          if (e.isIntersecting) proximas.current.add(n);
          else {
            proximas.current.delete(n);
            const c = (e.target as HTMLElement).querySelector('canvas');
            if (c && feitas.current.has(n)) {
              c.width = 0;
              c.height = 0;
              feitas.current.delete(n);
            }
          }
        }
        void processar();
      },
      { root: el, rootMargin: '150% 0px' },
    );
    el.querySelectorAll('[data-n]').forEach((x) => io.observe(x));
    return () => io.disconnect();
  }, [larg, doc, processar]);

  // largura nova (zoom ou girar a tela): refaz as folhas e mantém a mesma folha na tela
  const pagAntes = useRef(pagInicial);
  const primeira = useRef(true);
  useLayoutEffect(() => {
    const el = cont.current;
    if (!el || !larg) return;
    feitas.current.clear();
    const n = primeira.current ? pagInicial : pagAntes.current;
    primeira.current = false;
    el.scrollTop = (n - 1) * (altPag + FOLGA);
    void processar();
  }, [larg, largPag, altPag, pagInicial, processar]);

  const quadro = useRef(0);
  function aoRolar() {
    if (quadro.current) return;
    quadro.current = requestAnimationFrame(() => {
      quadro.current = 0;
      const el = cont.current;
      if (!el) return;
      const n = Math.min(doc.numPages, Math.max(1, Math.floor((el.scrollTop + el.clientHeight / 2) / (altPag + FOLGA)) + 1));
      pagAntes.current = n;
      if (n !== atual.current) {
        atual.current = n;
        aoMudarPagina(n);
        void processar();
      }
    });
  }

  useEffect(() => {
    irRef.current = (n: number) => {
      const el = cont.current;
      if (el) el.scrollTop = (Math.min(Math.max(1, n), doc.numPages) - 1) * (altPag + FOLGA);
    };
    return () => {
      irRef.current = null;
    };
  }, [altPag, doc, irRef]);

  return (
    <div className="pdf-rolagem" ref={cont} onScroll={aoRolar}>
      <div className="pdf-rolagem-lista">
        {Array.from({ length: doc.numPages }, (_, i) => (
          <div key={i} data-n={i + 1} className="pdf-folha" style={{ width: largPag, height: altPag }}>
            <canvas />
            {tons[i + 1] && cifras?.[i + 1] ? (
              <SobrePagina folha={cifras[i + 1]} semitons={tons[i + 1]} versao={versaoFontes} className="pdf-cifras" />
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

export function LeitorPdf({ catalogo }: { catalogo: Catalogo }) {
  const { n: nArq, secaoId } = useParams();
  const secao = catalogo.secoes.find((s) => s.id === (secaoId ?? 'lavras'));
  const voltarPara = `/${secao?.id ?? 'lavras'}/arquivos-pdf`;
  const arq = secao?.arquivos?.[Number(nArq)];
  const chave = `pdf-pagina:${arq?.url ?? ''}`;

  const [doc, setDoc] = useState<Doc | null>(null);
  const [erro, setErro] = useState('');
  const [pag, setPag] = useState(() => Math.max(1, Number(localStorage.getItem(chave) || 1)));
  const [zoom, setZoomEstado] = useState(lerZoomSalvo);
  const [rolar, setRolar] = useState(() => {
    try {
      return localStorage.getItem('pdf-modo') === 'rolar';
    } catch {
      return false;
    }
  });
  const [pagVista, setPagVista] = useState(pag);
  const irRolagem = useRef<((n: number) => void) | null>(null);

  // ---- mudança de tom (cada página do PDF guarda o seu) ----
  const nomeCifras = arq ? 'pdf-' + (arq.url.split('/').pop() ?? '').replace(/\.pdf$/i, '') : '';
  const chaveTons = `hinario-tom:${nomeCifras}`;
  const [cifras, setCifras] = useState<CifrasPdf | null>(null);
  const [tons, setTons] = useState<Record<number, number>>(SEM_TONS);
  const [painelTom, setPainelTom] = useState(false);
  const [versaoFontes, setVersaoFontes] = useState(0);
  const [tamCss, setTamCss] = useState({ w: 0, h: 0 });
  const sobre = useRef<SVGSVGElement | null>(null);
  useEffect(() => {
    if (!nomeCifras) return;
    let vivo = true;
    setCifras(null);
    carregarCifras(nomeCifras).then((c) => vivo && setCifras(c));
    try {
      const j = JSON.parse(localStorage.getItem(chaveTons) || '{}') as Record<string, number>;
      const limpo: Record<number, number> = {};
      for (const [k, v] of Object.entries(j)) if (Number.isFinite(v) && v) limpo[Number(k)] = Math.max(-6, Math.min(6, Math.round(v)));
      setTons(limpo);
    } catch {
      setTons(SEM_TONS);
    }
    fontesProntas().then(() => vivo && setVersaoFontes((v) => v + 1));
    return () => {
      vivo = false;
    };
  }, [nomeCifras, chaveTons]);

  const palco = useRef<HTMLDivElement>(null);
  const tela = useRef<HTMLCanvasElement>(null);
  const vista = useRef({ z: lerZoomSalvo(), x: 0, y: 0 });
  const topoPendente = useRef(true);
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
    if (sobre.current) sobre.current.style.transform = c.style.transform;
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
      if (topoPendente.current) {
        // folha nova com zoom travado: começa pelo topo
        topoPendente.current = false;
        const l0 = limitar(0, 1e9, vista.current.z);
        vista.current = { ...vista.current, x: l0.x, y: l0.y };
      }
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
      setTamCss((t) => (Math.abs(t.w - tam.current.w) < 0.5 && Math.abs(t.h - tam.current.h) < 0.5 ? t : { w: tam.current.w, h: tam.current.h }));
      nitidez.current = vista.current.z;
      const lim = limitar(vista.current.x, vista.current.y, vista.current.z);
      vista.current = { ...vista.current, ...lim };
      aplicar();
    },
    [doc, limitar, aplicar],
  );

  // troca de página: volta ao ajuste inicial
  useEffect(() => {
    if (!doc || rolar) return;
    vista.current = { z: lerZoomSalvo(), x: 0, y: 0 };
    topoPendente.current = true;
    setZoomEstado(vista.current.z);
    void desenhar(pag);
    try {
      localStorage.setItem(chave, String(pag));
    } catch {
      /* ignora */
    }
  }, [doc, pag, desenhar, chave, rolar]);

  // girar o aparelho / mudar o tamanho da janela
  useEffect(() => {
    if (rolar) return;
    const aoRedimensionar = () => void desenhar(pag);
    window.addEventListener('resize', aoRedimensionar);
    return () => window.removeEventListener('resize', aoRedimensionar);
  }, [desenhar, pag, rolar]);

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
      try {
        localStorage.setItem(CHAVE_ZOOM, String(novo < 1.03 ? 1 : Math.round(novo * 100) / 100));
      } catch {
        /* ignora */
      }
      aplicar();
      refinar();
    },
    [aplicar, limitar, refinar],
  );

  const total = doc?.numPages ?? 0;
  const irPara = useCallback(
    (n: number) => {
      const alvo = Math.min(Math.max(1, n), total || 1);
      if (rolar) irRolagem.current?.(alvo);
      else setPag(alvo);
    },
    [total, rolar],
  );

  // o mesmo + e − serve nos dois modos
  const mudarZoom = useCallback(
    (z: number) => {
      if (!rolar) return definirZoom(z);
      const novo = Math.min(ZMAX, Math.max(ZMIN, z));
      setZoomEstado(novo);
      try {
        localStorage.setItem(CHAVE_ZOOM, String(novo < 1.03 ? 1 : Math.round(novo * 100) / 100));
      } catch {
        /* ignora */
      }
    },
    [rolar, definirZoom],
  );

  function alternarModo() {
    const vaiRolar = !rolar;
    if (vaiRolar) setPagVista(pag);
    else setPag(pagVista);
    setRolar(vaiRolar);
    try {
      localStorage.setItem('pdf-modo', vaiRolar ? 'rolar' : 'folha');
    } catch {
      /* ignora */
    }
  }

  const paginaMostrada = rolar ? pagVista : pag;
  const folhaCifras = cifras?.[paginaMostrada];
  const temCifras = !!folhaCifras && folhaCifras.c.some((c) => c[4] !== '?' && c[4] !== '');
  const semitons = tons[paginaMostrada] ?? 0;
  const tomOriginal = useMemo(() => tomDaFolha(undefined, folhaCifras, []), [folhaCifras]);
  const nomeTomAtual = tomOriginal ? nomeTom(tomTransposto(tomOriginal, semitons)) : null;
  const ilegiveis = folhaCifras ? folhaCifras.c.filter((c) => c[4] === '?').length : 0;
  function mudarTom(n: number) {
    setTons((antes) => {
      const novo = { ...antes };
      if (n === 0) delete novo[paginaMostrada];
      else novo[paginaMostrada] = n;
      try {
        if (Object.keys(novo).length) localStorage.setItem(chaveTons, JSON.stringify(novo));
        else localStorage.removeItem(chaveTons);
      } catch {
        /* sem armazenamento */
      }
      return novo;
    });
  }

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
        else definirZoom(1.75, c.x, c.y);
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
  }, [definirZoom, limitar, aplicar, doc, rolar]);

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (rolar) return; // no modo rolar, as setas e o PageDown já rolam sozinhos
      if (e.key === 'ArrowRight' || e.key === 'PageDown') irPara(pag + 1);
      else if (e.key === 'ArrowLeft' || e.key === 'PageUp') irPara(pag - 1);
      else if (e.key === '+' || e.key === '=') definirZoom(arredondar(vista.current.z + PASSO));
      else if (e.key === '-') definirZoom(arredondar(vista.current.z - PASSO));
      else if (e.key === '0') definirZoom(1);
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [pag, irPara, definirZoom, rolar]);

  function perguntarPagina() {
    const r = window.prompt(`Ir para a página (1 a ${total}):`, String(paginaMostrada));
    const n = Number(r);
    if (r && Number.isFinite(n)) irPara(Math.round(n));
  }

  if (!secao || !arq) {
    return (
      <div className="aviso">
        <h1>PDF não encontrado</h1>
        <Link className="botao" to={voltarPara}>
          Voltar aos arquivos PDF
        </Link>
      </div>
    );
  }

  return (
    <div className="pagina pagina-pdf">
      <header className="topo topo-lavras">
        <BotaoVoltar fallback={voltarPara} />
        <div>
          <p className="topo-sub">Arquivos PDF</p>
          <h1>{arq.nome}</h1>
        </div>
        <MenuIr />
      </header>
      {rolar && doc ? (
        <Rolagem
          doc={doc}
          pagInicial={pag}
          zoom={zoom}
          irRef={irRolagem}
          cifras={cifras}
          tons={tons}
          versaoFontes={versaoFontes}
          aoMudarPagina={(n) => {
            setPagVista(n);
            try {
              localStorage.setItem(chave, String(n));
            } catch {
              /* ignora */
            }
          }}
        />
      ) : (
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
          {doc && semitons !== 0 && folhaCifras && tamCss.w > 0 && (
            <SobrePagina
              key={`cifras:${pag}`}
              folha={folhaCifras}
              semitons={semitons}
              versao={versaoFontes}
              className="pdf-tela pdf-cifras"
              style={{ width: tamCss.w, height: tamCss.h, transform: `translate(${vista.current.x}px, ${vista.current.y}px) scale(${vista.current.z})` }}
              aoMontar={(el) => {
                sobre.current = el;
              }}
            />
          )}
        </div>
      )}
      {doc && (
        <div className="pdf-barra" role="toolbar" aria-label="Controles do PDF">
          <button onClick={() => irPara(paginaMostrada - 1)} disabled={paginaMostrada <= 1} aria-label="Página anterior">
            ‹
          </button>
          <button className="pdf-pagina-btn" onClick={perguntarPagina} aria-label="Ir para uma página">
            {paginaMostrada} de {total}
          </button>
          <button onClick={() => irPara(paginaMostrada + 1)} disabled={paginaMostrada >= total} aria-label="Próxima página">
            ›
          </button>
          <span className="pdf-sep" aria-hidden="true" />
          <button onClick={() => mudarZoom(arredondar(zoom - PASSO))} disabled={zoom <= ZMIN} aria-label="Diminuir o zoom">
            −
          </button>
          <button className="pdf-zoom-btn" onClick={() => mudarZoom(1)} aria-label="Ajustar a folha na tela">
            {zoom <= 1.01 ? 'Ajustar' : `${Math.round(zoom * 100) / 100}×`}
          </button>
          <button onClick={() => mudarZoom(arredondar(zoom + PASSO))} disabled={zoom >= ZMAX} aria-label="Aumentar o zoom">
            +
          </button>
          <span className="pdf-sep" aria-hidden="true" />
          <button
            className={`pdf-modo-btn${rolar ? ' ativo' : ''}`}
            onClick={alternarModo}
            aria-pressed={rolar}
            aria-label={rolar ? 'Voltar a uma folha por vez' : 'Rolar as páginas para cima e para baixo'}
          >
            ↕
          </button>
          <button
            className={`pdf-tom-btn${semitons !== 0 ? ' ativo' : ''}`}
            onClick={() => setPainelTom((v) => !v)}
            aria-expanded={painelTom}
            aria-label="Mudar o tom das cifras desta página"
          >
            ♯♭{semitons !== 0 && nomeTomAtual ? ` ${nomeTomAtual}` : ''}
          </button>
        </div>
      )}
      {doc && painelTom && (
        <PainelTom
          className="painel-tom-pdf"
          tom={tomOriginal}
          semitons={semitons}
          temCifras={temCifras}
          ilegiveis={ilegiveis}
          duvidosa={folhaCifras?.q === 1}
          aoMudar={mudarTom}
          aoFechar={() => setPainelTom(false)}
        />
      )}
    </div>
  );
}
