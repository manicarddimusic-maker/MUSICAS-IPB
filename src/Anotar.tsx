import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Base,
  FolhaDef,
  Ferramenta,
  FundoBranco,
  Traco,
  achatar,
  desenharTraco,
  pintarBase,
  prepararBase,
} from './anotacoes';

type Props = {
  titulo: string;
  folhas: FolhaDef[];
  inicial?: number;
  rascunho?: boolean;
  onSalvar: (folhas: FolhaDef[], titulo: string) => Promise<void>;
  onDuplicar?: (folhas: FolhaDef[], titulo: string) => Promise<void>;
  onRemoverTudo?: () => Promise<void>;
  onFechar: () => void;
};

const CORES = ['#111111', '#d32f2f', '#1565c0', '#2e7d32', '#ef6c00', '#6a1b9a'];
const MARCAS = ['#ffe94d', '#9be39b', '#7fc8ff', '#ff9ec7', '#ffb766'];

const FERR: { id: Ferramenta; rotulo: string; icone: string; dica: string }[] = [
  { id: 'caneta', rotulo: 'Caneta', icone: '✎', dica: 'Escrever à mão (Apple Pencil)' },
  { id: 'marca', rotulo: 'Marca-texto', icone: '🖍', dica: 'Destacar' },
  { id: 'corretivo', rotulo: 'Corretivo', icone: '▭', dica: 'Cobrir algo que está impresso na folha' },
  { id: 'borracha', rotulo: 'Borracha', icone: '⌫', dica: 'Apagar traços e textos' },
  { id: 'texto', rotulo: 'Texto', icone: 'T', dica: 'Digitar (cifras, notas)' },
];

function largura(f: Ferramenta, k: number) {
  switch (f) {
    case 'caneta':
      return 0.0007 * k;
    case 'marca':
      return 0.006 * k;
    case 'corretivo':
      return 0.007 * k;
    case 'borracha':
      return 0.008 * k;
    default:
      return 0.010 + 0.0035 * k; // tamanho do texto
  }
}

function copiar(f: FolhaDef[]): FolhaDef[] {
  return f.map((x) => ({ ...x, tracos: [...x.tracos] }));
}

function distSeg(px: number, py: number, ax: number, ay: number, bx: number, by: number) {
  const dx = bx - ax;
  const dy = by - ay;
  const l = dx * dx + dy * dy;
  const t = l ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l)) : 0;
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

function atinge(t: Traco, x: number, y: number, r: number, W: number, H: number): boolean {
  if (t.t === 'texto') {
    const linhas = t.txt.split('\n');
    const larg = Math.max(...linhas.map((l) => l.length)) * t.s * 0.62;
    const alt = linhas.length * t.s * 1.2;
    return x >= t.x - r && x <= t.x + larg + r && y >= t.y - r && y <= t.y + alt + r;
  }
  const lim = r + t.w / 2;
  if (t.p.length === 1) return Math.hypot(x - t.p[0][0], y - t.p[0][1]) <= lim;
  for (let i = 1; i < t.p.length; i++) {
    if (distSeg(x, y, t.p[i - 1][0], t.p[i - 1][1], t.p[i][0], t.p[i][1]) <= lim) return true;
  }
  void W;
  void H;
  return false;
}

