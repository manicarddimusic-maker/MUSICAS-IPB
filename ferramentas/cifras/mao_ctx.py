import sys,json,cv2,numpy as np
def ctx(nome,partes=2,larg=1500,recorte=None):
    J=json.load(open(f'/tmp/cif/mao/{nome}.json')); a=cv2.imread(J['img'])
    for i,t in enumerate(J['toks']):
        cv2.rectangle(a,(t['x0']-3,t['y0']-3),(t['x1']+3,t['y1']+3),(0,150,0),2)
        cv2.putText(a,str(i+1),(t['x0']-6,t['y0']-7),cv2.FONT_HERSHEY_SIMPLEX,0.85,(255,0,0),2)
    if recorte: a=a[recorte[1]:recorte[3],recorte[0]:recorte[2]]
    # tira margens vazias: fica na área onde há caixas
    H=a.shape[0]; out=[]
    for k in range(partes):
        p=a[k*H//partes:(k+1)*H//partes+40]
        s=min(1.0,larg/p.shape[1]); p=cv2.resize(p,None,fx=s,fy=s,interpolation=cv2.INTER_AREA) if s<1 else p
        fn=f'/tmp/cif/mao/{nome}_ctx{k+1}.jpg'; cv2.imwrite(fn,p,[cv2.IMWRITE_JPEG_QUALITY,78]); out.append(fn)
    return out
if __name__=='__main__':
    print(ctx(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 2,int(sys.argv[3]) if len(sys.argv)>3 else 1500))
