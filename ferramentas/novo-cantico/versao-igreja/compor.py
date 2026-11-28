"""Folha da igreja: a música (pautas, notas e cifras) do hino 111 com a letra do hino 9.
Parte da página tratada do 111 (/tmp/nc/final/p173.png); troca título, crédito da letra, a letra inteira e o rodapé.
Saída: /tmp/ig/p009_igreja.png (mesmo quadro da página 173: as cifras ficam nos mesmos lugares)."""
import sys,json
sys.path.insert(0,'/tmp/ig'); sys.path.insert(0,'/tmp/cif')
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
from base import carregar,sistemas
from letras_antigas import linhas
X='/tmp/ig/fontes/'
F_LETRA=X+'goimg/font/gofont/ttfs/Go-Regular.ttf'
F_TITULO=X+'x-bodoni-moda/package/files/bodoni-moda-latin-900-normal.woff'
F_NOTA='/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf'
K=4                                     # tudo é desenhado 4x maior e reduzido (bordas lisas)

# ---- a letra do hino 9, como está impressa no hinário (sílabas, hifens e elisões "_") ----
ESTROFES=[
 ["A ti, ó Deus, al-tís-si-mo Se-nhor,","E-ter-no Pai, su-pre-mo ben-fei-tor,","Teus fi-lhos vêm a-le-gres dar lou-vor."],
 ["A ti, Deus Fi-lho, Sal-va-dor Je-sus,","Da gra-ça_a fon-te, da ver-da-de_a luz;","Por teu a-mor mos-tra-do so-bre_a cruz,"],
 ["A ti, ó Deus, Es-pí-ri-to de_a-mor,","De nos-sas al-mas san-ti-fi-ca-dor.","Mes-tre di-vi-no, bom Con-so-la-dor,"],
 ["Ó Deus tri-ú-no, vem-nos con-ce-der","A ple-ni-tu-de do re-al po-der","E_as nos-sas al-mas vêm, a-qui, re-ger."],
]
# 4ª linha: 8 sílabas em 10 notas — o "le" do 1º Aleluia e o "lu" do 2º valem duas notas (notas 3 e 9 sem sílaba)
ALELUIA=[(1,'A',True),(2,'le',True),(4,'lu',True),(5,'ia!',False),(6,'A',True),(7,'le',True),(8,'lu',True),(10,'ia!',False)]
MELISMA={2:3,8:9}                       # sílaba na nota 2 se estende pela 3; a da 8 pela 9
def silabas(linha):
    """'A ti, ó Deus, al-tís-si-mo' -> [(nota, texto, tem_hifen_depois)]"""
    out=[]; n=0
    for pal in linha.split():
        ps=pal.split('-')
        for i,s in enumerate(ps):
            n+=1; out.append((n,s,i<len(ps)-1))
    return out

def apagar_e_medir():
    e,P,d=carregar(); H,W=e.shape
    limpa=e.copy(); info=[]
    for k,S in enumerate(sistemas(e,P,d)):
        L,(y0,y1),lab=linhas(e,S,d)
        assert len(L)==4,(k,len(L))
        ids=[c['i'] for l in L for c in l['comps']]
        m=np.isin(lab,ids).astype(np.uint8)
        m=cv2.dilate(m,np.ones((7,7),np.uint8))
        limpa[y0:y1][m>0]=255
        # colunas (notas): centros das palavras antigas, agrupados
        cs=sorted((t['x0']+t['x1'])/2 for l in L for t in l['toks'][1:] if t['x1']-t['x0']>=9)
        grupos=[]
        for c in cs:
            if grupos and c-grupos[-1][-1]<=9: grupos[-1].append(c)
            else: grupos.append([c])
        col=[float(np.median(g)) for g in grupos if len(g)>=2 or (k==3 and g[0]>1340)]
        x0=float(np.median([l['toks'][0]['x0'] for l in L]))
        bases=np.array([l['base'] for l in L],float); r=np.arange(4)
        a,b=np.polyfit(r,bases,1)
        info.append(dict(x0=x0,col=col,bases=[float(b+a*i) for i in r],passo=float(a)))
    return e,limpa,info,d
