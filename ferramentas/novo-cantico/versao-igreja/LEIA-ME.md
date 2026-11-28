# Versão da igreja: letra do hino 9 com a música do hino 111

Pedido do Guilherme (28/11): na IPB Lavras o hino 9 (Aleluia ao Deus trino) é cantado com a música
do hino 111 (Comunhão Divina, EVENTIDE). O hino 9 ficou com duas folhas na aba Novo Cântico:
a original e esta, montada à parte.

- `compor.py` parte da página tratada do 111 (`/tmp/nc/final/p173.png`), apaga a letra, o título,
  o crédito da letra e o rodapé dele e compõe a letra do hino 9 sílaba por sílaba embaixo das notas
  (`base.py` acha pautas e sistemas; `letras_antigas.py` acha as sílabas impressas, que dão a coluna de cada nota).
- A 4ª linha ("Aleluia! Aleluia!") tem 8 sílabas para 10 notas: o "le" do primeiro Aleluia e o "lu" do
  segundo valem duas notas cada (confirmado pelo Guilherme).
- Fontes usadas: Go Regular (letra; github.com/golang/image, font/gofont/ttfs), Bodoni Moda 900 (título;
  pacote npm @fontsource/bodoni-moda) e Liberation Sans Italic (aviso). O crédito "HENRY MAXWELL WRIGHT, 1901"
  é um recorte nítido da página do hino 134.
- `p009_igreja.png` é a página pronta (mesmo quadro da página 173, por isso as cifras do 111 servem sem ajuste).
- `extras.json` vai em `/tmp/nc/extras/`: o `montar2.py` gera a folha `nc-009-igreja.png`, põe no hino 9 depois da
  folha do livro (com `nome` e `tomProprio`) e grava `folhas_extras.json`, que o `nc_json.py` usa para as cifras.
- No app, a folha com `tomProprio` guarda a troca de tom dela à parte da folha original (Leitor.tsx / cifras.ts).

Se a folha for refeita, trocar o nome do arquivo (ex.: `nc-009-igreja-v2.png`): os aparelhos guardam as folhas pelo nome.
