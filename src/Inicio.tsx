import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Catalogo, ordenarItens } from './catalogo';
import { caminho } from './ambiente';

type PromptEvento = Event & { prompt: () => Promise<void> };

const CAPAS: Record<string, string> = {
  hinos: '/midias/capas/image-1.webp',
  canticos: '/midias/capas/image-2.webp',
  salmos: '/midias/capas/image-3.webp',
  lavras: '/midias/capas/image-2.webp',
};

export default function Inicio({ catalogo }: { catalogo: Catalogo }) {
  const [instalacao, setInstalacao] = useState<PromptEvento | null>(null);
  const [instalado, setInstalado] = useState(false);

  useEffect(() => {
    const aoInstalar = (e: Event) => {
      e.preventDefault();
      setInstalacao(e as PromptEvento);
    };
    window.addEventListener('beforeinstallprompt', aoInstalar);
    if (window.matchMedia('(display-mode: standalone)').matches) setInstalado(true);
    return () => window.removeEventListener('beforeinstallprompt', aoInstalar);
  }, []);

  return (
    <div className="inicio">
      <div className="textura" aria-hidden="true" />

      <header className="capa">
        <div className="ornamento" aria-hidden="true">
          <span />
          <i>✝</i>
          <span />
        </div>
        <p className="capa-eyebrow">Hinário da Igreja</p>
        <h1>Músicas do nosso culto</h1>
        <p className="capa-sub">Hinos, cânticos espirituais, salmos e músicas Lavras</p>
      </header>

      <nav className="secoes">
        {catalogo.secoes.map((secao, i) => {
          const itens = ordenarItens(secao);
          return (
            <Link key={secao.id} to={`/${secao.id}`} className={`cartao cartao-${secao.id}`} style={{ animationDelay: `${i * 90}ms` }}>
              <img src={caminho(CAPAS[secao.id])} alt="" className="cartao-fundo" loading="eager" />
              <span className="cartao-veu" />
              <span className="cartao-conteudo">
                <span className="cartao-sub">{secao.subtitulo}</span>
                <span className="cartao-titulo">{secao.titulo}</span>
                <span className="cartao-info">
                  {itens.length === 0 ? 'Em breve' : itens.length === 1 ? '1 música' : `${itens.length} músicas`}
                  {secao.ordem === 'numero' ? ' · por número' : ' · A–Z'}
                </span>
              </span>
              <span className="cartao-seta" aria-hidden="true">
                ›
              </span>
            </Link>
          );
        })}
      </nav>

      <footer className="rodape">
        {instalacao && !instalado ? (
          <button
            className="botao-instalar"
            onClick={async () => {
              await instalacao.prompt();
              setInstalacao(null);
              setInstalado(true);
            }}
          >
            Instalar no aparelho
          </button>
        ) : (
          <p className="dica">No celular ou tablet, use “Adicionar à tela de início” para abrir como app.</p>
        )}
      </footer>
    </div>
  );
}
