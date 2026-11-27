/**
 * Mudança de tom das cifras.
 *
 * Só as notas mudam (a raiz do acorde e o baixo depois da barra); o resto do acorde
 * — m, 7, sus4, (b5), º… — continua exatamente como está escrito na folha.
 * A grafia segue a teoria: as notas sobem/descem pelo mesmo intervalo do tom
 * (Fm/Bb meio tom abaixo vira Em/A; E/G# um tom acima vira F#/A#).
 */

const LETRAS = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
const SEMITONS = [0, 2, 4, 5, 7, 9, 11];

/** letra: 0=C … 6=B; acid: −1 bemol, +1 sustenido */
export type Nota = { letra: number; acid: number };
export type Tom = { nota: Nota; menor: boolean };

const mod = (a: number, m: number) => ((a % m) + m) % m;

export function altura(n: Nota): number {
  return mod(SEMITONS[n.letra] + n.acid, 12);
}

export function nomeNota(n: Nota): string {
  return LETRAS[n.letra] + (n.acid > 0 ? '#'.repeat(n.acid) : 'b'.repeat(-n.acid));
}

export function nomeTom(t: Tom): string {
  return nomeNota(t.nota) + (t.menor ? 'm' : '');
}

function lerNota(txt: string, i: number): { nota: Nota; fim: number } | null {
  const letra = LETRAS.indexOf(txt[i]);
  if (letra < 0) return null;
  let acid = 0;
  let j = i + 1;
  while (j < txt.length && (txt[j] === '#' || txt[j] === '♯') && acid < 2) {
    acid++;
    j++;
  }
  if (acid === 0) {
    while (j < txt.length && (txt[j] === 'b' || txt[j] === '♭') && acid > -2) {
      acid--;
      j++;
    }
  }
  return { nota: { letra, acid }, fim: j };
}

type Pedaco = string | { nota: Nota; baixo: boolean };

/** Separa um texto de cifra ("F#m7/C#", "E-B", "G D G") em notas e no que fica igual. */
export function analisar(txt: string): Pedaco[] {
  const saida: Pedaco[] = [];
  let resto = '';
  let i = 0;
  while (i < txt.length) {
    const lida = lerNota(txt, i);
    if (lida) {
      const baixo = resto.endsWith('/');
      if (resto) saida.push(resto);
      resto = '';
      saida.push({ nota: lida.nota, baixo });
      i = lida.fim;
    } else {
      resto += txt[i];
      i++;
    }
  }
  if (resto) saida.push(resto);
  return saida;
}

export type AcordeLido = { raiz: Nota; menor: boolean; dim: boolean };

/** Lê o primeiro acorde de um texto (para descobrir o tom da música). */
export function lerAcorde(txt: string): AcordeLido | null {
  const p = analisar(txt);
  const i = p.findIndex((x) => typeof x !== 'string');
  if (i < 0) return null;
  const raiz = (p[i] as { nota: Nota }).nota;
  const depois = typeof p[i + 1] === 'string' ? (p[i + 1] as string) : '';
  const menor = /^(m(?!aj)|-)/.test(depois);
  const dim = /^(º|°|dim|o(?![a-z]))/.test(depois) || /^m7\(b5\)|^m7b5|^ø/.test(depois);
  return { raiz, menor: menor && !dim, dim };
}

/** Quantos sustenidos (+) ou bemóis (−) tem a armadura do tom. */
function armadura(t: Tom): number {
  const quintas = [0, 2, 4, -1, 1, 3, 5][t.nota.letra] + 7 * t.nota.acid;
  return t.menor ? quintas - 3 : quintas;
}

