# Myorii

**[🌐 묘리 소개·다운로드 웹사이트](https://moyrii-web-2026.vercel.app/)**

macOS 메뉴바에서 채팅, 할일, 메모를 여는 Python 데스크톱 컴패니언.

## macOS v1.0 다운로드

[그림으로 보는 설치·삭제 안내 PDF](https://raw.githubusercontent.com/hazyala/myorii-2026/refs/heads/main/output/pdf/Myorii-install-guide.pdf) - 드래그 설치, 최초 실행 허용, Ollama 설치 승인과 데이터 삭제를 안내합니다. DMG에도 같은 PDF가 포함됩니다.

2026-10-15 수정본: macOS 27에서 버전 확인 오류로 Ollama 설치가 차단되던 문제를 해결했습니다.

**[묘리 DMG 다운로드 — Apple Silicon용, 약 57MB](https://raw.githubusercontent.com/hazyala/myorii-2026/refs/heads/main/releases/Myorii-v1.0-macOS-arm64.dmg)** · [SHA-256 체크섬](https://raw.githubusercontent.com/hazyala/myorii-2026/refs/heads/main/releases/Myorii-v1.0-macOS-arm64.dmg.sha256)

macOS 14 이상, Apple Silicon(M 시리즈)용입니다. DMG를 열고 Myorii를 Applications로 옮겨 실행하세요. 처음 실행하면 필요한 Ollama와 기본 Qwen 모델(약 3.3GB)을 내려받습니다. 기존 설치와 모델은 재사용합니다.

이 파일은 `main`의 `v1.0` 수정 배포본이며 Apple Developer ID 서명·공증은 없습니다. macOS가 실행을 차단하면 신뢰하는 배포처인지 확인한 뒤 시스템 설정 → 개인정보 보호 및 보안에서 실행 허용 여부를 결정해주세요. [설치·검증 범위 자세히 보기](docs/macos-distribution.md)

DMG에는 **묘리 제거** 도구도 포함됩니다. 묘리 앱을 휴지통으로 옮기며, 대화·할일·메모·설정과 저장된 API 키, Ollama 앱, 전체 기본 모델은 각각 선택한 경우에만 정리합니다. [제거 범위와 방법](docs/macos-removal.md)

표시 버전은 **v1.0**으로 유지하며 DMG 파일명에도 명시했습니다. 최초 배포의 `v1.0` Git 태그는 그대로 보존됩니다. 이 수정본은 해당 태그 이후 변경을 포함합니다.

## 앱 화면

발표자료 `Design_System.pptx`에 수록된 Myorii 화면입니다. 채팅의 코드블록 답변, 오늘의 할 일, 메모 목록과 편집 화면을 보여줍니다.

| 채팅 | 할 일 |
| :---: | :---: |
| <img src="docs/screenshots/presentation/01-chat.png" alt="코드블록 답변과 복사 버튼이 보이는 채팅 화면" width="320" /> | <img src="docs/screenshots/presentation/02-todo.png" alt="오늘의 할 일 목록과 완료 체크 화면" width="320" /> |

| 메모 목록 | 메모 편집 |
| :---: | :---: |
| <img src="docs/screenshots/presentation/03-memo.png" alt="메모 미리보기 카드와 새 메모 버튼" width="320" /> | <img src="docs/screenshots/presentation/04-memo-editor.png" alt="마크다운 서식이 보이는 메모 편집 화면" width="320" /> |

## 메뉴바에서 이어지는 작업

작업 중 작은 팝오버에서 모델에 질문하고, 답변의 코드나 이름을 복사하고, 필요한 내용을 메모로 남긴다. 대화 모델은 Ollama 또는 OpenAI·Gemini·Anthropic API 중 선택한다. 할일과 메모는 SQLite에 저장하며 채팅에서도 추가·조회·수정·삭제할 수 있다.

`main`에는 배포 코드와 설치 파일을, `dev`에는 다음 버전의 개발 코드를 유지한다. `v1.0` 태그는 main의 배포 커밋을 가리킨다. Windows 실행기는 아직 구현하지 않았다.

- `QSystemTrayIcon` 클릭으로 창을 열고 닫는다. `QLockFile`로 중복 실행을 막는다.
- 워커 thread가 응답을 받아 Qt signal로 화면에 전달한다. 네이밍·코드 등 일부 응답은 포맷 정리를 위해 버퍼링한다.
- 이미지와 문서 첨부를 모델 요청에 넣는다. 문서는 형식별 handler가 읽을 수 있는 텍스트·표본만 추출한다.
- 채팅 기록 저장을 선택하고 세션·할일·메모의 순서를 재정렬한다.
- `/todo `, `/memo ` 태그 또는 자연어로 로컬 저장소를 다룬다. 대상이 모호하면 후보 ID를 보여주고, 모델 응답을 기다리는 사이 바뀐 내용을 덮어쓰지 않는다.
- 테마·언어·모델 선택은 SQLite, 외부 API 키는 macOS Keychain에 저장한다.

## 요청이 지나가는 경로

```mermaid
flowchart LR
    UI[PyQt6 ChatView] --> Worker[ChatWorker]
    Worker --> Service[ChatService]
    Service --> Routes[의도 / 프롬프트 / 모델 / 응답 포맷]
    Service --> Files[AttachmentRouter]
    Service --> Tools[ChatTools]
    Tools --> Stores[todo_store / memo_store]
    UI --> Stores
    Stores --> DB[(SQLite)]
    Routes --> Provider[OllamaClient / CloudClient]
    Provider --> Models[선택한 LLM]
    UI --> ChatStore[chat_store / preferences]
    ChatStore --> DB
    Provider --> Keys[macOS Keychain]
```

의도에 따라 프롬프트와 응답 표현을 바꾸며 모델은 설정에서 선택한 모델을 유지한다. 로컬 도구 요청은 모델의 JSON 계획을 검증한 뒤 저장소에 적용한다. 일반 채팅과 파일 첨부, 저장소 변경의 상세 경계는 [아키텍처](docs/architecture.md)와 [라우터 설계](docs/router-design.md)에 있다.

## 기술과 코드 위치

| 역할 | 기술 / 코드 |
|---|---|
| 데스크톱 UI | PyQt6, `ui/`, `platform/macos/menubar.py` |
| LLM 요청 | Ollama Python client, urllib 기반 cloud client, `core/llm/` |
| 로컬 데이터 | sqlite3, `storage/`, `core/paths.py` |
| 첨부 파싱 | pypdf, pdfminer.six, 표준 XML/ZIP 처리, `core/llm/attachments/` |
| macOS 연결 | PyObjC, keyring macOS backend |
| 번들 | PyInstaller, `packaging/macos/Myorii.spec` |
| 회귀 테스트 | unittest, `tests/` |

`prompts/`는 공통·의도별 프롬프트, `core/tools/`는 채팅으로 저장소를 다루는 코드다. `docs/`는 개발 규칙, UI 가이드, 기존 로드맵과 수동 테스트를 보관한다.

## macOS 개발 실행

Python 3.12 이상과 메뉴바를 표시할 데스크톱 세션이 필요하다. `requirements.txt`에 macOS PyObjC 의존성이 있다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
ollama pull qwen3-vl:4b-instruct
ollama serve
```

Ollama가 실행된 상태에서 다른 터미널로 앱을 실행한다. 이미 Ollama 서비스가 켜져 있으면 다시 `serve`할 필요는 없다.

```bash
source .venv/bin/activate
python main.py
```

외부 API를 사용할 경우 설정에서 제공자·키·모델을 선택한다. `.env` 파일로 API 키를 받는 구조는 아니다. 이미지 입력 가능 여부와 모델 접근 권한은 선택한 제공자·모델에 달려 있다.

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p 'test_*.py'
PYINSTALLER_CONFIG_DIR=/tmp/myorii_pyinstaller .venv/bin/pyinstaller packaging/macos/Myorii.spec --noconfirm --clean
open -n dist/Myorii.app
```

테스트에는 재현 응답을 사용하는 제공자 검증이 포함된다.

## 데이터와 현재 범위

DB는 `~/Library/Application Support/Myorii/myorii.db`에 생성된다. 대화·첨부 경로·할일·메모·설정을 보관한다. 외부 API 모드에서는 대화와 첨부 내용이 해당 제공자에게 전송된다. 로컬 모델 모드는 Ollama를 사용한다.

PDF OCR, 오피스 서식·차트 해석, 전체 스프레드시트 계산은 구현 범위가 아니다. 시작 시 자동 실행 스위치는 UI만 있다. Windows, 동기화, 외부 도구 연결의 계획은 [기존 로드맵](docs/roadmap.md)에 따로 남겨 둔다.

[사용 예와 첨부 범위](docs/USAGE.md) · [수동 테스트](docs/manual-test-cases.md) · [개발 규칙](docs/development-rule.md)

## macOS 설치 파일

`python scripts/build_dmg.py`로 현재 Mac 아키텍처용 DMG를 만든다. 검은 묘리 아이콘과 Python 실행 환경을 포함한다. 첫 실행 시 필요한 Ollama·Qwen 모델을 준비 화면에서 다운로드하고, 기존 설치와 모델은 재사용한다. API 사용자는 로컬 준비를 건너뛸 수 있다. 상세 설치 흐름·검증 범위·서명 상태는 [macOS 배포 안내](docs/macos-distribution.md)를 참고한다.
