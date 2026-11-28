import json,os
R='/home/claude/musicas-ipb/public/data/cifras/'
U=json.load(open('/tmp/cif/user.json'))
por={}
for img,F in U['folhas'].items():
    for sec in U['secoes'][img]: por.setdefault(sec,{})[img]=F
for sec,fs in por.items():
    fn=R+sec+'.json'
    J=json.load(open(fn)) if os.path.exists(fn) else dict(v=1,folhas={})
    J['folhas'].update(fs)
    json.dump(J,open(fn,'w'),ensure_ascii=False,separators=(',',':'))
    print(sec,'+',len(fs),'folhas do usuário; total',len(J['folhas']),os.path.getsize(fn)//1024,'KB')