if __name__=='__main__':
    e,limpa,info,d=apagar_e_medir()
    for k,i in enumerate(info): print('sistema',k,'x0',i['x0'],'bases',np.round(i['bases'],1).tolist(),'passo %.2f'%i['passo'],'colunas',len(i['col']),np.round(i['col'],1).tolist())
    cv2.imwrite('/tmp/ig/vis/limpa.png',limpa)
    dif=(e.astype(int)-limpa.astype(int))!=0
    print('pixels apagados',int(dif.sum()))

# ---------------------------------------------------------------- composição
def _fonte(caminho,alvo_px,letra,k=K):
    """fonte no tamanho em que a letra dada fica com alvo_px de altura (medido já na escala final)"""
    lo,hi=4.0,2000.0
    for _ in range(40):
        mid=(lo+hi)/2; f=ImageFont.truetype(caminho,mid); b=f.getbbox(letra)
        if (b[3]-b[1])/k<alvo_px: lo=mid
        else: hi=mid
    return ImageFont.truetype(caminho,(lo+hi)/2)
def consertar_hastes(limpa,orig):
    """três lugares em que uma letra antiga encostava na haste de uma nota: sai a letra, fica a haste"""
    # 'h' (3º sistema): haste nas colunas 786-787, que seguia por baixo da letra
    limpa[1647:1671,782:799]=255
    # (a ponta dela ficava escondida pela letra; agora começa junto da linha de base)
    # 'e' (3º sistema): haste nas colunas 1081-1082, começa logo abaixo da letra
    limpa[1654:1673,1070:1086]=255
    limpa[1669:1673,1081]=orig[1676:1680,1081]; limpa[1669:1673,1082]=orig[1676:1680,1082]
    # vírgula (4º sistema) em cima da ponta da haste
    limpa[2157:2170,228:241]=255
    return limpa
def credito_wright():
    """recorte nítido de "HENRY MAXWELL WRIGHT, 1901" (página do hino 134, mesma letra e mesmo tamanho)"""
    p=cv2.imread('/tmp/nc/final/p207.png',0)
    faixa=p[278:322,40:760]; ink=faixa<150
    ys=np.where(ink.sum(axis=1)>0)[0]; xs=np.where(ink.sum(axis=0)>0)[0]
    # só a primeira linha (até o vão em branco)
    y0=ys[0]; y1=y0
    while y1+1 in set(ys.tolist()): y1+=1
    rec=faixa[y0:y1+1,xs[0]:xs[-1]+1]
    return rec
