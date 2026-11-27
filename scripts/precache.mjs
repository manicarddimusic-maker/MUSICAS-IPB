// Lista os arquivos do aplicativo (js, css, fontes, ícones, capas, cifras para mudar o tom) para o modo offline.
import { readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const raiz = 'dist';
const lista = [];
function andar(dir) {
  for (const n of readdirSync(join(raiz, dir))) {
    const rel = dir + '/' + n;
    if (statSync(join(raiz, rel)).isDirectory()) andar(rel);
    else lista.push('/' + rel);
  }
}
for (const d of ['assets', 'icons', 'midias/capas', 'data/cifras']) { try { andar(d); } catch {} }
writeFileSync(join(raiz, 'precache.json'), JSON.stringify(lista));
console.log('precache.json:', lista.length, 'arquivos');
