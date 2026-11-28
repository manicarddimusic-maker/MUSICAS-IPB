import sys,json,os,subprocess
# uso: mao_rot.py <nome já visto> "<rótulos separados por espaço>" [<próxima imagem>]
nome,rot=sys.argv[1],sys.argv[2].split()
J=json.load(open(f'/tmp/cif/mao/{nome}.json'))
if len(rot)!=len(J['toks']): print('ATENÇÃO: rótulos',len(rot),'tokens',len(J['toks'])); sys.exit(1)
for t,r in zip(J['toks'],rot): t['txt']=r.replace('+',' ')
json.dump(J,open(f'/tmp/cif/mao/{nome}.json','w')); print(nome,'salvo:',sum(1 for r in rot if r not in '-?'),'cifras')
if len(sys.argv)>3: subprocess.run(['python3','/tmp/cif/mao.py',sys.argv[3]])
