import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Item, Secao, rotuloCompleto } from './catalogo';

type Props = {
  secao: Secao;
  item: Item;
  anterior?: Item;
  proximo?: Item;
};

const ZOOMS = [1, 2, 3.5];

export default function Leitor({ secao, item, anterior, proximo }: Props) {
  const [pagina, setPagina] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [desloc, setDesloc] = useState({ x: 0, y: 0 });
  const [rotacao, setRotacao] = useState(0);
  const [areaTam, setAreaTam] = useState({ w: 0, h: 0 });
  const [falhou, setFalhou] = useState(false);
  const navigate = useNavigate();
  const area = useRef<HTMLDivElement>(null);
  const imagem = useRef<HTMLImageElement>(null);
  const ponteiros = useRef(new Map<number, { x: number; y: number }>());
  const gesto = useRef({ distancia: 0, zoom: 1, x: 0, y: 0, dx: 0, dy: 0, pan: false, x0: 0, y0: 0, t0: 0 });

  const paginas = item.paginas;
  const atual = paginas[Math.min(pagina, paginas.length - 1)];
  const lateral = rotacao === 90 || rotacao === 270;

  // limites para a folha nunca sair da tela ao ampliar
  const limitar = useCallback(
    (x: number, y: number, z: number) => {
      const im = imagem.current;
      const { w, h } = areaTam;
      if (!im || !im.naturalWidth || !w) return { x: 0, y: 0 };
      const A = lateral ? im.naturalHeight : im.naturalWidth;
      const B = lateral ? im.naturalWidth : im.naturalHeight;
      const k = Math.min(w / A, h / B);
      const maxX = Math.max(0, (A * k * z - w) / 2);
      const maxY = Math.max(0, (B * k * z - h) / 2);
      return { x: Math.min(maxX, Math.max(-maxX, x)), y: Math.min(maxY, Math.max(-maxY, y)) };
    },
    [areaTam, lateral],
  );

  function definirZoom(z: number) {
    const novo = Math.min(5, Math.max(1, z));
    setZoom(novo);
    setDesloc((d) => (novo === 1 ? { x: 0, y: 0 } : limitar(d.x, d.y, novo)));
  }

  useEffect(() => {
    setPagina(0);
  }, [item.id]);

  useEffect(() => {
    setZoom(1);
    setDesloc({ x: 0, y: 0 });
    setFalhou(false);
  }, [pagina, item.id]);

  // lembra a rotação escolhida para cada folha (por aparelho)
  useEffect(() => {
    let r = 0;
    try {
      r = Number(localStorage.getItem('rot:' + atual.img)) || 0;
    } catch {
      /* sem armazenamento */
    }
    setRotacao(r);
  }, [atual.img]);

  function girar() {
    const nova = (rotacao + 90) % 360;
    setRotacao(nova);
    setZoom(1);
    setDesloc({ x: 0, y: 0 });
    try {
      localStorage.setItem('rot:' + atual.img, String(nova));
    } catch {
      /* sem armazenamento */
    }
  }

  useEffect(() => {
    const el = area.current;
    if (!el) return;
    const medir = () => setAreaTam({ w: el.clientWidth, h: el.clientHeight });
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    window.addEventListener('orientationchange', medir);
    return () => {
      ro.disconnect();
      window.removeEventListener('orientationchange', medir);
    };
  }, []);

  // tela sempre acesa enquanto a música está aberta
  useEffect(() => {
    let trava: { release: () => Promise<void> } | null = null;
    let ativo = true;
    const pedir = async () => {
      try {
        const wl = (navigator as unknown as { wakeLock?: { request: (t: 'screen') => Promise<{ release: () => Promise<void> }> } }).wakeLock;
        if (wl && document.visibilityState === 'visible') {
          const nova = await wl.request('screen');
          if (ativo) trava = nova;
          else nova.release().catch(() => {});
        }
      } catch {
        /* sem suporte: a tela pode apagar */
      }
    };
    pedir();
    const aoVoltar = () => {
      if (document.visibilityState === 'visible') pedir();
    };
    document.addEventListener('visibilitychange', aoVoltar);
    return () => {
      ativo = false;
      document.removeEventListener('visibilitychange', aoVoltar);
      trava?.release().catch(() => {});
    };
  }, []);

  // deixa as próximas folhas prontas para a virada de página ser instantânea
  useEffect(() => {
    const prontas: HTMLImageElement[] = [];
    const alvos = [paginas[pagina + 1]?.img, paginas[pagina - 1]?.img, proximo?.paginas[0]?.img, anterior?.paginas[0]?.img];
    for (const src of alvos) {
      if (!src) continue;
      const im = new Image();
      im.src = src;
      prontas.push(im);
    }
    return () => {
      prontas.length = 0;
    };
  }, [pagina, item.id, paginas, proximo, anterior]);

  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => {
      const alvo = e.target as HTMLElement | null;
      if (alvo && /^(INPUT|TEXTAREA|BUTTON|A)$/.test(alvo.tagName) && (e.key === ' ' || e.key === 'Enter')) return;
      if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault();
        proxima();
      } else if (e.key === 'ArrowLeft' || e.key === 'PageUp' || e.key === 'ArrowUp') {
        e.preventDefault();
        anteriorPagina();
      } else if (e.key === 'Escape') navigate(`/${secao.id}`);
      else if (e.key === '+' || e.key === '=') definirZoom(zoom + 0.5);
      else if (e.key === '-') definirZoom(zoom - 0.5);
      else if (e.key === 'r' || e.key === 'R') girar();
    };
    window.addEventListener('keydown', aoTeclar);
    return () => window.removeEventListener('keydown', aoTeclar);
  });

  // zoom com a roda do mouse / pinça no trackpad do notebook
  useEffect(() => {
    const el = area.current;
    if (!el) return;
    const aoRolar = (e: WheelEvent) => {
      e.preventDefault();
      if (e.ctrlKey || e.metaKey) {
        definirZoom(zoom * Math.exp(-e.deltaY * 0.01));
      } else if (zoom > 1) {
        setDesloc((d) => limitar(d.x - e.deltaX, d.y - e.deltaY, zoom));
      }
    };
    el.addEventListener('wheel', aoRolar, { passive: false });
    return () => el.removeEventListener('wheel', aoRolar);
  });

  function proxima() {
    if (pagina < paginas.length - 1) setPagina(pagina + 1);
    else if (proximo) navigate(`/${secao.id}/${proximo.id}`);
  }

  function anteriorPagina() {
    if (pagina > 0) setPagina(pagina - 1);
    else if (anterior) navigate(`/${secao.id}/${anterior.id}`);
  }

  function tocar(x: number, alvo?: Element | null) {
    if (alvo?.closest('button')) return;
    if (zoom > 1) return;
    const r = area.current?.getBoundingClientRect();
    const meio = (r?.left ?? 0) + (r?.width ?? window.innerWidth) / 2;
    if (x > meio) proxima();
    else anteriorPagina();
  }

  function aoPressionar(e: React.PointerEvent) {
    if ((e.target as Element).closest('button')) return;
    (e.target as Element).setPointerCapture?.(e.pointerId);
    ponteiros.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const pts = [...ponteiros.current.values()];
    if (pts.length === 2) {
      const d = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      gesto.current = { ...gesto.current, distancia: d, zoom, pan: false };
    } else if (pts.length === 1) {
      gesto.current = {
        ...gesto.current, x: e.clientX, y: e.clientY, dx: desloc.x, dy: desloc.y, pan: zoom > 1,
        x0: e.clientX, y0: e.clientY, t0: Date.now(), distancia: 0,
      };
    }
  }

  function aoMover(e: React.PointerEvent) {
    if (!ponteiros.current.has(e.pointerId)) return;
    ponteiros.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const pts = [...ponteiros.current.values()];
    if (pts.length === 2 && gesto.current.distancia > 0) {
      const d = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      definirZoom((gesto.current.zoom * d) / gesto.current.distancia);
    } else if (pts.length === 1 && gesto.current.pan) {
      setDesloc(limitar(gesto.current.dx + (e.clientX - gesto.current.x), gesto.current.dy + (e.clientY - gesto.current.y), zoom));
    }
  }

  function aoSoltar(e: React.PointerEvent) {
    const tinha = ponteiros.current.delete(e.pointerId);
    if (ponteiros.current.size === 0 && tinha) {
      const dx = e.clientX - gesto.current.x0;
      const dy = e.clientY - gesto.current.y0;
      const moveu = Math.abs(dx) > 12 || Math.abs(dy) > 12;
      const usouDoisDedos = gesto.current.distancia > 0;
      if (zoom === 1 && !usouDoisDedos) {
        if (!moveu) tocar(e.clientX, e.target as Element);
        else if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.4 && Date.now() - gesto.current.t0 < 900) {
          if (dx < 0) proxima();
          else anteriorPagina();
        }
      }
      gesto.current.distancia = 0;
    } else if (ponteiros.current.size === 1) {
      // terminou a pinça: segue arrastando com o dedo que ficou
      const [p] = [...ponteiros.current.values()];
      gesto.current = { ...gesto.current, x: p.x, y: p.y, dx: desloc.x, dy: desloc.y, pan: zoom > 1, distancia: 0 };
    }
  }

  function ciclarZoom() {
    const i = ZOOMS.findIndex((z) => Math.abs(z - zoom) < 0.05);
    definirZoom(ZOOMS[(i + 1) % ZOOMS.length]);
  }

  const tomAtual = atual.tom ?? item.tom;

  return (
    <div className="leitor">
      <header className={`barra barra-${secao.id}`}>
        <Link to={`/${secao.id}`} className="barra-voltar" aria-label="Voltar à lista">
          ‹
        </Link>
        <div className="barra-texto">
          <p>{rotuloCompleto(secao, item)}</p>
          <h1>{item.titulo}</h1>
        </div>
        <span className="barra-indice">
          {tomAtual && <em className="barra-tom">Tom: {tomAtual}</em>}
          {secao.ordem === 'numero' ? `${item.num}` : ''}
          {paginas.length > 1 && <small>{`${pagina + 1}/${paginas.length}`}</small>}
        </span>
      </header>

      <div
        className="area"
        ref={area}
        onPointerDown={aoPressionar}
        onPointerMove={aoMover}
        onPointerUp={aoSoltar}
        onPointerCancel={aoSoltar}
      >
        <img
          key={atual.img}
          src={atual.img}
          ref={imagem}
          alt={atual.alt}
          className="folha"
          draggable={false}
          onLoad={() => setFalhou(false)}
          onError={() => setFalhou(true)}
          style={{
            width: lateral && areaTam.w ? areaTam.h : undefined,
            height: lateral && areaTam.w ? areaTam.w : undefined,
            objectFit: 'contain',
            transform: `translate(-50%, -50%) translate(${desloc.x}px, ${desloc.y}px) scale(${zoom})${
              rotacao ? ` rotate(${rotacao}deg)` : ''
            }`,
            cursor: zoom > 1 ? 'grab' : 'pointer',
          }}
        />
        {falhou && (
          <div className="folha-erro" role="alert">
            <p>Esta folha ainda não foi salva neste aparelho e não há internet agora.</p>
            <button
              onClick={() => {
                setFalhou(false);
                const im = imagem.current;
                if (im) im.src = atual.img + (atual.img.includes('?') ? '&' : '?') + 'r=' + Date.now();
              }}
            >
              Tentar de novo
            </button>
          </div>
        )}
        <button className="botao-zoom" onClick={ciclarZoom} aria-label="Ampliar a folha" title="Ampliar (+ / −)">
          {zoom === 1 ? '🔍' : `${Math.round(zoom * 10) / 10}×`}
        </button>
        <button className="botao-girar" onClick={girar} aria-label="Girar a folha" title="Girar a folha (R)">
          ⟳
        </button>
        {paginas.length > 1 && (
          <>
            <button className="pagina-seta esq" onClick={anteriorPagina} aria-label="Página anterior" disabled={pagina === 0}>
              ‹
            </button>
            <button
              className="pagina-seta dir"
              onClick={proxima}
              aria-label="Próxima página"
              disabled={pagina === paginas.length - 1}
            >
              ›
            </button>
          </>
        )}
      </div>

      <nav className="navegacao">
        {anterior ? (
          <Link to={`/${secao.id}/${anterior.id}`} className="nav-item">
            <span>‹ {rotuloCompleto(secao, anterior)}</span>
            <small>{anterior.titulo}</small>
          </Link>
        ) : (
          <span className="nav-item vazio" />
        )}
        <span className="nav-pos">{paginas.length > 1 ? `${pagina + 1} / ${paginas.length}` : ''}</span>
        {proximo ? (
          <Link to={`/${secao.id}/${proximo.id}`} className="nav-item direita">
            <span>{rotuloCompleto(secao, proximo)} ›</span>
            <small>{proximo.titulo}</small>
          </Link>
        ) : (
          <span className="nav-item vazio" />
        )}
      </nav>
    </div>
  );
}
