import { Tom, criarTranspositor, nomeTom, normalizarSemitons, tomTransposto, tonsPossiveis } from './tom';

const NOTAS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'];

type Props = {
  /** tom original da folha (se foi possível saber) */
  tom: Tom | null;
  semitons: number;
  /** a folha tem cifras reconhecidas? */
  temCifras: boolean;
  aoMudar: (semitons: number) => void;
  aoFechar: () => void;
  /** quantas cifras desta folha o aplicativo não conseguiu ler */
  ilegiveis?: number;
  /** a foto desta folha está fora de foco: a leitura das cifras pode ter falhas */
  duvidosa?: boolean;
  className?: string;
};

function textoDiferenca(n: number): string {
  if (n === 0) return 'tom original';
  const meio = Math.abs(n);
  const tons = meio / 2;
  const quanto = tons === 0.5 ? '½ tom' : Number.isInteger(tons) ? `${tons} ${tons === 1 ? 'tom' : 'tons'}` : `${Math.floor(tons)} ${Math.floor(tons) === 1 ? 'tom' : 'tons'} e ½`;
  return `${quanto} ${n > 0 ? 'acima' : 'abaixo'}`;
}

/** Painel para subir ou descer o tom: de meio em meio tom, de um em um, ou direto no tom desejado. */
export default function PainelTom({ tom, semitons, temCifras, aoMudar, aoFechar, ilegiveis = 0, duvidosa = false, className }: Props) {
  const mudar = (n: number) => aoMudar(normalizarSemitons(n));
  const atual = tom ? nomeTom(tomTransposto(tom, semitons)) : semitons === 0 ? 'Original' : (semitons > 0 ? '+' : '−') + String(Math.abs(semitons) / 2).replace('.5', '½').replace(/^0½/, '½');
  return (
    <div className={`painel-tom${className ? ' ' + className : ''}`} role="dialog" aria-label="Mudar o tom das cifras" onPointerDown={(e) => e.stopPropagation()}>
      <div className="painel-tom-topo">
        <strong>Mudar o tom</strong>
        <button className="painel-tom-fechar" onClick={aoFechar} aria-label="Fechar o painel de tom">
          ✕
        </button>
      </div>
      {!temCifras ? (
        <>
          <p className="painel-tom-aviso">
            Nesta folha o aplicativo ainda não conseguiu ler as cifras (escritas à mão ou foto sem nitidez), então ele não troca direto na folha. Enquanto isso, use a
            tabela: escolha quanto subir ou descer e veja em que acorde cada nota se transforma.
          </p>
          <div className="painel-tom-linha">
            <button onClick={() => mudar(semitons - 2)} aria-label="Descer um tom">
              −1
            </button>
            <button onClick={() => mudar(semitons - 1)} aria-label="Descer meio tom">
              −½
            </button>
            <div className="painel-tom-atual" aria-live="polite">
              <b>{semitons === 0 ? '0' : (semitons > 0 ? '+' : '−') + String(Math.abs(semitons) / 2).replace('.5', '½').replace(/^0½/, '½')}</b>
              <small>{textoDiferenca(semitons)}</small>
            </div>
            <button onClick={() => mudar(semitons + 1)} aria-label="Subir meio tom">
              +½
            </button>
            <button onClick={() => mudar(semitons + 2)} aria-label="Subir um tom">
              +1
            </button>
          </div>
          {semitons !== 0 && (
            <div className="painel-tom-tabela" aria-label="Tabela de conversão das notas">
              {NOTAS.map((n) => (
                <span key={n}>
                  {n} <i>→</i> <b>{criarTranspositor(semitons, null, semitons < 0)(n)}</b>
                </span>
              ))}
            </div>
          )}
        </>
      ) : (
        <>
          <div className="painel-tom-linha">
            <button onClick={() => mudar(semitons - 2)} aria-label="Descer um tom">
              −1
            </button>
            <button onClick={() => mudar(semitons - 1)} aria-label="Descer meio tom">
              −½
            </button>
            <div className="painel-tom-atual" aria-live="polite">
              <b>{atual}</b>
              <small>{textoDiferenca(semitons)}</small>
            </div>
            <button onClick={() => mudar(semitons + 1)} aria-label="Subir meio tom">
              +½
            </button>
            <button onClick={() => mudar(semitons + 2)} aria-label="Subir um tom">
              +1
            </button>
          </div>
          {tom && (
            <div className="painel-tom-tons" role="group" aria-label="Ir direto para um tom">
              {tonsPossiveis(tom).map((t) => (
                <button
                  key={t.semitons}
                  className={t.semitons === semitons ? 'ativo' : t.semitons === 0 ? 'original' : undefined}
                  onClick={() => mudar(t.semitons)}
                  aria-pressed={t.semitons === semitons}
                >
                  {t.nome}
                </button>
              ))}
            </div>
          )}
          <div className="painel-tom-pe">
            <button className="painel-tom-original" onClick={() => mudar(0)} disabled={semitons === 0}>
              Voltar ao original{tom ? ` (${nomeTom(tom)})` : ''}
            </button>
            <span>As cifras em azul já estão no novo tom.</span>
          </div>
          {(ilegiveis > 0 || duvidosa) && (
            <p className="painel-tom-aviso painel-tom-atencao">
              {ilegiveis > 0
                ? `${ilegiveis === 1 ? 'Uma cifra desta folha não pôde ser lida' : `${ilegiveis} cifras desta folha não puderam ser lidas`}: ${ilegiveis === 1 ? 'fica marcada' : 'ficam marcadas'} em vermelho e ${ilegiveis === 1 ? 'continua' : 'continuam'} no tom original.`
                : 'A foto desta folha está fora de foco: confira as cifras, alguma pode ter ficado sem trocar.'}
            </p>
          )}
        </>
      )}
    </div>
  );
}
