"""Generate an illustrated Korean installation and removal guide; requires reportlab."""
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
c.setTitle('묘리 설치 및 삭제 안내')
c.setAuthor('Myorii')


def text(x,y,value,size=12,color=INK):
    c.setFillColor(color); c.setFont('Korean',size); c.drawString(x,y,value)


def base(page,title,subtitle):
    c.setFillColor(HexColor('#fffafc')); c.rect(0,0,W,H,fill=1,stroke=0)
    text(40,799,'MYORII  /  설치 및 삭제 안내',10,ACCENT)
    text(40,754,title,27)
    text(40,725,subtitle,12,MUTED)
    c.setStrokeColor(HexColor('#e5dce1')); c.line(40,45,W-40,45)
    text(40,27,'macOS · Apple Silicon · v1.0',9,MUTED)
    text(W-65,27,f'{page} / 4',9,MUTED)


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
step(292,3,'실행 경고가 나오면 다음 페이지를 따라주세요.', ['이 배포본은 Apple Developer ID 서명·공증이 없어 경고가 날 수 있습니다.',
                                          '확인한 묘리 배포처에서 받은 파일인 경우에만 진행하세요.'])
c.setFillColor(HexColor('#f4e9ef'));c.roundRect(40,83,515,111,12,fill=1,stroke=0)
text(56,169,'앱이 열리면 로컬 AI 준비를 시작하세요',15)
text(56,144,'‘준비 시작’을 누르면 필요한 Ollama와 Qwen 모델을 내려받습니다.',11)
text(56,123,'기본 모델은 약 3.3GB입니다. 이미 설치돼 있으면 재사용합니다.',11)
text(56,102,'설치·실행 승인 방법은 3쪽, 삭제 방법은 4쪽에서 확인하세요.',11)
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
c.showPage()
base(3,'로컬 AI 준비를 끝내기','묘리에서 안내하는 Ollama 설치와 모델 다운로드를 완료해주세요.')
step(668,1,'‘준비 시작’을 누르세요.', [
    'Ollama와 기본 Qwen 모델 다운로드에 동의하는 버튼입니다.',
    '인터넷 연결과 충분한 저장 공간이 필요합니다. 모델은 약 3.3GB입니다.',
    '이미 설치된 Ollama와 모델은 다시 받지 않고 사용합니다.'])
c.setFillColor(HexColor('#f4e9ef'));c.roundRect(40,425,515,130,12,fill=1,stroke=0)
text(56,529,'설치 여부를 묻는 창이 나오면 ‘예’를 선택하세요',16,ACCENT)
text(56,501,'로컬 AI를 사용하려면 Ollama의 설치·실행을 허용해야 합니다.',12)
text(56,478,'macOS나 Ollama 버전에 따라 ‘열기’·‘허용’ 등으로 표시될 수 있습니다.',11)
text(56,455,'묘리의 준비 과정에서 요청한 Ollama인지 확인하고 승인해주세요.',11)
step(389,2,'다운로드와 모델 준비가 끝날 때까지 기다리세요.', [
    '진행 화면에 현재 작업과 다운로드량이 표시됩니다.',
    '처음 모델을 불러오는 데 시간이 걸릴 수 있습니다.',
    '완료되면 묘리 채팅 화면이 열립니다.'])
step(274,3,'실패하면 안내를 확인하고 ‘다시 시도’를 누르세요.', [
    '인터넷·저장 공간과 Ollama 실행 승인 여부를 확인하세요.',
    '받은 모델 일부는 재시도할 때 이어서 사용할 수 있습니다.'])
step(178,4,'API만 쓸 때는 ‘API 사용 / 나중에’를 선택하세요.', [
    '이 경우 Ollama 설치는 필수가 아닙니다.',
    '설정에서 API 제공자와 모델을 선택하고 API 키를 등록하세요.'])
text(40,76,'도움말: 설정 → 정보 → 도움말 사이트 열기',11,ACCENT)
c.showPage()
base(4,'묘리 앱과 데이터 제거하기','제거 도구에서 대화·할일·메모 데이터를 지울지 선택할 수 있습니다.')
step(668,1,'묘리를 종료한 뒤, DMG의 ‘묘리 제거’를 여세요.', [
    '묘리 설정에서 ‘앱 종료’를 누르세요. 창을 닫는 것과 다릅니다.',
    'DMG를 지웠다면 배포처에서 다시 내려받아 여세요.',
    '제거 도구 실행이 차단되면 2쪽의 ‘그래도 열기’ 절차를 따르세요.'])
c.setFillColor(HexColor('#f4e9ef'));c.roundRect(40,419,515,145,12,fill=1,stroke=0)
text(56,538,'항상 함께 처리',13,ACCENT)
text(56,515,'묘리 앱 (데이터는 기본적으로 보존)',12)
text(56,493,'데이터 선택 시 저장된 API 키도 삭제합니다.',11)
text(56,467,'선택한 경우에만 처리 (기본값: 선택 안 됨)',13,ACCENT)
text(56,443,'□ 묘리 데이터     □ Ollama 앱     □ 전체 Ollama 모델',11)
step(384,2,'데이터, Ollama와 모델을 지울지 각각 선택하세요.', [
    '묘리 데이터는 선택하지 않으면 재설치 후에도 유지됩니다.',
    '모델을 선택하면 Qwen뿐 아니라 기본 위치의 전체 모델이 대상입니다.',
    'Ollama 관련 항목을 선택했다면 Ollama와 사용 중인 AI 작업도 종료하세요.'])
step(269,3,'‘제거 대상 확인’에서 경로를 보고 ‘제거’를 누르세요.', [
    '다른 곳에 둔 묘리는 ‘다른 위치의 묘리 선택…’으로 추가하세요.',
    '앱·DB·모델은 휴지통으로 옮깁니다. 영구 삭제는 휴지통을 비우세요.',
    '저장된 API 키 삭제는 되돌릴 수 없습니다. 서비스의 키 자체는 폐기되지 않습니다.'])
text(40,162,'자동 처리 범위',12,ACCENT)
text(40,142,'현재 계정의 DB: ~/Library/Application Support/Myorii',10)
text(40,125,'기본 모델: ~/.ollama/models · 다른 계정, 별도 경로, Homebrew 설치는 직접 확인하세요.',10)
text(40,108,'권한 오류가 나면 완료된 항목과 남은 항목을 확인하세요. 임의로 권한을 바꾸지 않습니다.',10)
text(40,78,'도움말  https://moyrii-web-2026.vercel.app',11,ACCENT)
c.linkURL('https://moyrii-web-2026.vercel.app', (40,73,400,91), relative=0)
c.save()
print(OUT)
