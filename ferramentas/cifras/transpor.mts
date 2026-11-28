// lê do stdin: [{k: semitons, acordes: [...] , tom?: "F"}]  ->  escreve [{tom, tomNovo, acordes: [...]}]
import { criarTranspositor, estimarTom, lerTom, nomeTom, prefereBemol, tomTransposto } from '/home/claude/musicas-ipb/src/tom.ts';
let txt = '';
process.stdin.on('data', (d) => (txt += d));
process.stdin.on('end', () => {
  const itens = JSON.parse(txt) as { k: number; acordes: string[]; tom?: string }[];
  const saida = itens.map((it) => {
    const reais = it.acordes.filter((a) => a && a !== '?');
    const tom = lerTom(it.tom) ?? estimarTom(reais);
    const t = criarTranspositor(it.k, tom, prefereBemol(reais));
    return { tom: tom ? nomeTom(tom) : null, tomNovo: tom ? nomeTom(tomTransposto(tom, it.k)) : null, acordes: it.acordes.map((a) => (a && a !== '?' ? t(a) : a)) };
  });
  process.stdout.write(JSON.stringify(saida));
});
