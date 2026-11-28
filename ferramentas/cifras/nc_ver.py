import sys,json,cv2
pg=int(sys.argv[1]); y0,y1=int(sys.argv[2]),int(sys.argv[3])
r=json.load(open(f'/tmp/cif/pag/p{pg:03d}.json')); e=cv2.imread(f'/tmp/nc/final/p{pg:03d}.png')
for c in r['c']:
    x,base,w,cap,txt,conf,ya,yb=c[:8]
    cor=(0,0,255) if txt=='?' else (0,140,0)
    cv2.rectangle(e,(x-2,ya-2),(x+w+2,yb+2),cor,2)
    cv2.putText(e,txt,(x,ya-7),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,0,0) if txt!='?' else (0,0,255),2)
cv2.imwrite(f'/tmp/cif/dbg/ver{pg}.jpg',e[y0:y1],[cv2.IMWRITE_JPEG_QUALITY,70])
print(pg,r['tom'],len(r['c']),e.shape)
