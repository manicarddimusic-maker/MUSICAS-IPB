"""Copia/converte as fotos novas para /tmp/nn/fotos/NN.jpg na ordem em que foram enviadas (com a orientação EXIF aplicada)."""
import os,json
from PIL import Image,ImageOps
import pillow_heif
pillow_heif.register_heif_opener()
U='/mnt/user-data/uploads/'
B1="9b4fbe15 b0fff8b1 ea920061 4669eeda 4930213f 8d512afe a7e96245 44bedaef d8a1beaa abc1a7bd 0e2bbab5 614289a0 6910d6bc f8473e68 45812168 f5a39da9 f10b823f 077c92a0 e6793ee3 87a43e1f".split()
B2="0f1bb993 833e1b9c 5a1c8779 804589d6 5adcdb38 99fc2083 b524824f e98b2123 37a7594f e771732e a95d85c6 e8057683 db060c1d bbd9cc70 e03420b8 5a2adfed 8310f35d 2a5a73b2 801879cf 7f5cd894".split()
B4="ceddbf58 f661b9b9 8ce2c463 e7bd7ce1 4ddb55fe 9242985e cf017d42 b7ff19a6 530c55e9 cc7c67be".split()
B3="aad1cc5c 85d9706a 349c3a11 1c8d8d33 934ace55 4ea8c988 51698686 716e3432 efca950e 7678225f 41e5e217 28fb0d47 24b0ca9c c0edf8c2 02a109a6 d4d1bf09 951a005c".split()
H=sorted([f for f in os.listdir(U) if f.lower().endswith('.heic')],key=lambda f:-int(f.rsplit('-',1)[1].split('.')[0]))
lista=[U+b+'-image.jpg' for b in B1+B2+B3+B4]      # os 10 .heic chegaram vazios (135 bytes, sem imagem)
idx=[]
for i,p in enumerate(lista):
    im=Image.open(p); im=ImageOps.exif_transpose(im).convert('RGB')
    out=f'/tmp/nn/fotos/{i:02d}.png' if p.lower().endswith('.heic') else f'/tmp/nn/fotos/{i:02d}.jpg'
    if p.lower().endswith('.heic'): im.save(out)
    else: im.save(out,quality=97,subsampling=0)
    idx.append(dict(i=i,src=os.path.basename(p),arq=out,w=im.size[0],h=im.size[1]))
    print(i,os.path.basename(p)[:40],im.size)
json.dump(idx,open('/tmp/nn/fotos.json','w'),indent=0)
