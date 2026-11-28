import json,sys
from multiprocessing import Pool
import samepage
D=json.load(open('/tmp/nc/ident4.json'))
def hy(d): return d['hymn'] if d['role']=='T' else d.get('hymn_c')
pairs=[]
for src in 'abcde':
    P=[d for d in D if d['f']==src]
    for i in range(len(P)):
        for j in range(i+1,min(len(P),i+8)):
            a,b=P[i],P[j]
            if a['i']==b['i']: continue          # duas metades da mesma foto
            ha,hb=hy(a),hy(b)
            if ha is None or hb is None or abs(ha-hb)<=1: pairs.append((a['name'],b['name']))
def work(p):
    try: return (p[0],p[1],samepage.same(p[0],p[1]))
    except Exception as e: return (p[0],p[1],-1)
if __name__=='__main__':
    print(len(pairs),'pares',flush=True)
    # ordena para aproveitar o cache por processo
    with Pool(2) as pool: res=pool.map(work,pairs,chunksize=40)
    json.dump(res,open('/tmp/nc/dups.json','w'))
    print('dups>=80:',sum(1 for r in res if r[2]>=80))
