import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

const LUGARES: { para: string; nome: string; icone: string }[] = [
  { para: '/', nome: 'Início', icone: '⌂' },
  { para: '/hinario', nome: 'Hinos', icone: '♪' },
  { para: '/hinos', nome: 'Hinos – Partitura', icone: '♪' },
  { para: '/hinoscifra', nome: 'Hinos – Cifra', icone: '♪' },
  { para: '/canticos', nome: 'Cânticos Espirituais', icone: '♪' },
  { para: '/caderninho', nome: 'Cânticos Antigos IPB', icone: '♪' },
  { para: '/palavra', nome: 'Palavra de Deus Cantada', icone: '✦' },
  { para: '/lavras', nome: 'Músicas Lavras', icone: '♪' },
  { para: '/lavras/arquivos-pdf', nome: 'Arquivos PDF (Lavras)', icone: '▤' },
  { para: '/rascunhos', nome: 'Meus Rascunhos', icone: '✎' },
];

/** Botão "Voltar" explícito: volta para onde a pessoa estava (ou para um lugar seguro, se não houver histórico). */
export function BotaoVoltar({ fallback = '/', rotulo = 'Voltar' }: { fallback?: string; rotulo?: string }) {
  const navigate = useNavigate();
  function voltar() {
    const idx = (window.history.state as { idx?: number } | null)?.idx;
    if (typeof idx === 'number' && idx > 0) navigate(-1);
    else navigate(fallback, { replace: true });
  }
  return (
    <button className="btn-voltar" onClick={voltar} aria-label={`${rotulo} para a tela anterior`}>
      <span aria-hidden="true">‹</span>
      <span>{rotulo}</span>
    </button>
  );
}

/** Menu "Ir para…": leva a qualquer parte do aplicativo. */
export function MenuIr() {
  const [aberto, setAberto] = useState(false);
  const local = useLocation();
  useEffect(() => setAberto(false), [local.pathname]);
  useEffect(() => {
    if (!aberto) return;
    const tecla = (e: KeyboardEvent) => e.key === 'Escape' && setAberto(false);
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [aberto]);
  return (
    <>
      <button className="btn-menu" onClick={() => setAberto(true)} aria-label="Ir para qualquer parte do aplicativo" aria-haspopup="dialog">
        <span aria-hidden="true">☰</span>
        <span>Ir para…</span>
      </button>
      {aberto && (
        <div className="menu-ir" role="dialog" aria-label="Ir para" onClick={() => setAberto(false)}>
          <nav className="menu-ir-folha" onClick={(e) => e.stopPropagation()}>
            <header>
              <strong>Ir para…</strong>
              <button className="btn-voltar" onClick={() => setAberto(false)} aria-label="Fechar o menu">
                ✕ Fechar
              </button>
            </header>
            {LUGARES.map((l) => (
              <Link key={l.para} to={l.para} className={local.pathname === l.para ? 'atual' : ''}>
                <span aria-hidden="true">{l.icone}</span>
                {l.nome}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </>
  );
}
