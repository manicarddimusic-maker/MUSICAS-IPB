import { CSSProperties, forwardRef, useMemo } from 'react';
import { FONTES, FolhaCifras, giroDaFolha, pesoDaFolha, planejar } from './cifras';
import type { Transpositor } from './tom';

type Props = {
  folha: FolhaCifras;
  transpor: Transpositor;
  /** muda quando as fontes terminam de carregar (refaz as medidas) */
  versao?: number;
  className?: string;
  style?: CSSProperties;
};

/**
 * Camada desenhada por cima da folha: cobre cada cifra original com a cor do papel
 * e escreve a cifra no novo tom, no mesmo lugar e do mesmo tamanho.
 */
const CifrasSobre = forwardRef<SVGSVGElement, Props>(function CifrasSobre({ folha, transpor, versao, className, style }, ref) {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const prontas = useMemo(() => planejar(folha, transpor), [folha, transpor, versao]);
  const fonte = FONTES[folha.f ?? 's'];
  return (
    <svg
      ref={ref}
      className={className}
      style={style}
      viewBox={`0 0 ${folha.w} ${folha.h}`}
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
      focusable="false"
    >
      <g transform={giroDaFolha(folha)}>
      {prontas.map((c, i) =>
        c.ilegivel ? (
          <rect key={`r${i}`} x={c.rx} y={c.ry} width={c.rw} height={c.rh} fill="rgba(214, 40, 40, 0.16)" stroke="#c62828" strokeWidth={Math.max(1, c.fs * 0.06)} rx={c.fs * 0.12} />
        ) : (
          <rect key={`r${i}`} x={c.rx} y={c.ry} width={c.rw} height={c.rh} fill={c.fundo} />
        ),
      )}
      <g fontFamily={fonte} fontWeight={pesoDaFolha(folha)}>
        {prontas.map((c, i) =>
          c.ilegivel ? null : (
            <text
              key={`t${i}`}
              x={c.x}
              y={c.base}
              fontSize={c.fs}
              fill={c.tinta}
              textLength={c.larg}
              lengthAdjust={c.larg ? 'spacingAndGlyphs' : undefined}
            >
              {c.txt}
            </text>
          ),
        )}
      </g>
      </g>
    </svg>
  );
});

export default CifrasSobre;
