"""Qual foto traz qual hino, e quais páginas do livro (pg) cada foto mostra."""
import json
ROT="361 357 356 355 345 344 339 336 334 325-A 323 316 308 303 289 274 266 247 245 244 243 238 231 229 216 210 201 197 191 187 179 175 170 169 167 165 164 158 155 151 147 145 136 134 115 113 111 105 98 96 94 92 83 81 73 44 26 149 148 398 396 393 388 384 373 372 371".split()
def mapa():
    F=json.load(open('/tmp/nc/final/folhas.json')); idx=json.load(open('/tmp/nn/fotos.json'))
    pgs={}
    for f in F: pgs.setdefault(f['rot'],[]).extend(p['pg'] for p in f['pages'])
    out=[]
    for d,rot in zip(idx,ROT):
        NOVAS={'148':[232],'149':[233]}
        out.append(dict(i=d['i'],arq=d['arq'],w=d['w'],h=d['h'],rot=rot,pgs=sorted(pgs.get(rot,NOVAS.get(rot,[]))),deitada=d['w']>d['h'],nova=rot in NOVAS))
    return out
if __name__=='__main__':
    P=json.load(open('/tmp/nc/final/paginas.json'))
    for m in mapa():
        aviso=''
        if m['deitada'] and len(m['pgs'])!=2: aviso='  <<< foto deitada mas o hino tem %d página(s)'%len(m['pgs'])
        if not m['deitada'] and len(m['pgs'])!=1: aviso='  <<< foto em pé mas o hino tem %d página(s)'%len(m['pgs'])
        print(m['i'],m['rot'],'deitada' if m['deitada'] else 'em pé',m['pgs'],[P.get(str(p),{}).get('cls','NOVA') for p in m['pgs']],aviso)
