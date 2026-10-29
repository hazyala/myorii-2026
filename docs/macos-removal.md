# 묘리 제거 도구

DMG에 포함된 `묘리 제거.app`은 묘리 앱을 제거하고 현재 Mac 계정의 로컬 데이터 삭제 여부를 선택할 수 있다. 기본적으로 데이터는 보존된다. 실행 중인 묘리는 먼저 설정의 **앱 종료**로 종료한다.

## 사용자 동작

1. 배포 DMG를 열고 **묘리 제거**를 실행한다. 처음 실행이 차단되면 설치 안내 PDF의 보안 승인 절차를 따른다.
2. 묘리 데이터, Ollama 앱과 기본 위치의 전체 모델을 지울지 각각 선택한다. 세 선택은 기본적으로 꺼져 있다. 선택했다면 Ollama와 모델을 사용하는 작업도 종료한다.
3. **제거 대상 확인**에서 실제 경로를 확인한다. 다른 위치의 묘리 앱은 **다른 위치의 묘리 선택…**으로 추가한다.
4. **제거**를 누르면 앱·데이터·선택한 모델을 휴지통으로 옮긴다. 완전 삭제와 공간 확보는 사용자가 휴지통을 비워 수행한다. 취소하면 변경하지 않는다.

묘리 데이터 제거를 선택하면 파일을 휴지통으로 옮긴 뒤 묘리가 저장한 OpenAI·Gemini·Anthropic API 키도 키체인에서 삭제한다. 선택하지 않으면 키도 보존한다. 키체인 삭제는 되돌릴 수 없으며, 제공자 서버의 API 키를 폐기하는 것은 아니다. OS가 키체인 접근을 요청할 수 있다. 실패한 키 항목은 화면에서 안내한다.

## 대상과 제외 범위

| 항목 | 처리 |
|---|---|
| `/Applications/Myorii.app`, `~/Applications/Myorii.app` | 설치된 묘리 앱 제거 |
| 사용자가 추가 선택한 묘리 앱 | 번들 ID 검증 후 제거 |
| `~/Library/Application Support/Myorii` | 데이터 선택 시 DB와 WAL·SHM 등 전체 데이터 폴더 제거 |
| 키체인 서비스 `Myorii API` | 데이터 선택 시 `openai`, `gemini`, `anthropic` 계정만 삭제 |
| `/Applications/Ollama.app`, `~/Applications/Ollama.app` | Ollama 선택 시 제거 |
| `~/.ollama/models` | 모델 선택 시 전체 모델 제거 |
| Ollama 인증 키, 설정, 기타 지원 파일 및 CLI 링크 | 보존 |
| 다른 Mac 계정 데이터, Homebrew/별도 CLI 설치, 별도 모델 저장소 | 자동 제거하지 않음 |
| 원본 첨부 문서와 사용자가 내보낸 파일 | 보존 |

`OLLAMA_MODELS`가 기본 경로와 다른 값으로 설정되어 있으면 모델 자동 제거를 중단하고 안내한다. 중단된 서버가 별도 셸 설정으로 사용했던 경로 등은 자동으로 알아낼 수 없다. 해당 설치 방식의 안내에 따라 별도로 정리해야 한다.

## 구현과 보호 장치

- `packaging/macos/uninstaller/Removal.swift`: 경로 구성, 앱 신원 확인, 실행 직전 재검증, 휴지통 이동 처리. 모든 대상을 검증한 뒤 이동을 시작한다.
- `packaging/macos/uninstaller/main.swift`: AppKit 선택·최종 확인 화면, 묘리/개발 실행/Ollama 실행 중 차단, 키체인 정리.
- 대상 또는 상위 경로가 심볼릭 링크면 거절한다. 실제 데이터 폴더 안의 링크는 폴더와 함께 이동하며 연결된 외부 원본은 건드리지 않는다.
- 앱 이름만 신뢰하지 않고 `app.myorii.desktop` 또는 `com.electron.ollama` 번들 ID를 검사한다.
- 권한 변경, 관리자 암호 수집, 강제 종료, 휴지통 비우기를 수행하지 않는다.
- 여러 파일 이동 중 실패하면 이미 이동한 항목과 실패 경로를 표시한다. 전체 완료로 안내하지 않는다. 파일 이동이 실패한 경우 키체인 정리는 시작하지 않는다.
- 별도 Python 설치 없이 실행되는 Swift 네이티브 앱이며 최소 macOS 14를 대상으로 빌드한다. Developer ID 서명·공증은 아직 없다.

## 검증

격리된 임시 홈과 가짜 앱·DB·모델에서 기본 보존, 각 선택 조합, 누락된 앱, 중복 경로, 잘못된 번들, 심볼릭 링크, 대상 변경, 외부 경로 삽입, 일부 권한 오류를 검사한다. 실제 사용자 데이터나 API 키를 테스트 대상으로 삼지 않는다.

```sh
swiftc -module-cache-path /tmp/myorii-swift-cache -target arm64-apple-macos14.0 \
  packaging/macos/uninstaller/Removal.swift tests/uninstaller_tests.swift \
  -o /tmp/MyoriiRemovalTests
/tmp/MyoriiRemovalTests
```

macOS 휴지통으로 임시 파일을 실제 이동했다가 회수하는 검사는 `/tmp/MyoriiRemovalTests --native-trash`로 수행한다. 2026-10-15에 기본 14개와 휴지통 왕복 1개, 총 15개가 통과했다. 실제 화면에서는 선택이 꺼진 상태, 실행 중 앱 제거 차단, 취소를 확인했다. 다른 계정의 관리자 소유 설치와 Gatekeeper·키체인 승인 화면은 별도 Mac에서 추가 검증이 필요하다.

