import { useCallback, useEffect, useState } from 'react';
import Anotar from './Anotar';
import { BotaoVoltar, MenuIr } from './Navegar';
import {
  FolhaDef,
  FundoBranco,
  Rascunho,
  achatar,
  apagarRascunho,
  gravarRascunho,
  listarRascunhos,
  novoId,
} from './anotacoes';

export async function salvarRascunho(base: Partial<Rascunho> & { titulo: string }, folhas: FolhaDef[]): Promise<Rascunho> {
  const agora = Date.now();
  const r: Rascunho = {
    id: base.id ?? novoId(),
    titulo: base.titulo.trim() || 'Rascunho sem nome',
    criado: base.criado ?? agora,
    em: agora,
    origem: base.origem,
    folhas: folhas.map((f) => ({ ...f, tracos: [...f.tracos] })),
    miniatura: await achatar(folhas[0], folhas[0].tracos, 420).catch(() => undefined),
  };
  await gravarRascunho(r);
  return r;
}

function Miniatura({ blob }: { blob?: Blob }) {
  const [url, setUrl] = useState<string>();
  useEffect(() => {
    if (!blob) return;
    const u = URL.createObjectURL(blob);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [blob]);
  return url ? <img src={url} alt="" className="rasc-mini" /> : <span className="rasc-mini vazio" aria-hidden="true">♪</span>;
}

export default function Rascunhos() {
  const [lista, setLista] = useState<Rascunho[] | null>(null);
  const [aberto, setAberto] = useState<Rascunho | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const recarregar = useCallback(() => {
    listarRascunhos()
      .then(setLista)
      .catch(() => {
        setLista([]);
        setErro('Este navegador não permite guardar rascunhos aqui.');
      });
  }, []);
  useEffect(recarregar, [recarregar]);

  function novo(fundo: FundoBranco) {
    const agora = Date.now();
    setAberto({
      id: novoId(),
      titulo: 'Novo rascunho',
      criado: agora,
      em: agora,
      folhas: [{ branco: { w: 1600, h: 2200, fundo }, tracos: [] }],
    });
  }

  async function apagar(r: Rascunho) {
    if (!window.confirm(`Apagar o rascunho “${r.titulo}”?`)) return;
    await apagarRascunho(r.id);
    recarregar();
  }

  async function copiar(r: Rascunho) {
    await salvarRascunho({ titulo: `Cópia de ${r.titulo}`, origem: r.origem }, r.folhas);
    recarregar();
  }

  if (aberto) {
    return (
      <Anotar
        rascunho
        titulo={aberto.titulo}
        folhas={aberto.folhas}
        onSalvar={async (f, nome) => {
          const r = await salvarRascunho({ ...aberto, titulo: nome }, f);
          setAberto({ ...r, miniatura: undefined });
        }}
        onDuplicar={async (f, nome) => {
          await salvarRascunho({ titulo: `Cópia de ${nome}`, origem: aberto.origem }, f);
        }}
        onFechar={() => {
          setAberto(null);
          recarregar();
        }}
      />
    );
  }

  return (
    <div className="pagina">
      <header className="topo topo-rascunhos">
        <BotaoVoltar fallback="/" />
        <div>
          <p className="topo-sub">Só neste aparelho</p>
          <h1>Meus Rascunhos</h1>
        </div>
        <MenuIr />
        <span className="contagem">{lista?.length ?? 0}</span>
      </header>

      <section className="rasc-novo" aria-label="Criar rascunho">
        <p>Criar uma folha nova para escrever à mão ou digitar:</p>
        <div>
          <button onClick={() => novo('branca')}>＋ Em branco</button>
          <button onClick={() => novo('linhas')}>＋ Pautada</button>
          <button onClick={() => novo('pauta')}>＋ Partitura</button>
        </div>
        <small>Para fazer um rascunho de uma música existente, abra a música e use ✎ → “Duplicar como rascunho”.</small>
      </section>

      {erro && <p className="pdf-erro" style={{ padding: '0 18px' }}>{erro}</p>}
      {lista && lista.length === 0 && !erro && <p className="vazio">Você ainda não tem rascunhos.</p>}
      <ol className="lista">
        {lista?.map((r) => (
          <li key={r.id} className="rasc-item">
            <button className="rasc-abrir" onClick={() => setAberto(r)}>
              <Miniatura blob={r.miniatura} />
              <span className="titulo-item">
                {r.titulo}
                <small className="versos">
                  {' '}
                  · {r.folhas.length} {r.folhas.length === 1 ? 'folha' : 'folhas'} · {new Date(r.em).toLocaleDateString('pt-BR')}
                  {r.origem ? ` · de “${r.origem}”` : ''}
                </small>
              </span>
            </button>
            <button className="rasc-acao" onClick={() => copiar(r)} aria-label={`Duplicar ${r.titulo}`} title="Duplicar">
              ⧉
            </button>
            <button className="rasc-acao" onClick={() => apagar(r)} aria-label={`Apagar ${r.titulo}`} title="Apagar">
              🗑
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
