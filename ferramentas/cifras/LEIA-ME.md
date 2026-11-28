# Ferramentas das cifras (troca de tom)

Scripts usados para ler as cifras das folhas e gerar `public/data/cifras/*.json`.
Foram escritos para rodar numa máquina de trabalho com as pastas `/tmp/cif`, `/tmp/nc` e `/tmp/hc`
(os caminhos estão fixos nos scripts); ficam aqui guardados para não se perderem.

## Hinos – Partitura: fotos com as cifras impressas riscadas e reescritas à mão noutro tom

Ordem para refazer `public/data/cifras/hinos.json` do zero:

1. `transf_hinos.py`  – registra cada foto contra as fontes já lidas (página do hinário `nc:<pg>`,
   folha digital `exata:<img>`, página do PDF de cifras `pdf:<p>`) → `/tmp/cif/transf/*.json`
2. copiar `dados/hinos_base_v58.json` para `public/data/cifras/hinos.json`
3. `transf_json.py`   – grava as fotos SEM caneta
4. `hfin_a.py`        – leva os lugares de cifra da página limpa para a foto, só pela geometria → `/tmp/cif/hfin/<foto>.json`
5. `hfin_d.py`        – monta as fotos COM caneta (usa `hfin_b.py`, `hfin_c.py`, rótulos e correções);
   com `CONF=1` gera `/tmp/cif/hfin/conf_<foto>.jpg` (a foto com a cifra final em azul sob cada lugar)
6. `copiar_folha.py`  – fotos repetidas da mesma folha: copia o resultado conferido de uma para a outra

Dados feitos à mão (em `dados/`):

- `hinos_final.py` (tabela `K`): quantos semitons separam o tom impresso do tom escrito à caneta em cada foto;
  `FORA`: fotos deixadas para fazer à mão (corretivo por cima da linha de cifras)
- `rotulos.json`: cifras lidas à mão, por posição na página do hinário
- `slots_extra/<pg>.txt` e `.linhas`: páginas do hinário completadas à mão (`nc_pag.py`, `nc_linha.py`).
  Rótulo `IMPRESSA=ESCRITA` = o que está escrito à mão naquele lugar (vale como está, sem transpor)
- `corr/<foto>.txt`: correções por foto, em coordenadas da imagem de conferência (1800 px no lado maior):
  `set X Y TXT`, `del X Y [borr]`, `add X Y TXT`, `put X Ybase TXT`, `mv X Y dx [dy]`,
  `era x0 y0 x1 y1`, `noera X Y`, `x X Y`, `no X Y`, `delq x0 y0 x1 y1`
- `linhas/<foto>.txt`: linhas de cifras marcadas à mão na foto

No aplicativo, uma entrada de cifra com texto vazio (`''`) é uma "borracha": só cobre aquele pedaço da folha com a
cor do papel quando o tom muda (apaga a letra da caneta e os riscos). Ver `planejar` em `src/cifras.ts`.

## Pendências (28/11)

- Hinos – Partitura sem troca de tom: 10, 61, 63, 93, 113, 116, 143, 147, 148, 153, 167, 186, 306, 311
  (folhas datilografadas só com cifra à mão, ou com corretivo); fotos em `FORA`.
- `nc_parciais.py`: achou 681 cifras do hinário lidas pela metade (ex.: "C/E" lida como "C") em 206 páginas;
  ainda não aplicado.
- Hinário Novo Cântico: 65 hinos com foto fora de foco + 148 e 149 (aguardando fotos novas).
