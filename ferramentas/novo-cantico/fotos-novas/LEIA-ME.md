# Fotos novas do Hinário Novo Cântico (28/11)

67 fotos de celular (57 + 10 reenviadas) trocaram as páginas fora de foco de 65 hinos
e trouxeram os hinos 148 e 149, que faltavam (páginas 232 e 233).

Ordem dos passos (tudo trabalha em `/tmp/nn` e `/tmp/nc`):

1. `conv.py` — copia as fotos, na ordem em que chegaram, para `/tmp/nn/fotos/NN.jpg`.
2. `mapa.py` — qual foto traz qual hino e quais páginas do livro.
3. `fazer.py` — para cada foto: tons (`pagina.py`), pautas seguidas na própria foto (`tracar.py`),
   modelo da curvatura da folha e medidas (`retif.py`), página desentortada em `/tmp/nn/ret2/`.
   As pautas são a régua: cada página sai com as pautas retas, com a mesma largura (1440 px)
   e o mesmo espaço entre linhas.
4. `final.py` — página final: reforço da letra onde a foto saiu fora de foco (`nitidez.py`),
   linhas da pauta reforçadas, quadro igual em todas as páginas (`estrutura.py` acha título, cifras e rodapé).
5. `completar.py` — só nas 8 páginas em que a foto cortou a última pauta (lista `MUSICA`) o pedaço de baixo
   vem da página antiga; rodapé cortado ou borrado some.
6. `integrar.py` — põe as páginas em `/tmp/nc/final` e atualiza `paginas.json`.
7. `../montar2.py` e `../pdf_nc.py` — folhas da aba (as refeitas ganham `-v2` no nome) e PDF único (`hinario-novo-cantico-v2.pdf`).

Cifras das páginas novas (pasta `../../cifras`):

- `nctudo.py` lê; `nc_palavras.py` confere cifra por cifra contra as palavras impressas
  (segunda leitura de cada palavra, cifra lida pela metade, pedaço separado pela haste de uma nota);
  o que as duas leituras não confirmaram foi lido a olho (`dados/nc_palavras_manual.json`, `dados/nc_adic.json`,
  lista `MANUAL` dentro do script, na ordem de `dados/nc_duvidas.json`).
- `nc_cobertura.py` acha tinta na linha das cifras que nenhuma cifra cobre; `nc_conferir.py` desenha tiras de conferência.
- Resultado final das 103 páginas: `dados/nc_palavras.json`. `nc_json.py` monta os arquivos do app.

Páginas a refazer quando chegarem fotos com a página inteira (a última pauta ficou de fora):
hinos 113, 179, 244, 303, 316, 357, 371 e 373.