const MAIORES: Nota[] = [
  { letra: 0, acid: 0 }, // C
  { letra: 1, acid: -1 }, // Db
  { letra: 1, acid: 0 }, // D
  { letra: 2, acid: -1 }, // Eb
  { letra: 2, acid: 0 }, // E
  { letra: 3, acid: 0 }, // F
  { letra: 3, acid: 1 }, // F#
  { letra: 4, acid: 0 }, // G
  { letra: 5, acid: -1 }, // Ab
  { letra: 5, acid: 0 }, // A
  { letra: 6, acid: -1 }, // Bb
  { letra: 6, acid: 0 }, // B
];
const MENORES: Nota[] = [
  { letra: 0, acid: 0 }, // Cm
  { letra: 0, acid: 1 }, // C#m
  { letra: 1, acid: 0 }, // Dm
  { letra: 2, acid: -1 }, // Ebm
  { letra: 2, acid: 0 }, // Em
  { letra: 3, acid: 0 }, // Fm
  { letra: 3, acid: 1 }, // F#m
  { letra: 4, acid: 0 }, // Gm
  { letra: 4, acid: 1 }, // G#m
  { letra: 5, acid: 0 }, // Am
  { letra: 6, acid: -1 }, // Bbm
  { letra: 6, acid: 0 }, // Bm
];

/** O tom de chegada, com o nome mais usado (Ab e não G#, F# e não Gb…). */
export function tomTransposto(t: Tom, semitons: number): Tom {
  if (mod(semitons, 12) === 0) return t;
  const a = mod(altura(t.nota) + semitons, 12);
  return { nota: (t.menor ? MENORES : MAIORES)[a], menor: t.menor };
}

/** Nome mais simples para uma altura: natural se existir; senão sustenido ou bemol. */
function simples(a: number, bemol: boolean): Nota {
  const k = SEMITONS.indexOf(a);
  if (k >= 0) return { letra: k, acid: 0 };
  if (bemol) return { letra: SEMITONS.indexOf(mod(a + 1, 12)), acid: -1 };
  return { letra: SEMITONS.indexOf(mod(a - 1, 12)), acid: 1 };
}

/** Coloca a nota na letra pedida; se ficar estranha (E#, Cb, dobrado), usa o nome simples. */
function naLetra(letra: number, a: number, bemol: boolean): Nota {
  let acid = mod(a - SEMITONS[letra], 12);
  if (acid > 6) acid -= 12;
  if (Math.abs(acid) > 1) return simples(a, bemol);
  // E#, B#, Cb e Fb: troca pela nota natural, que é como se lê na prática
  if (SEMITONS.indexOf(a) >= 0 && acid !== 0) return simples(a, bemol);
  return { letra, acid };
}

export type Transpositor = (txt: string) => string;

/**
 * Cria a função que troca as notas de um texto de cifra.
 * tom: tom original da música (se souber); com ele a grafia fica igual à dos livros.
 * usaBemol: quando não se sabe o tom, diz se a folha original prefere bemóis.
 */
export function criarTranspositor(semitons: number, tom: Tom | null, usaBemol = false): Transpositor {
  const n = mod(semitons, 12);
  if (n === 0) return (txt) => txt;
  const novo = tom ? tomTransposto(tom, n) : null;
  const bemol = novo ? armadura(novo) < 0 : usaBemol;
  const passoLetra = tom && novo ? mod(novo.nota.letra - tom.nota.letra, 7) : 0;
  const memoria = new Map<string, string>();

  function raizNova(r: Nota): Nota {
    const a = mod(altura(r) + n, 12);
    if (!tom) return simples(a, bemol);
    return naLetra(mod(r.letra + passoLetra, 7), a, bemol);
  }
  function baixoNovo(b: Nota, raiz: Nota | null, raizN: Nota | null): Nota {
    const a = mod(altura(b) + n, 12);
    if (!raiz || !raizN) return tom ? naLetra(mod(b.letra + passoLetra, 7), a, bemol) : simples(a, bemol);
    // o baixo guarda a mesma distância (de letras) que tinha da raiz: E/G# → F/A
    return naLetra(mod(raizN.letra + mod(b.letra - raiz.letra, 7), 7), a, bemol);
  }

  return (txt) => {
    const pronto = memoria.get(txt);
    if (pronto !== undefined) return pronto;
    let raiz: Nota | null = null;
    let raizN: Nota | null = null;
    let saida = '';
    for (const p of analisar(txt)) {
      if (typeof p === 'string') saida += p;
      else if (p.baixo) saida += nomeNota(baixoNovo(p.nota, raiz, raizN));
      else {
        raiz = p.nota;
        raizN = raizNova(p.nota);
        saida += nomeNota(raizN);
      }
    }
    memoria.set(txt, saida);
    return saida;
  };
}