export default function Anotar({ titulo, folhas, inicial = 0, rascunho, onSalvar, onDuplicar, onRemoverTudo, onFechar }: Props) {
  const [fol, setFol] = useState<FolhaDef[]>(() => copiar(folhas));
  const [pi, setPi] = useState(Math.min(inicial, folhas.length - 1));
  const [ferr, setFerr] = useState<Ferramenta>('caneta');
  const [cor, setCor] = useState(CORES[0]);
  const [corMarca, setCorMarca] = useState(MARCAS[0]);
  const [tam, setTam] = useState<Record<Ferramenta, number>>({ caneta: 3, marca: 3, corretivo: 4, borracha: 3, texto: 3 });
  const [dedo, setDedo] = useState(() => window.innerWidth < 700);
  const [sujo, setSujo] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [menu, setMenu] = useState(false);
  const [nome, setNome] = useState(titulo);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [editTexto, setEditTexto] = useState<{ x: number; y: number } | null>(null);
  const [zv, setZv] = useState(1);

  const rolagem = useRef<HTMLDivElement>(null);
  const caixa = useRef<HTMLDivElement>(null);
  const tela = useRef<HTMLCanvasElement>(null);
  const base = useRef<Base | null>(null);
  const folRef = useRef(fol);
  folRef.current = fol;
  const piRef = useRef(pi);
  piRef.current = pi;
  const ao_vivo = useRef<Traco | null>(null);
  const zoom = useRef(1);
  const encaixe = useRef(0);
  const hist = useRef<{ pi: number; tracos: Traco[] }[]>([]);
  const refazer = useRef<{ pi: number; tracos: Traco[] }[]>([]);
  const toques = useRef(new Map<number, { x: number; y: number }>());
  const pinca = useRef<{ d: number; cx: number; cy: number } | null>(null);
  const caneta_ativa = useRef(false);
  const caneta_fim = useRef(0);
  const apagou = useRef(false);
  const textoPend = useRef<{ x: number; y: number } | null>(null);
  const rodandoRaf = useRef(0);

  const estado = useRef({ ferr, cor, corMarca, tam, dedo });
  estado.current = { ferr, cor, corMarca, tam, dedo };

  /* ----- tela ----- */
  const pintarTela = useCallback(() => {
    const c = tela.current;
    const b = base.current;
    if (!c || !b) return;
    const ctx = c.getContext('2d')!;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.drawImage(b.canvas, 0, 0);
    if (ao_vivo.current) desenharTraco(ctx, ao_vivo.current, b.W, b.papel);
  }, []);

  const agendar = useCallback(() => {
    if (rodandoRaf.current) return;
    rodandoRaf.current = requestAnimationFrame(() => {
      rodandoRaf.current = 0;
      pintarTela();
    });
  }, [pintarTela]);

  const reconstruir = useCallback(() => {
    const b = base.current;
    if (!b) return;
    pintarBase(b, folRef.current[piRef.current], folRef.current[piRef.current].tracos);
    pintarTela();
  }, [pintarTela]);

  const aplicarLargura = useCallback((z: number) => {
    const b = base.current;
    const r = rolagem.current;
    const cx = tela.current;
    if (!b || !r || !cx) return;
    const ajuste = Math.min((r.clientWidth - 16) , ((r.clientHeight - 16) * b.W) / b.H);
    encaixe.current = ajuste;
    zoom.current = Math.max(0.4, Math.min(6, z));
    setZv(zoom.current);
    if (caixa.current) caixa.current.style.width = `${Math.round(ajuste * zoom.current)}px`;
    void cx;
  }, []);

  const zoomEm = useCallback(
    (z: number, cxp?: number, cyp?: number) => {
      const r = rolagem.current;
      const cv = tela.current;
      if (!r || !cv) return;
      const rr = r.getBoundingClientRect();
      const px = cxp ?? rr.left + rr.width / 2;
      const py = cyp ?? rr.top + rr.height / 2;
      const r0 = cv.getBoundingClientRect();
      const fx = (px - r0.left) / r0.width;
      const fy = (py - r0.top) / r0.height;
      aplicarLargura(z);
      const r1 = cv.getBoundingClientRect();
      r.scrollLeft += r1.left + fx * r1.width - px;
      r.scrollTop += r1.top + fy * r1.height - py;
    },
    [aplicarLargura],
  );

  useEffect(() => {
    let vivo = true;
    setCarregando(true);
    setErro(null);
    setEditTexto(null);
    prepararBase(folRef.current[pi])
      .then((b) => {
        if (!vivo) return;
        base.current = b;
        const c = tela.current;
        if (c) {
          c.width = b.W;
          c.height = b.H;
        }
        pintarBase(b, folRef.current[pi], folRef.current[pi].tracos);
        aplicarLargura(1);
        pintarTela();
        if (rolagem.current) {
          rolagem.current.scrollLeft = 0;
          rolagem.current.scrollTop = 0;
        }
        setCarregando(false);
      })
      .catch((e: Error) => {
        if (vivo) {
          setErro(e.message);
          setCarregando(false);
        }
      });
    return () => {
      vivo = false;
    };
  }, [pi, aplicarLargura, pintarTela]);

  useEffect(() => {
    const aoRedimensionar = () => aplicarLargura(zoom.current);
    window.addEventListener('resize', aoRedimensionar);
    return () => window.removeEventListener('resize', aoRedimensionar);
  }, [aplicarLargura]);

  /* ----- histórico ----- */
  function guardarHistorico() {
    hist.current.push({ pi: piRef.current, tracos: folRef.current[piRef.current].tracos });
    if (hist.current.length > 200) hist.current.shift();
    refazer.current = [];
  }

  function trocarTracos(p: number, tracos: Traco[]) {
    const novo = copiar(folRef.current);
    novo[p] = { ...novo[p], tracos };
    folRef.current = novo;
    setFol(novo);
    setSujo(true);
  }

  function desfazer() {
    const h = hist.current.pop();
    if (!h) return;
    refazer.current.push({ pi: h.pi, tracos: folRef.current[h.pi].tracos });
    trocarTracos(h.pi, h.tracos);
    if (h.pi !== piRef.current) setPi(h.pi);
    else reconstruir();
  }

  function refazerAcao() {
    const h = refazer.current.pop();
    if (!h) return;
    hist.current.push({ pi: h.pi, tracos: folRef.current[h.pi].tracos });
    trocarTracos(h.pi, h.tracos);
    if (h.pi !== piRef.current) setPi(h.pi);
    else reconstruir();
  }

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        if (e.shiftKey) refazerAcao();
        else desfazer();
      }
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  });

  /* ----- ponteiro ----- */
  function ponto(e: React.PointerEvent | PointerEvent) {
    const cv = tela.current!;
    const r = cv.getBoundingClientRect();
    const pr = e.pointerType === 'pen' ? e.pressure || 0.5 : 0.5;
    return [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.width, pr] as [number, number, number];
  }

  function apagarEm(x: number, y: number) {
    const b = base.current;
    if (!b) return;
    const raio = largura('borracha', estado.current.tam.borracha);
    const atuais = folRef.current[piRef.current].tracos;
    const restantes = atuais.filter((t) => !atinge(t, x, y, raio, b.W, b.H));
    if (restantes.length === atuais.length) return;
    if (!apagou.current) {
      guardarHistorico();
      apagou.current = true;
    }
    trocarTracos(piRef.current, restantes);
    reconstruir();
  }

  function aoPressionar(e: React.PointerEvent<HTMLCanvasElement>) {
    if (carregando || erro) return;
    if (e.pointerType === 'pen') caneta_ativa.current = true;
    if (e.pointerType === 'touch') {
      if (caneta_ativa.current || performance.now() - caneta_fim.current < 400) return; // descanso da palma
      toques.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (toques.current.size >= 2) {
        ao_vivo.current = null;
        pintarTela();
        const [a, b] = [...toques.current.values()];
        pinca.current = { d: Math.hypot(a.x - b.x, a.y - b.y), cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2 };
        return;
      }
      if (!estado.current.dedo) return;
    }
    try {
      (e.currentTarget as HTMLCanvasElement).setPointerCapture(e.pointerId);
    } catch {
      /* sem captura: segue desenhando normalmente */
    }
    const p = ponto(e);
    const { ferr: f, cor: c, corMarca: cm, tam: t } = estado.current;
    if (f === 'texto') {
      textoPend.current = { x: p[0], y: p[1] };
      return;
    }
    apagou.current = false;
    if (f === 'borracha') {
      apagarEm(p[0], p[1]);
      ao_vivo.current = null;
      return;
    }
    ao_vivo.current = { t: f, c: f === 'marca' ? cm : f === 'corretivo' ? '#ffffff' : c, w: largura(f, t[f]), p: [p] };
    agendar();
  }

  function aoMover(e: React.PointerEvent<HTMLCanvasElement>) {
    if (e.pointerType === 'touch') {
      const ant = toques.current.get(e.pointerId);
      if (!ant) return;
      toques.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (toques.current.size >= 2 && pinca.current) {
        const [a, b] = [...toques.current.values()];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        const cx = (a.x + b.x) / 2;
        const cy = (a.y + b.y) / 2;
        if (pinca.current.d > 0) zoomEm(zoom.current * (d / pinca.current.d), cx, cy);
        if (rolagem.current) {
          rolagem.current.scrollLeft -= cx - pinca.current.cx;
          rolagem.current.scrollTop -= cy - pinca.current.cy;
        }
        pinca.current = { d, cx, cy };
        return;
      }
      if (!estado.current.dedo && rolagem.current) {
        rolagem.current.scrollLeft -= e.clientX - ant.x;
        rolagem.current.scrollTop -= e.clientY - ant.y;
        return;
      }
    }
    const f = estado.current.ferr;
    if (f === 'borracha') {
      if (e.buttons || e.pointerType !== 'mouse') {
        const evs = (e.nativeEvent as PointerEvent).getCoalescedEvents?.() ?? [e.nativeEvent as PointerEvent];
        for (const ev of evs.length ? evs : [e.nativeEvent as PointerEvent]) {
          const p = ponto(ev);
          if (e.buttons || ev.pointerType !== 'mouse') apagarEm(p[0], p[1]);
        }
      }
      return;
    }
    const v = ao_vivo.current;
    if (!v || v.t === 'texto') return;
    const evs = (e.nativeEvent as PointerEvent).getCoalescedEvents?.() ?? [];
    for (const ev of evs.length ? evs : [e.nativeEvent as PointerEvent]) {
      const p = ponto(ev);
      const u = v.p[v.p.length - 1];
      if (Math.hypot(p[0] - u[0], p[1] - u[1]) > 0.0004) v.p.push(p);
    }
    agendar();
  }

  function aoSoltar(e: React.PointerEvent<HTMLCanvasElement>) {
    if (e.pointerType === 'pen') {
      caneta_ativa.current = false;
      caneta_fim.current = performance.now();
    }
    if (e.pointerType === 'touch') {
      toques.current.delete(e.pointerId);
      if (toques.current.size < 2) pinca.current = null;
    }
    apagou.current = false;
    if (textoPend.current && estado.current.ferr === 'texto') {
      const tp = textoPend.current;
      textoPend.current = null;
      setEditTexto(tp);
      return;
    }
    const v = ao_vivo.current;
    if (!v || v.t === 'texto') return;
    ao_vivo.current = null;
    guardarHistorico();
    const tracos = [...folRef.current[piRef.current].tracos, v];
    trocarTracos(piRef.current, tracos);
    const b = base.current;
    if (b) {
      desenharTraco(b.canvas.getContext('2d')!, v, b.W, b.papel);
      pintarTela();
    }
  }

  /* ----- texto ----- */
  function confirmarTexto(valor: string) {
    const ed = editTexto;
    setEditTexto(null);
    const txt = valor.replace(/\s+$/g, '');
    if (!ed || !txt) return;
    guardarHistorico();
    const s = largura('texto', estado.current.tam.texto);
    const t: Traco = { t: 'texto', c: estado.current.cor, s, x: ed.x, y: ed.y - s * 0.6, txt };
    trocarTracos(piRef.current, [...folRef.current[piRef.current].tracos, t]);
    reconstruir();
  }

  /* ----- ações ----- */
  async function salvar() {
    try {
      setMsg('Salvando…');
      await onSalvar(folRef.current, nome);
      setSujo(false);
      setMsg('Salvo ✓');
    } catch (e) {
      setMsg((e as Error).message || 'Não foi possível salvar.');
    }
    window.setTimeout(() => setMsg(null), 2400);
  }

  async function duplicar() {
    if (!onDuplicar) return;
    setMenu(false);
    try {
      setMsg('Criando cópia…');
      await onDuplicar(folRef.current, nome);
      setMsg('Cópia criada em “Rascunhos” ✓');
    } catch (e) {
      setMsg((e as Error).message || 'Não foi possível duplicar.');
    }
    window.setTimeout(() => setMsg(null), 2800);
  }

  async function exportar() {
    setMenu(false);
    try {
      setMsg('Gerando imagem…');
      const blob = await achatar(folRef.current[piRef.current], folRef.current[piRef.current].tracos);
      const arq = new File([blob], `${nome.replace(/[^\w\-]+/g, '_') || 'folha'}-${piRef.current + 1}.jpg`, { type: 'image/jpeg' });
      const nav = navigator as Navigator & { canShare?: (d: ShareData) => boolean };
      if (nav.canShare?.({ files: [arq] })) {
        await navigator.share({ files: [arq], title: nome });
      } else {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = arq.name;
        a.click();
        window.setTimeout(() => URL.revokeObjectURL(a.href), 4000);
      }
      setMsg(null);
    } catch (e) {
      if ((e as Error).name !== 'AbortError') setMsg((e as Error).message || 'Não foi possível exportar.');
      else setMsg(null);
    }
  }

  async function limparTudo() {
    setMenu(false);
    if (!window.confirm('Apagar TODAS as anotações destas folhas? (A foto original continua igual.)')) return;
    const novo = copiar(folRef.current).map((f) => ({ ...f, tracos: [] }));
    guardarHistorico();
    folRef.current = novo;
    setFol(novo);
    setSujo(true);
    reconstruir();
    try {
      await onRemoverTudo?.();
      setSujo(false);
    } catch {
      /* continua editável */
    }
  }

  function novaFolha(fundo: FundoBranco) {
    setMenu(false);
    const novo = [...copiar(folRef.current), { branco: { w: 1600, h: 2200, fundo }, tracos: [] }];
    folRef.current = novo;
    setFol(novo);
    setSujo(true);
    setPi(novo.length - 1);
  }

  function fechar() {
    if (sujo && !window.confirm('Há alterações que não foram salvas. Sair mesmo assim?')) return;
    onFechar();
  }

  const podeDesfazer = hist.current.length > 0;
  const podeRefazer = refazer.current.length > 0;
  const paleta = ferr === 'marca' ? MARCAS : CORES;
  const corAtiva = ferr === 'marca' ? corMarca : cor;
  const usaCor = ferr === 'caneta' || ferr === 'marca' || ferr === 'texto';

  const lado = base.current ? encaixe.current * zoom.current : 0;
  const sTxt = largura('texto', tam.texto);

  return (
    <div className="anot" role="dialog" aria-label="Anotar a folha">
      <header className="anot-topo">
        <button className="anot-btn" onClick={fechar} aria-label="Fechar o modo de anotação" title="Fechar">
          ✕
        </button>
        {rascunho ? (
          <input className="anot-nome" value={nome} onChange={(e) => { setNome(e.target.value); setSujo(true); }} aria-label="Nome do rascunho" />
        ) : (
          <strong className="anot-titulo">{nome}</strong>
        )}
        <div className="anot-grupo">
          <button className="anot-btn" onClick={desfazer} disabled={!podeDesfazer} aria-label="Desfazer" title="Desfazer (Ctrl+Z)">
            ↶
          </button>
          <button className="anot-btn" onClick={refazerAcao} disabled={!podeRefazer} aria-label="Refazer" title="Refazer">
            ↷
          </button>
        </div>
        <div className="anot-grupo">
          <button className="anot-btn" onClick={() => zoomEm(zoom.current / 1.25)} aria-label="Diminuir" title="Diminuir">
            −
          </button>
          <button className="anot-btn" onClick={() => zoomEm(1)} aria-label="Ajustar à tela" title="Ajustar à tela">
            {Math.round(zv * 100)}%
          </button>
          <button className="anot-btn" onClick={() => zoomEm(zoom.current * 1.25)} aria-label="Ampliar" title="Ampliar">
            +
          </button>
        </div>
        <button className={`anot-btn anot-salvar${sujo ? ' pendente' : ''}`} onClick={salvar} title="Salvar neste aparelho">
          {sujo ? 'Salvar' : 'Salvo ✓'}
        </button>
        <div className="anot-mais">
          <button className="anot-btn" onClick={() => setMenu((m) => !m)} aria-label="Mais opções" aria-expanded={menu}>
            ⋯
          </button>
          {menu && (
            <div className="anot-menu" role="menu">
              {onDuplicar && <button onClick={duplicar}>⧉ Duplicar como rascunho</button>}
              <button onClick={exportar}>⇪ Exportar esta folha (imagem)</button>
              {rascunho && (
                <>
                  <button onClick={() => novaFolha('branca')}>＋ Nova folha em branco</button>
                  <button onClick={() => novaFolha('linhas')}>＋ Nova folha pautada (linhas)</button>
                  <button onClick={() => novaFolha('pauta')}>＋ Nova folha de partitura</button>
                </>
              )}
              <button onClick={limparTudo}>🗑 Apagar todas as anotações</button>
            </div>
          )}
        </div>
      </header>

      <div className="anot-ferr">
        {FERR.map((f) => (
          <button key={f.id} className={`anot-ferr-btn${ferr === f.id ? ' ativo' : ''}`} onClick={() => setFerr(f.id)} title={f.dica} aria-pressed={ferr === f.id}>
            <span aria-hidden="true">{f.icone}</span>
            <small>{f.rotulo}</small>
          </button>
        ))}
        {usaCor && (
          <div className="anot-cores" role="group" aria-label="Cor">
            {paleta.map((c) => (
              <button key={c} className={`anot-cor${corAtiva === c ? ' ativa' : ''}`} style={{ background: c }} onClick={() => (ferr === 'marca' ? setCorMarca(c) : setCor(c))} aria-label={`Cor ${c}`} />
            ))}
          </div>
        )}
        <label className="anot-tam">
          <small>{ferr === 'texto' ? 'Tamanho' : ferr === 'borracha' ? 'Raio' : 'Espessura'}</small>
          <input type="range" min={1} max={10} value={tam[ferr]} onChange={(e) => setTam({ ...tam, [ferr]: Number(e.target.value) })} />
        </label>
        <button className={`anot-ferr-btn${dedo ? ' ativo' : ''}`} onClick={() => setDedo(!dedo)} aria-pressed={dedo} title="Quando ligado, o dedo também desenha. Desligado: só a Apple Pencil desenha e o dedo move/amplia a folha.">
          <span aria-hidden="true">☝</span>
          <small>{dedo ? 'Dedo desenha' : 'Só caneta'}</small>
        </button>
      </div>

      <div className="anot-rolagem" ref={rolagem}>
        <div className="anot-caixa" ref={caixa} style={{ width: lado || undefined }}>
          <canvas
            ref={tela}
            className={`anot-tela ferr-${ferr}`}
            onPointerDown={aoPressionar}
            onPointerMove={aoMover}
            onPointerUp={aoSoltar}
            onPointerCancel={aoSoltar}
            onContextMenu={(e) => e.preventDefault()}
          />
          {editTexto && lado > 0 && (
            <textarea
              key={`${editTexto.x}-${editTexto.y}`}
              className="anot-texto"
              autoFocus
              rows={1}
              style={{ left: editTexto.x * lado, top: editTexto.y * lado - sTxt * lado * 0.6, fontSize: sTxt * lado, color: cor }}
              placeholder="Digite…"
              onBlur={(e) => confirmarTexto(e.currentTarget.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') setEditTexto(null);
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  (e.currentTarget as HTMLTextAreaElement).blur();
                }
              }}
            />
          )}
        </div>
        {carregando && <p className="anot-aviso">Abrindo a folha…</p>}
        {erro && <p className="anot-aviso erro">{erro}</p>}
      </div>

      <footer className="anot-pe">
        {fol.length > 1 ? (
          <>
            <button className="anot-btn" onClick={() => setPi(Math.max(0, pi - 1))} disabled={pi === 0} aria-label="Folha anterior">
              ‹
            </button>
            <span>
              Folha {pi + 1} de {fol.length}
            </span>
            <button className="anot-btn" onClick={() => setPi(Math.min(fol.length - 1, pi + 1))} disabled={pi === fol.length - 1} aria-label="Próxima folha">
              ›
            </button>
          </>
        ) : (
          <span>{rascunho ? 'Rascunho' : 'Anotações ficam guardadas só neste aparelho'}</span>
        )}
        {msg && <em className="anot-msg" role="status">{msg}</em>}
      </footer>
    </div>
  );
}
