import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Link, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArquivoPdf, Catalogo, Secao, carregarCatalogo, livrosDaPalavra, normalizar, ordenarItens, rotaLista, rotuloItem } from './catalogo';
import { baixarBlob, gerarPdfSecao, nomeArquivoPdf } from './exportarPdf';
import { caminho } from './ambiente';
import Leitor from './Leitor';
import Inicio, { CAPAS } from './Inicio';
import Rascunhos from './Rascunhos';
import { BotaoVoltar, MenuIr } from './Navegar';
import { LeitorPdf } from './LeitorPdf';

function ehLista(caminho: string): boolean {
  const p = caminho.split('/').filter(Boolean);
  if (p.length === 1) return p[0] !== 'rascunhos';
  return p.length === 2 && p[0] === 'livro';
}

const chaveLista = (caminho: string) => `hinario-lista:${caminho}`;
function lerJson<T>(k: string): T | null {
  try {
    const v = sessionStorage.getItem(k);
    return v ? (JSON.parse(v) as T) : null;
  } catch {
    return null;
  }
}
function gravarJson(k: string, v: unknown) {
  try {
    sessionStorage.setItem(k, JSON.stringify(v));
  } catch {
    /* sem armazenamento */
  }
}

export default function App() {
  const [catalogo, setCatalogo] = useState<Catalogo | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const location = useLocation();

  useEffect(() => {
    carregarCatalogo()
      .then(setCatalogo)
      .catch((e: Error) => setErro(e.message));
  }, []);

  useEffect(() => {
    // as listas cuidam da própria posição (voltam exatamente de onde saiu)
    if (!ehLista(location.pathname)) window.scrollTo({ top: 0 });
  }, [location.pathname]);

  if (erro) {
    return (
      <div className="aviso">
        <h1>Não foi possível abrir o hinário</h1>
        <p>{erro}</p>
        <button onClick={() => window.location.reload()}>Tentar de novo</button>
      </div>
    );
  }

  if (!catalogo) {
    return (
      <div className="carregando">
        <img className="marca-carregando logo-app" src={caminho('/icons/icone-192.png')} alt="" width={84} height={84} />
        <p>Abrindo o hinário…</p>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<Inicio catalogo={catalogo} />} />
      <Route path="/livro/:livroSlug" element={<SecaoPage catalogo={catalogo} />} />
      <Route path="/rascunhos" element={<Rascunhos />} />
      <Route path="/lavras/arquivos-pdf" element={<ArquivosPdf catalogo={catalogo} />} />
      <Route path="/lavras/arquivos-pdf/:n" element={<LeitorPdf catalogo={catalogo} />} />
      <Route path="/:secaoId" element={<SecaoPage catalogo={catalogo} />} />
      <Route path="/:secaoId/:itemId" element={<LeitorPage catalogo={catalogo} />} />
      <Route path="*" element={<NaoEncontrado />} />
    </Routes>
  );
}

function NaoEncontrado() {
  return (
    <div className="aviso">
      <h1>Página não encontrada</h1>
      <Link className="botao" to="/">
        Voltar ao início
      </Link>
    </div>
  );
}

function acharSecao(catalogo: Catalogo, id?: string): Secao | undefined {
  return catalogo.secoes.find((s) => s.id === id);
}

function Hub({ catalogo }: { catalogo: Catalogo }) {
  const cartoes = livrosDaPalavra(catalogo);
  return (
    <div className="pagina">
      <header className="topo topo-palavra">
        <BotaoVoltar fallback="/" />
        <div>
          <p className="topo-sub">Passagens bíblicas cantadas</p>
          <h1>Palavra de Deus Cantada</h1>
        </div>
        <MenuIr />
        <span className="contagem">{cartoes.reduce((t, c) => t + c.itens.length, 0)}</span>
      </header>
      <div className="inicio hub">
        <nav className="secoes">
          {cartoes.map((c) => (
            <Link key={c.para} to={c.para} className={`cartao cartao-${c.capa}`}>
              <img src={caminho(CAPAS[c.capa])} alt="" className="cartao-fundo" loading="eager" />
              <span className="cartao-veu" />
              <span className="cartao-conteudo">
                <span className="cartao-sub">Livro da Bíblia</span>
                <span className="cartao-titulo">{c.nome}</span>
                <span className="cartao-info">{c.itens.length === 1 ? '1 música' : `${c.itens.length} músicas`}</span>
              </span>
              <span className="cartao-seta" aria-hidden="true">
                ›
              </span>
            </Link>
          ))}
        </nav>
      </div>
    </div>
  );
}

