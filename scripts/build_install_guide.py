"""Generate an illustrated Korean installation guide; requires reportlab."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf/Myorii-install-guide.pdf'
FONT = '/System/Library/Fonts/Supplemental/AppleGothic.ttf'
pdfmetrics.registerFont(TTFont('Korean', FONT, subfontIndex=0))
W, H = 595.28, 841.89
INK = HexColor('#18212d')
MUTED = HexColor('#536173')
ACCENT = HexColor('#d72c68')
YELLOW = HexColor('#ffcf48')
OUT.parent.mkdir(parents=True, exist_ok=True)
c = canvas.Canvas(str(OUT), pagesize=(W,H))
c.setTitle('묘리 설치 안내')
c.setAuthor('Myorii')


def text(x,y,value,size=12,color=INK):
    c.setFillColor(color); c.setFont('Korean',size); c.drawString(x,y,value)


def base(page,title,subtitle):
    c.setFillColor(HexColor('#fffafc')); c.rect(0,0,W,H,fill=1,stroke=0)
    text(40,799,'MYORII  /  설치 안내',10,ACCENT)
    text(40,754,title,27)
    text(40,725,subtitle,12,MUTED)
    c.setStrokeColor(HexColor('#e5dce1')); c.line(40,45,W-40,45)
    text(40,27,'macOS · Apple Silicon · 테스트 배포본',9,MUTED)
    text(W-65,27,f'{page} / 2',9,MUTED)


def badge(x,y,n):
    c.setFillColor(ACCENT); c.circle(x,y,11,fill=1,stroke=0)
    c.setFillColor(white); c.setFont('Korean',12); c.drawCentredString(x,y-4,str(n))


def step(y,n,title,lines):
    badge(51,y+4,n); text(72,y,title,16)
    for i,line in enumerate(lines): text(72,y-25-i*19,line,12,MUTED)


def image(path,x,y,w,h):
    c.drawImage(str(path),x,y,w,h,mask='auto')

base(1,'묘리를 응용 프로그램으로 옮기기','DMG를 연 뒤, 묘리 아이콘을 Applications 폴더로 끌어다 놓으세요.')
step(674,1,'다운로드한 DMG를 두 번 클릭하세요.', ['설치 창의 안내 파일 이름과 아이콘 순서는 다를 수 있습니다.'])
# Crop only empty Finder space with a PDF clip; screenshot pixels remain intact.
source=ROOT/'packaging/macos/guide-images/drag-install.png'
iw,ih=ImageReader(str(source)).getSize()
x,y,scale=40,423,515/1100
c.saveState();p=c.beginPath();p.roundRect(x,y,515,190,10);c.clipPath(p,stroke=0)
image(source,x,y+190-ih*scale,iw*scale,ih*scale)
c.restoreState()
def pt(px,py):return x+px*scale,y+190-py*scale
c.setStrokeColor(YELLOW);c.setLineWidth(2.5)
for box in [(858,115,115,164),(518,115,125,164)]:
    bx,by=pt(box[0],box[1]+box[3]);c.roundRect(bx,by,box[2]*scale,box[3]*scale,7,stroke=1,fill=0)
# Arrow follows the actual right-to-left drag direction.
a=pt(916,335);b=pt(580,335)
c.setStrokeColor(YELLOW);c.setLineWidth(4);c.line(*a,*b)
c.line(b[0],b[1],b[0]+12,b[1]+7);c.line(b[0],b[1],b[0]+12,b[1]-7)
text(b[0]+18,b[1]+10,'이쪽으로 드래그',11,YELLOW)
step(405,2,'복사가 끝나면 Applications에서 실행하세요.', ['Finder의 응용 프로그램 폴더에서 Myorii를 두 번 클릭하세요.',
                                          '이미 설치했다면 묘리를 종료한 뒤 새 앱으로 교체하세요.'])
step(292,3,'실행 경고가 나오면 다음 페이지를 따라주세요.', ['이번 테스트 버전은 Apple 서명·공증이 없어 경고가 나올 수 있습니다.',
                                          '확인한 묘리 배포처에서 받은 파일인 경우에만 진행하세요.'])
c.setFillColor(HexColor('#f4e9ef'));c.roundRect(40,83,515,111,12,fill=1,stroke=0)
text(56,169,'앱이 열리면 로컬 AI 준비를 시작하세요',15)
text(56,144,'‘준비 시작’을 누르면 필요한 Ollama와 Qwen 모델을 내려받습니다.',11)
text(56,123,'기본 모델은 약 3.3GB입니다. 이미 설치돼 있으면 재사용합니다.',11)
text(56,102,'API만 사용하려면 ‘API 사용 / 나중에’를 선택하세요.',11)
c.showPage()
base(2,'처음 실행할 때 ‘그래도 열기’','경고창을 닫고  → 시스템 설정 → 개인정보 보호 및 보안을 여세요.')
source=ROOT/'packaging/macos/guide-images/security.png'
iw,ih=ImageReader(str(source)).getSize()
x,y,w=40,259,515
scale=w/iw;h=ih*scale
image(source,x,y,w,h)
def box(px,py,bw,bh,n):
    bx=x+px*scale;by=y+h-(py+bh)*scale
    c.setStrokeColor(YELLOW);c.setLineWidth(2.5);c.roundRect(bx,by,bw*scale,bh*scale,5,stroke=1,fill=0)
    badge(bx-7,by+bh*scale+5,n)
box(27,917,429,67,1)
box(1256,910,181,61,2)
box(824,598,471,66,3)
step(224,1,'왼쪽에서 ‘개인정보 보호 및 보안’을 선택하세요.', [])
step(185,2,'아래로 내려 ‘보안’ 영역의 ‘그래도 열기’를 누르세요.', [])
step(146,3,'확인창의 ‘그래도 열기’를 누르고 인증하세요.', ['Touch ID 또는 Mac 로그인 암호로 인증하면 묘리가 실행됩니다.'])
text(40,75,'버튼이 안 보이면 응용 프로그램의 Myorii를 한 번 실행한 뒤 다시 확인하세요.',10,MUTED)
c.save()
print(OUT)
