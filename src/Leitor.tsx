import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Item, Secao, rotuloItem } from './catalogo';

type Props = {
  secao: Secao;
  item: Item;
  anterior?: Item;
  proximo?: Item;
};

export default function Leitor({ secao, item, anterior, proximo }: Props) {
  const [pagina, setPagina] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [desloc, setDesloc] = useState({ x: 0, y: 0 });
  const [girado, setGirado] = useState(false);
  const [areaTam, setAreaTam] = useState({ w: 0, h: 0 });
  const navigate = useNavigate();
  const area = useRef<HTMLDivElement>(null);
  const ponteiros = useRef(new Map<number, { x: number; y: number }>());
  const gesto = useRef({ distancia: 0, zoom: 1, x: 0, y: 0, dx: 0, dy: 0, pan: false });

  const paginas = item.paginas;
  const atual = paginas[Math.min(pagina, paginas.length - 1)];

  useEffect(() => {
    setPagina(0);
    setZoom(1);
    setDesloc({ x: 0, y: 0 });
    setGirado(false);
  }, [item.id]);

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

  useEffect(() => {
    setZoom(1);
    setDesloc({ x: 0, y: 0 });
  }, [pagina]);

  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') proxima();
      if (e.key === 'ArrowLeft') anteriorPagina();
      if (e.key === 'Escape') navigate(`/${secao.id}`);
    };
    window.addEventListener('keydown', aoTeclar);
    return () => window.removeEventListener('keydown', aoTeclar);
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
    const meio = (area.current?.clientWidth ?? window.innerWidth) / 2;
    if (zoom > 1) return;
    if (x > meio) proxima();
    else anteriorPagina();
  }

  function aoPressionar(e: React.PointerEvent) {
    (e.target as Element).setPointerCapture?.(e.pointerId);
    ponteiros.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const pts = [...ponteiros.current.values()];
    if (pts.length === 2) {
      const d = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      gesto.current = { distancia: d, zoom, x: desloc.x, y: desloc.y, dx: 0, dy: 0, pan: false };
    } else if (pts.length === 1) {
      gesto.current = { ...gesto.current, x: e.clientX, y: e.clientY, dx: desloc.x, dy: desloc.y, pan: zoom > 1 };
    }
  }

  function aoMover(e: React.PointerEvent) {
    if (!ponteiros.current.has(e.pointerId)) return;
    ponteiros.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const pts = [...ponteiros.current.values()];
    if (pts.length === 2 && gesto.current.distancia > 0) {
      const d = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      const novo = Math.min(5, Math.max(1, (gesto.current.zoom * d) / gesto.current.distancia));
      setZoom(novo);
      if (novo === 1) setDesloc({ x: 0, y: 0 });
    } else if (pts.length === 1 && gesto.current.pan) {
      setDesloc({
        x: gesto.current.dx + (e.clientX - gesto.current.x),
        y: gesto.current.dy + (e.clientY - gesto.current.y),
      });
    }
  }

  function aoSoltar(e: React.PointerEvent) {
    const tinha = ponteiros.current.delete(e.pointerId);
    if (ponteiros.current.size === 0 && tinha) {
      const dx = Math.abs(e.clientX - gesto.current.x);
      const dy = Math.abs(e.clientY - gesto.current.y);
      const moveu = dx > 12 || dy > 12;
      if (zoom === 1 && !gesto.current.pan && !moveu) tocar(e.clientX, e.target as Element);
      gesto.current.distancia = 0;
    }
  }

  function alternarZoom(e: React.MouseEvent) {
    if (e.detail === 0) return;
    setZoom((z) => (z > 1 ? 1 : 2));
    setDesloc({ x: 0, y: 0 });
  }


  return (
    <div className="leitor">
      <header className={`barra barra-${secao.id}`}>
        <Link to={`/${secao.id}`} className="barra-voltar" aria-label="Voltar à lista">
          ‹
        </Link>
        <div className="barra-texto">
          <p>{rotuloItem(secao, item)}</p>
          <h1>{item.titulo}</h1>
        </div>
        <span className="barra-indice">
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
        onDoubleClick={alternarZoom}
      >
        <img
          key={atual.img}
          src={atual.img}
          alt={atual.alt}
          className={`folha${girado ? ' folha-girada' : ''}`}
          draggable={false}
          style={{
            width: girado && areaTam.w ? areaTam.h : undefined,
            height: girado && areaTam.w ? areaTam.w : undefined,
            maxWidth: girado ? 'none' : undefined,
            maxHeight: girado ? 'none' : undefined,
            objectFit: 'contain',
            transform: `translate(${desloc.x}px, ${desloc.y}px) scale(${zoom})${
              girado ? ' rotate(90deg)' : ''
            }`,
            cursor: zoom > 1 ? 'grab' : 'pointer',
          }}
        />
        {zoom === 1 && (
          <button
            className="botao-girar"
            onPointerDown={(e) => e.stopPropagation()}
            onPointerUp={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              setGirado((v) => !v);
              setZoom(1);
              setDesloc({ x: 0, y: 0 });
            }}
            aria-label="Girar a folha"
            title={girado ? 'Ver como na foto' : 'Girar a folha'}
          >
            ⟳
          </button>
        )}
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
            <span>‹ {rotuloItem(secao, anterior)}</span>
            <small>{anterior.titulo}</small>
          </Link>
        ) : (
          <span className="nav-item vazio" />
        )}
        <span className="nav-pos">{paginas.length > 1 ? `${pagina + 1} / ${paginas.length}` : ''}</span>
        {proximo ? (
          <Link to={`/${secao.id}/${proximo.id}`} className="nav-item direita">
            <span>{rotuloItem(secao, proximo)} ›</span>
            <small>{proximo.titulo}</small>
          </Link>
        ) : (
          <span className="nav-item vazio" />
        )}
      </nav>
    </div>
  );
}