def compor(debug=False):
    e,limpa,info,d=apagar_e_medir(); H,W=limpa.shape
    limpa=consertar_hastes(limpa,e)
    # --- o que sai do alto e do pé da página do 111
    tc=(e[312:360,40:700]<150).sum(axis=1)                               # 2ª linha do crédito antigo (para alinhar o novo)
    base_cred=312+int(np.where(tc>=0.35*tc.max())[0][-1])+1
    x_cred=40+int(np.where((e[262:356,40:700]<150).sum(axis=0)>0)[0][0])
    limpa[0:150,:]=255                     # título e número do 111
    limpa[262:358,30:1040]=255             # créditos da letra do 111 (duas linhas)
    limpa[2385:,:]=255                     # rodapé do 111
    # --- crédito da letra do hino 9 (recorte nítido)
    rec=credito_wright(); h,w=rec.shape
    # a base das maiúsculas: última linha com bastante tinta (a vírgula desce um pouco)
    tinta=(rec<150).sum(axis=1); base_rec=int(np.where(tinta>=0.35*tinta.max())[0][-1])+1
    y0=base_cred-base_rec
    limpa[y0:y0+h,x_cred:x_cred+w]=np.minimum(limpa[y0:y0+h,x_cred:x_cred+w],rec)
    # --- camada de texto novo (4x)
    cam=Image.new('L',(W*K,H*K),255); dr=ImageDraw.Draw(cam)
    f=_fonte(F_LETRA,20.6,'D')
    hif='-'
    def tinta_x(txt,x,ancora):
        b=dr.textbbox((x,0),txt,font=f,anchor=ancora); return b[0],b[2]
    relat=[]
    for s,inf in enumerate(info):
        for r in range(4):
            Y=inf['bases'][r]*K
            if s<3: sil=silabas(ESTROFES[r][s]); mel={}
            else: sil=list(ALELUIA); mel=dict(MELISMA)
            assert max(n for n,_,_ in sil)<=10 and (s==3 or len(sil)==10),(s,r,len(sil))
            postos=[]
            for n,txt,hd in sil:
                if n==1:
                    t=f'{r+1}.{txt}'
                    a,b=tinta_x(t,0,'ls'); x=inf['x0']*K-a
                    dr.text((x,Y),t,font=f,fill=0,anchor='ls'); ex=tinta_x(t,x,'ls')
                else:
                    x=inf['col'][n-2]*K
                    dr.text((x,Y),txt,font=f,fill=0,anchor='ms'); ex=tinta_x(txt,x,'ms')
                postos.append((n,ex,hd))
            if s==3 and r==3:               # "Amém" depois da 4ª estrofe
                for n,txt,hd in ((11,'A',True),(12,'mém.',False)):
                    x=inf['col'][n-2]*K; dr.text((x,Y),txt,font=f,fill=0,anchor='ms'); postos.append((n,tinta_x(txt,x,'ms'),hd))
            # hifens: no meio do vão; na sílaba que vale duas notas, embaixo da nota sem sílaba
            for i,(n,ex,hd) in enumerate(postos[:-1]):
                if not hd: continue
                prox=postos[i+1]
                xm=(ex[1]+prox[1][0])/2 if n not in mel else inf['col'][mel[n]-2]*K
                vao=prox[1][0]-ex[1]
                if vao<5*K: relat.append((s,r,n,'vão curto',vao/K)); continue
                dr.rectangle([xm-5.5*K,Y-9.75*K,xm+5.5*K,Y-7.25*K],fill=0)
    # --- título e número
    ft=_fonte(F_TITULO,60.0,'D'); TR=3; SX=1.12; ESP=7
    def titulo(txt,fonte):
        larg=int(sum(fonte.getlength(c) for c in txt)+ESP*len(txt)+80*K); alt=int(140*K)
        im=Image.new('L',(larg,alt),255); d2=ImageDraw.Draw(im); x=40*K
        for i,c in enumerate(txt):
            d2.text((x,100*K),c,font=fonte,fill=0,anchor='ls',stroke_width=TR,stroke_fill=0)
            av=fonte.getlength(txt[i:i+2])-fonte.getlength(txt[i+1:i+2]) if i+1<len(txt) else fonte.getlength(c)
            x+=av+ESP
        a=np.array(im); a=cv2.resize(a,(int(a.shape[1]*SX),a.shape[0]),interpolation=cv2.INTER_AREA)
        xs=np.where((a<128).sum(axis=0)>0)[0]
        return a[:,xs[0]:xs[-1]+1]          # a linha de base fica em y=100*K
    cam=np.array(cam)
    def colar(img,x_esq,base_y):
        y0=int(round(base_y*K))-100*K; x0=int(round(x_esq*K)); h,w=img.shape
        cam[y0:y0+h,x0:x0+w]=np.minimum(cam[y0:y0+h,x0:x0+w],img)
    t=titulo('Aleluia ao Deus trino',ft)
    colar(t,788-t.shape[1]/K/2,119)
    fn=_fonte(F_TITULO,63.0,'9'); nmr=titulo('9',fn)
    colar(nmr,1529-nmr.shape[1]/K,119)
    # --- aviso de que é a versão da igreja
    cam=Image.fromarray(cam); dr=ImageDraw.Draw(cam)
    fa=_fonte(F_NOTA,17.0,'L')
    dr.text((788*K,250*K),'Letra do hino 9 com a música do hino 111 — versão da IPB Lavras',font=fa,fill=0,anchor='ms')
    cam=np.array(cam)
    red=cv2.resize(cam,(W,H),interpolation=cv2.INTER_AREA)
    # onde a ponta de uma haste encostaria numa sílaba nova, fica um respiro de 3 px (só nas faixas da letra)
    halo=cv2.dilate((red<128).astype(np.uint8),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)))>0
    faixa=np.zeros((H,W),bool)
    for inf in info: faixa[int(inf['bases'][0]-30):int(inf['bases'][3]+10),100:]=True
    limpa[halo&faixa]=255
    out=np.minimum(limpa,red)
    if debug: print('avisos:',relat)
    return out,e
if __name__=='__main__' and 'compor' in sys.argv:
    out,e=compor(debug=True)
    cv2.imwrite('/tmp/ig/p009_igreja.png',out)
    print(out.shape)
