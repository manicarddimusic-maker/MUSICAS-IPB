import { useEffect, useState } from 'react';
import { Link, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';
import { Catalogo, Secao, carregarCatalogo, normalizar, ordenarItens, rotuloItem } from './catalogo';
import { baixarBlob, gerarPdfSecao, nomeArquivoPdf } from './exportarPdf';
import { caminho } from './ambiente';
import Leitor from './Leitor';
import Inicio from './Inicio';

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
    window.scrollTo({ top: 0 });
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

function SecaoPage({ catalogo }: { catalogo: Catalogo }) {
  const { secaoId } = useParams();
  const secao = acharSecao(catalogo, secaoId);
  const navigate = useNavigate();
  const [busca, setBusca] = useState('');
  const [pdf, setPdf] = useState<{ feitos: number; total: number } | null>(null);
  const [erroPdf, setErroPdf] = useState<string | null>(null);
  const [avisoNumero, setAvisoNumero] = useState<string | null>(null);

  if (!secao) return <NaoEncontrado />;

  const itens = ordenarItens(secao);
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
        <Link className="voltar" to="/" aria-label="Voltar ao início">
          ‹
        </Link>
        <div>
          <p className="topo-sub">{secao.subtitulo}</p>
          <h1>{secao.titulo}</h1>
        </div>
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
              placeholder={secao.id === 'salmos' ? 'Ir para o Salmo…' : secao.id === 'caderninho' ? 'Ir para o número…' : 'Ir para o hino número…'}
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
            placeholder="Buscar cântico pelo nome…"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            aria-label="Buscar"
          />
        )}
      </div>

      {avisoNumero && <p className="pdf-erro" style={{ padding: '0 18px' }}>{avisoNumero}</p>}

      {filtrados.length === 0 ? (
        <p className="vazio">
          {itens.length === 0 ? 'Ainda não há músicas nesta seção.' : 'Nada encontrado com esse número ou nome.'}
        </p>
      ) : (
        <ol className="lista">
          {filtrados.map((item) => (
            <li key={item.id}>
              <Link to={`/${secao.id}/${item.id}`} className="linha">
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

function LeitorPage({ catalogo }: { catalogo: Catalogo }) {
  const { secaoId, itemId } = useParams();
  const navigate = useNavigate();
  const secao = acharSecao(catalogo, secaoId);
  const itens = secao ? ordenarItens(secao) : [];
  const indice = itens.findIndex((i) => i.id === itemId);
  const item = itens[indice];

  useEffect(() => {
    if (!secao) return;
    if (!item) navigate(`/${secao.id}`, { replace: true });
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
