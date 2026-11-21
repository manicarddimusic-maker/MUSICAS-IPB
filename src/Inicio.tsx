import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Catalogo, ordenarItens } from './catalogo';
import { caminho, ARTEFATO } from './ambiente';
import { folhasSalvas, salvarTudo, urlsDeFolhas } from './offline';

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
  const urls = useMemo(() => urlsDeFolhas(catalogo), [catalogo]);
  const [salvas, setSalvas] = useState<number | null>(null);
  const [baixando, setBaixando] = useState<{ feitas: number; total: number; falhas: number } | null>(null);
  const [msgOffline, setMsgOffline] = useState<string | null>(null);
  const cancelar = useRef(false);

  useEffect(() => {
    if (ARTEFATO) return;
    folhasSalvas(urls)
      .then((s) => setSalvas(s.size))
      .catch(() => setSalvas(null));
  }, [urls]);

  async function baixar() {
    cancelar.current = false;
    setMsgOffline(null);
    setBaixando({ feitas: salvas ?? 0, total: urls.length, falhas: 0 });
    try {
      const { falhas } = await salvarTudo(urls, (feitas, total, f) => setBaixando({ feitas, total, falhas: f }), () => cancelar.current);
      const s = await folhasSalvas(urls);
      setSalvas(s.size);
      if (cancelar.current) setMsgOffline('Download pausado. Toque de novo para continuar de onde parou.');
      else if (falhas > 0) setMsgOffline(`${falhas} folhas não baixaram (internet instável). Toque de novo para completar.`);
    } catch {
      setMsgOffline('Não foi possível baixar agora. Confira a internet e tente de novo.');
    } finally {
      setBaixando(null);
    }
  }

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
          <img className="logo-app" src={caminho('/icons/icone-192.png')} alt="" width={68} height={68} />
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

      {!ARTEFATO && salvas !== null && (
        <section className="offline">
          {salvas >= urls.length && !baixando ? (
            <p className="offline-ok">✓ Tudo salvo neste aparelho — funciona sem internet ({urls.length} folhas)</p>
          ) : (
            <>
              <p className="offline-txt">
                {baixando
                  ? `Salvando para usar sem internet… ${baixando.feitas}/${baixando.total}`
                  : `Para tocar sem depender da internet, salve tudo neste aparelho (${salvas}/${urls.length} salvas).`}
              </p>
              {baixando && (
                <div className="offline-barra" aria-hidden="true">
                  <span style={{ width: `${(baixando.feitas / baixando.total) * 100}%` }} />
                </div>
              )}
              {baixando ? (
                <button className="botao-offline" onClick={() => (cancelar.current = true)}>
                  Pausar
                </button>
              ) : (
                <button className="botao-offline" onClick={baixar}>
                  Salvar tudo para usar sem internet
                </button>
              )}
            </>
          )}
          {msgOffline && <p className="offline-aviso">{msgOffline}</p>}
        </section>
      )}

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
