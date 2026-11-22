import { useEffect, useRef, useState } from 'react';
import { Pagina } from './catalogo';

type Props = {
  titulo: string;
  paginas: Pagina[];
  personalizada: boolean;
  onSalvar: (ordem: string[]) => void;
  onRestaurar: () => void;
  onFechar: () => void;
};

/** Arrastar as folhas de uma música para a ordem que a pessoa quiser (fica guardado neste aparelho). */
export default function Reordenar({ titulo, paginas, personalizada, onSalvar, onRestaurar, onFechar }: Props) {
  const [lista, setLista] = useState<Pagina[]>(paginas);
  const [arrasto, setArrasto] = useState<{ img: string; x: number; y: number; dx: number; dy: number; w: number; h: number } | null>(null);
  const cartas = useRef(new Map<string, HTMLDivElement>());
  const alterado = lista.some((p, i) => p.img !== paginas[i]?.img);

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && onFechar();
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [onFechar]);

  function mover(de: number, para: number) {
    if (para < 0 || para >= lista.length || de === para) return;
    const nova = [...lista];
    const [x] = nova.splice(de, 1);
    nova.splice(para, 0, x);
    setLista(nova);
  }

  function aoPressionar(e: React.PointerEvent<HTMLDivElement>, p: Pagina) {
    if ((e.target as HTMLElement).closest('button')) return;
    const el = cartas.current.get(p.img);
    if (!el) return;
    const r = el.getBoundingClientRect();
    (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
    setArrasto({ img: p.img, x: e.clientX, y: e.clientY, dx: e.clientX - r.left, dy: e.clientY - r.top, w: r.width, h: r.height });
  }

  function aoMover(e: React.PointerEvent<HTMLDivElement>) {
    if (!arrasto) return;
    setArrasto({ ...arrasto, x: e.clientX, y: e.clientY });
    // carta mais próxima do dedo / caneta
    let melhor = -1;
    let dist = Infinity;
    lista.forEach((p, i) => {
      const el = cartas.current.get(p.img);
      if (!el) return;
      const r = el.getBoundingClientRect();
      const d = Math.hypot(e.clientX - (r.left + r.width / 2), e.clientY - (r.top + r.height / 2));
      if (d < dist) {
        dist = d;
        melhor = i;
      }
    });
    const atual = lista.findIndex((p) => p.img === arrasto.img);
    if (melhor >= 0 && melhor !== atual) mover(atual, melhor);
  }

  function aoSoltar() {
    setArrasto(null);
  }

  const doArrasto = arrasto ? lista.find((p) => p.img === arrasto.img) : undefined;

  return (
    <div className="ordem" role="dialog" aria-label="Reordenar as folhas">
      <header className="ordem-topo">
        <button className="anot-btn" onClick={onFechar} aria-label="Fechar">
          ✕
        </button>
        <div>
          <strong>Reordenar folhas</strong>
          <small>{titulo}</small>
        </div>
        <button className={`anot-btn anot-salvar${alterado ? ' pendente' : ''}`} onClick={() => onSalvar(lista.map((p) => p.img))} disabled={!alterado}>
          {alterado ? 'Salvar ordem' : 'Sem mudanças'}
        </button>
      </header>
      <p className="ordem-dica">Segure e arraste cada folha para o lugar que quiser. Ou use as setas ◀ ▶. A nova ordem fica guardada neste aparelho.</p>
      <div className="ordem-grade" onPointerMove={aoMover} onPointerUp={aoSoltar} onPointerCancel={aoSoltar}>
        {lista.map((p, i) => (
          <div
            key={p.img}
            ref={(el) => {
              if (el) cartas.current.set(p.img, el);
            }}
            className={`ordem-carta${arrasto?.img === p.img ? ' levantada' : ''}`}
            onPointerDown={(e) => aoPressionar(e, p)}
          >
            <span className="ordem-num">{i + 1}</span>
            <img src={p.img} alt={`Folha ${i + 1}`} draggable={false} />
            <div className="ordem-setas">
              <button onClick={() => mover(i, i - 1)} disabled={i === 0} aria-label={`Mover a folha ${i + 1} para antes`}>
                ◀
              </button>
              <button onClick={() => mover(i, i + 1)} disabled={i === lista.length - 1} aria-label={`Mover a folha ${i + 1} para depois`}>
                ▶
              </button>
            </div>
          </div>
        ))}
      </div>
      {arrasto && doArrasto && (
        <div className="ordem-fantasma" style={{ left: arrasto.x - arrasto.dx, top: arrasto.y - arrasto.dy, width: arrasto.w, height: arrasto.h }}>
          <img src={doArrasto.img} alt="" />
        </div>
      )}
      {personalizada && (
        <button className="ordem-restaurar" onClick={onRestaurar}>
          Voltar à ordem original
        </button>
      )}
    </div>
  );
}
