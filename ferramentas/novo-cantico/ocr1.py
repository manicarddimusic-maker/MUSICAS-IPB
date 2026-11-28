import json,sys,subprocess,re,time
from PIL import Image
def osd(im):
    im.convert('L').resize((im.width*1000//max(im.size),im.height*1000//max(im.size))).save('/tmp/nc/_o.png')
    r=subprocess.run(['tesseract','/tmp/nc/_o.png','-','--psm','0','-l','osd'],capture_output=True,text=True).stdout
    m=re.search(r'Rotate: (\d+)',r); c=re.search(r'Orientation confidence: ([\d.]+)',r)
    return (int(m.group(1)) if m else None, float(c.group(1)) if c else 0)
b=json.load(open('big.json'))
for f,k in (('a',0),('a',3),('a',4),('a',1)):
    im=Image.open(b[f][k]); t=time.time()
    print(f,k,im.size,osd(im),round(time.time()-t,1))