/**
 * Descobre o tom pelos acordes, na ordem em que aparecem na folha.
 * Conta os acordes que pertencem a cada tom e dá peso ao último e ao primeiro acorde.
 */
export function estimarTom(acordes: string[]): Tom | null {
  const lidos = acordes.map(lerAcorde).filter((x): x is AcordeLido => !!x);
  if (!lidos.length) return null;
  const primeiro = lidos[0];
  const ultimo = lidos[lidos.length - 1];
  // graus do tom maior: I ii iii IV V vi vii°  (semitons e se é menor)
  const MAIOR: [number, 'M' | 'm' | 'd'][] = [[0, 'M'], [2, 'm'], [4, 'm'], [5, 'M'], [7, 'M'], [9, 'm'], [11, 'd']];
  // tom menor: i ii° III iv v V VI VII vii°
  const MENOR: [number, 'M' | 'm' | 'd'][] = [[0, 'm'], [2, 'd'], [3, 'M'], [5, 'm'], [7, 'm'], [7, 'M'], [8, 'M'], [10, 'M'], [11, 'd']];
  const tipo = (a: AcordeLido) => (a.dim ? 'd' : a.menor ? 'm' : 'M');
  let melhor: { pontos: number; a: number; menor: boolean } | null = null;
  for (let a = 0; a < 12; a++) {
    for (const menor of [false, true]) {
      const graus = menor ? MENOR : MAIOR;
      let pontos = 0;
      for (const ac of lidos) {
        const d = mod(altura(ac.raiz) - a, 12);
        if (graus.some(([s, q]) => s === d && q === tipo(ac))) pontos += 1;
        if (d === 0 && tipo(ac) === (menor ? 'm' : 'M')) pontos += 0.35; // a tônica costuma aparecer bastante
      }
      const ehTonica = (ac: AcordeLido) => mod(altura(ac.raiz) - a, 12) === 0 && tipo(ac) === (menor ? 'm' : 'M');
      if (ehTonica(ultimo)) pontos += Math.max(2.5, lidos.length * 0.2);
      if (ehTonica(primeiro)) pontos += Math.max(1.5, lidos.length * 0.1);
      if (!menor) pontos += 0.01; // empate: maior
      if (!melhor || pontos > melhor.pontos) melhor = { pontos, a, menor };
    }
  }
  if (!melhor) return null;
  const alvo = melhor;
  // usa a grafia que a própria folha usa para essa nota
  const daFolha = lidos.find((ac) => altura(ac.raiz) === alvo.a);
  const nota = daFolha ? daFolha.raiz : (alvo.menor ? MENORES : MAIORES)[alvo.a];
  return { nota, menor: alvo.menor };
}

/** Lê um tom escrito ("G", "Em", "E-", "Bb", "F#m"). */
export function lerTom(txt: string | undefined | null): Tom | null {
  if (!txt) return null;
  const a = lerAcorde(txt.trim());
  return a ? { nota: a.raiz, menor: a.menor } : null;
}

/** A folha usa mais bemóis do que sustenidos? (para quando o tom não é conhecido) */
export function prefereBemol(acordes: string[]): boolean {
  let b = 0;
  let s = 0;
  for (const t of acordes)
    for (const p of analisar(t))
      if (typeof p !== 'string') {
        if (p.nota.acid < 0) b++;
        else if (p.nota.acid > 0) s++;
      }
  return b > s;
}

/** Os 12 tons possíveis a partir do original, com quantos semitons cada um está (−5 … +6). */
export function tonsPossiveis(tom: Tom): { semitons: number; nome: string }[] {
  const lista: { semitons: number; nome: string }[] = [];
  for (let k = -5; k <= 6; k++) lista.push({ semitons: k, nome: nomeTom(tomTransposto(tom, k)) });
  return lista;
}

/** Deixa os semitons entre −5 e +6 (subir 7 é o mesmo que descer 5). */
export function normalizarSemitons(n: number): number {
  let k = mod(n, 12);
  if (k > 6) k -= 12;
  return k;
}