function SecaoPage({ catalogo }: { catalogo: Catalogo }) {
  const { secaoId: idDaRota, livroSlug } = useParams();
  const secaoId = livroSlug ? 'palavra' : idDaRota;
  const secao = acharSecao(catalogo, secaoId);
  const livro = livroSlug ? livrosDaPalavra(catalogo).find((l) => l.slug === livroSlug) : undefined;
  const navigate = useNavigate();
  const local = useLocation();
  const [busca, setBusca] = useState(() => lerJson<{ busca?: string }>(chaveLista(window.location.pathname))?.busca ?? '');
  const [pdf, setPdf] = useState<{ feitos: number; total: number } | null>(null);
  const [erroPdf, setErroPdf] = useState<string | null>(null);
  const [avisoNumero, setAvisoNumero] = useState<string | null>(null);

  const rotaAtual = local.pathname;
  const ultimoRestaurado = useRef('');

  // guarda a busca digitada nesta lista
  useEffect(() => {
    const k = chaveLista(rotaAtual);
    const ant = lerJson<{ y?: number; id?: string; busca?: string }>(k) ?? {};
    gravarJson(k, { ...ant, busca });
  }, [busca, rotaAtual]);

  // ao chegar na lista: volta exatamente onde estava (ou ao item que acabou de ver)
  useLayoutEffect(() => {
    if (ultimoRestaurado.current === rotaAtual) return;
    const k = chaveLista(rotaAtual);
    const salvo = lerJson<{ y?: number; id?: string; vistoId?: string; busca?: string }>(k);
    const alvo = salvo?.vistoId ? document.querySelector<HTMLElement>(`[data-item-id="${CSS.escape(salvo.vistoId)}"]`) : null;
    if (!salvo || (salvo.y === undefined && !alvo)) {
      window.scrollTo({ top: 0 });
      ultimoRestaurado.current = rotaAtual;
      return;
    }
    if (salvo.vistoId && salvo.vistoId === salvo.id && salvo.y !== undefined) {
      window.scrollTo({ top: salvo.y });
    } else if (alvo) {
      alvo.scrollIntoView({ block: 'center' });
    } else if (salvo.y !== undefined) {
      window.scrollTo({ top: salvo.y });
    }
    ultimoRestaurado.current = rotaAtual;
  });

  if (!secao) return <NaoEncontrado />;
  if (secao.id === 'palavra' && !livroSlug) return <Hub catalogo={catalogo} />;
  if (livroSlug && !livro) return <NaoEncontrado />;

  const itens = livro ? ordenarItens({ ...secao, itens: livro.itens }) : ordenarItens(secao);
  const termo = normalizar(busca);
  const filtrados = termo
    ? itens.filter(
        (i) => normalizar(i.titulo).includes(termo) || String(i.num ?? '').includes(termo.replace(/^salmo\s*/, '')),
      )
    : itens;

  function irParaNumero(valor: string) {
    const n = parseInt(valor.replace(/\D/g, ''), 10);
    if (!n) return;
    const alvo = itens.find((i) => i.num === n);
    if (alvo) {
      setAvisoNumero(null);
      navigate(`/${secao!.id}/${alvo.id}`);
    } else {
      setAvisoNumero(`Não há o número ${n} neste hinário.`);
    }
  }

  async function exportarPdf() {
    if (pdf) return;
    setErroPdf(null);
    setPdf({ feitos: 0, total: 0 });
    try {
      const blob = await gerarPdfSecao(secao!, itens, (feitos, total) => setPdf({ feitos, total }));
      await baixarBlob(blob, nomeArquivoPdf(secao!));
    } catch (e) {
      setErroPdf(e instanceof Error ? e.message : 'Não foi possível gerar o PDF.');
    } finally {
      setPdf(null);
    }
  }

  return (
    <div className="pagina">
      <header className={`topo topo-${secao.id}`}>
        <BotaoVoltar fallback={secao.id === 'salmos' || secao.id === 'palavra' ? '/palavra' : '/'} />
        <div>
          <p className="topo-sub">{livro ? 'Palavra de Deus Cantada' : secao.subtitulo}</p>
          <h1>{livro ? livro.nome : secao.titulo}</h1>
        </div>
        <MenuIr />
        <span className="contagem">{itens.length}</span>
      </header>

      {itens.length > 0 && (
        <div className="barra-pdf">
          <button className="botao-pdf" onClick={exportarPdf} disabled={pdf !== null}>
            {pdf ? `Gerando PDF… ${pdf.feitos}/${pdf.total || '…'}` : 'Exportar PDF (todas em ordem)'}
          </button>
          {pdf && (
            <div className="barra-pdf-progresso" aria-hidden="true">
              <span style={{ width: `${pdf.total ? (pdf.feitos / pdf.total) * 100 : 4}%` }} />
            </div>
          )}
          {erroPdf && <p className="pdf-erro">{erroPdf}</p>}
        </div>
      )}

      <div className="barra-busca">
        {secao.ordem === 'numero' ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              irParaNumero(busca);
            }}
          >
            <input
              inputMode="numeric"
              pattern="[0-9]*"
              placeholder={secao.id === 'salmos' ? 'Ir para o Salmo…' : secao.id === 'caderninho' ? 'Ir para o número…' : 'Ir para o hino…'}
              value={busca}
              onChange={(e) => {
                setBusca(e.target.value);
                setAvisoNumero(null);
              }}
              aria-label="Número"
            />
            <button type="submit">Ir</button>
          </form>
        ) : (
          <input
            type="search"
            placeholder="Buscar pelo nome…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            aria-label="Buscar"
          />
        )}
      </div>

      {avisoNumero && <p className="pdf-erro" style={{ padding: '0 18px' }}>{avisoNumero}</p>}

      {secao.arquivos && secao.arquivos.length > 0 && !termo && (
        <Link to={`/${secao.id}/arquivos-pdf`} className="cartao-arquivos">
          <span className="arquivos-icone" aria-hidden="true">PDF</span>
          <span className="arquivos-texto">
            <strong>Arquivos PDF</strong>
            <small>Os {secao.arquivos.length} PDFs originais, do jeito que foram enviados</small>
          </span>
          <span aria-hidden="true">›</span>
        </Link>
      )}

      {filtrados.length === 0 ? (
        <p className="vazio">
          {itens.length === 0 ? 'Ainda não há músicas nesta seção.' : 'Nada encontrado com esse número ou nome.'}
        </p>
      ) : (
        <ol className="lista">
          {filtrados.map((item) => (
            <li key={item.id}>
              <Link
                to={`/${secao.id}/${item.id}`}
                className="linha"
                data-item-id={item.id}
                onClick={() => {
                  const k = chaveLista(local.pathname);
                  gravarJson(k, { ...(lerJson<object>(k) ?? {}), y: window.scrollY, id: item.id, vistoId: item.id, busca });
                }}
              >
                <span className="numero">{rotuloItem(secao, item)}</span>
                <span className="titulo-item">
                  {item.titulo}
                  {item.versiculos && <small className="versos"> · vers. {item.versiculos}</small>}
                </span>
                {item.paginas.length > 1 && <span className="selo">{item.paginas.length} págs</span>}
              </Link>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function tamanhoLegivel(bytes?: number | null): string {
  if (!bytes) return '';
  return bytes >= 1048576 ? `${(bytes / 1048576).toFixed(1).replace('.', ',')} MB` : `${Math.round(bytes / 1024)} KB`;
}

function ArquivosPdf({ catalogo }: { catalogo: Catalogo }) {
  const secao = acharSecao(catalogo, 'lavras');
  const arquivos: ArquivoPdf[] = secao?.arquivos ?? [];
  if (!secao) return <NaoEncontrado />;
  return (
    <div className="pagina">
      <header className={`topo topo-${secao.id}`}>
        <BotaoVoltar fallback={`/${secao.id}`} />
        <div>
          <p className="topo-sub">{secao.titulo}</p>
          <h1>Arquivos PDF</h1>
        </div>
        <MenuIr />
        <span className="contagem">{arquivos.length}</span>
      </header>
      <p className="arquivos-nota">Os PDFs originais, sem nenhuma alteração. Depois de baixar as músicas no aparelho, eles abrem também sem internet.</p>
      <ol className="lista">
        {arquivos.map((a, i) => (
          <li key={a.url}>
            <Link className="linha linha-pdf" to={`/lavras/arquivos-pdf/${i}`}>
              <span className="numero">PDF</span>
              <span className="titulo-item">
                {a.nome}
                <small className="versos">
                  {' '}
                  · {a.paginas ? `${a.paginas} págs` : ''}
                  {a.paginas && a.bytes ? ' · ' : ''}
                  {tamanhoLegivel(a.bytes)}
                </small>
              </span>
              <span aria-hidden="true">›</span>
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}

function LeitorPage({ catalogo }: { catalogo: Catalogo }) {
  const { secaoId, itemId } = useParams();
  const navigate = useNavigate();
  const secao = acharSecao(catalogo, secaoId);
  const todos = secao ? ordenarItens(secao) : [];
  const atual = todos.find((i) => i.id === itemId);
  const itens = secao?.id === 'palavra' && atual ? todos.filter((i) => (i.livro || 'Outros') === (atual.livro || 'Outros')) : todos;
  const indice = itens.findIndex((i) => i.id === itemId);
  const item = itens[indice];

  useEffect(() => {
    if (!secao) return;
    if (!item) navigate(rotaLista(secao.id), { replace: true });
  }, [secao, item, navigate]);

  if (!secao || !item) {
    return (
      <div className="carregando">
        <img className="marca-carregando logo-app" src={caminho('/icons/icone-192.png')} alt="" width={84} height={84} />
        <p>Abrindo…</p>
      </div>
    );
  }
  return (
    <Leitor
      secao={secao}
      item={item}
      anterior={itens[indice - 1]}
      proximo={itens[indice + 1]}
    />
  );
}
