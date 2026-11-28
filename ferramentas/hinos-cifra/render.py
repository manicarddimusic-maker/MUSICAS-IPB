import json
from PIL import Image
d=json.load(open('segs.json')); heads=d['heads']; segs=d['segs']
S=400/72
XR={0:(71,291),1:(305,525)}
PAD=8
def crop(p,c,y0,y1):
    im=Image.open(f'pg/p-{p:03d}.png')
    x0,x1=XR[c]
    return im.crop((int(x0*S),int((y0-PAD)*S),int(x1*S),int((y1+PAD)*S))).convert('L')
meta=[]
for k in sorted(segs,key=int):
    h=heads[int(k)]; parts=[crop(*s) for s in segs[k]]
    nome=f"hc-{h['num']:03d}{'a' if h['label'] else ''}"
    W=parts[0].width; gap=int(10*S)
    total=sum(p.height for p in parts)+gap*(len(parts)-1)
    files=[]
    if len(parts)==1 or total/W<=2.2:
        im=Image.new('L',(W,total),255); y=0
        for p in parts: im.paste(p,(0,y)); y+=p.height+gap
        ims=[im]
    else: ims=parts
    for i,im in enumerate(ims):
        fn=f"{nome}{'' if len(ims)==1 else '-'+str(i+1)}.jpg"
        im.save('out/'+fn,quality=86,optimize=True); files.append(fn)
    meta.append(dict(num=h['num'],label=h['label'],titulo=h['title'],files=files,aspect=round(total/W,2)))
json.dump(meta,open('meta.json','w'),ensure_ascii=False,indent=1)
print(len(meta),sum(len(m['files']) for m in meta),'arquivos', sum(1 for m in meta if len(m['files'])>1),'hinos em varias imagens')
