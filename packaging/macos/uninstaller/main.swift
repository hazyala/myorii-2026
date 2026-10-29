import AppKit
import Security
import Darwin

func message(_ title: String, _ detail: String) {
    let alert = NSAlert()
    alert.messageText = title
    alert.informativeText = detail
    alert.addButton(withTitle: "확인")
    alert.runModal()
}

func command(_ executable: String, _ args: [String]) throws -> (Int32, String) {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: executable)
    process.arguments = args
    let output = Pipe()
    process.standardOutput = output
    process.standardError = FileHandle.nullDevice
    try process.run()
    let data = output.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()
    return (process.terminationStatus, String(decoding: data, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines))
}

func checkStopped(ollama: Bool) throws {
    if NSWorkspace.shared.runningApplications.contains(where: { $0.bundleIdentifier == "app.myorii.desktop" }) {
        throw RemovalError(message: "먼저 묘리 설정에서 ‘앱 종료’를 눌러주세요. 창을 닫는 것만으로는 종료되지 않습니다.")
    }
    let lock = FileManager.default.temporaryDirectory.appendingPathComponent("myorii.lock")
    if let value = try? String(contentsOf: lock, encoding: .utf8),
       let pid = Int32(value.components(separatedBy: .newlines).first ?? ""), pid > 0,
       (kill(pid, 0) == 0 || errno == EPERM),
       let name = value.components(separatedBy: .newlines).dropFirst().first,
       !name.isEmpty,
       let processName = try? command("/bin/ps", ["-p", String(pid), "-o", "comm="]).1,
       URL(fileURLWithPath: processName).lastPathComponent == URL(fileURLWithPath: name).lastPathComponent {
        throw RemovalError(message: "묘리 프로세스가 아직 실행 중입니다. 개발 실행을 포함해 묘리를 종료한 뒤 다시 시도해주세요.")
    }
    if ollama {
        if NSWorkspace.shared.runningApplications.contains(where: { $0.bundleIdentifier == "com.electron.ollama" }) {
            throw RemovalError(message: "Ollama 메뉴에서 Quit Ollama를 선택한 뒤 다시 시도해주세요.")
        }
        let status = try command("/usr/bin/pgrep", ["-x", "ollama"]).0
        guard status == 1 else {
            throw RemovalError(message: "Ollama 서버가 실행 중이거나 상태를 확인할 수 없습니다. 다른 앱의 AI 작업과 Ollama 서버를 종료한 뒤 다시 시도해주세요.")
        }
    }
}

func customModels() throws -> String? {
    let environment = ProcessInfo.processInfo.environment["OLLAMA_MODELS"] ?? ""
    let (status, launched) = try command("/bin/launchctl", ["getenv", "OLLAMA_MODELS"])
    guard status == 0 || status == 1 else {
        throw RemovalError(message: "모델 저장 위치 설정을 확인할 수 없습니다.")
    }
    let path = environment.isEmpty ? launched : environment
    return path.isEmpty ? nil : path
}

func removeCredentials() -> [String] {
    var failures: [String] = []
    for provider in ["openai", "gemini", "anthropic"] {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
                                   kSecAttrService as String: "Myorii API",
                                   kSecAttrAccount as String: provider]
        let status = SecItemDelete(query as CFDictionary)
        if status != errSecSuccess && status != errSecItemNotFound {
            failures.append("\(provider): \(status)")
        }
    }
    return failures
}

// Read-only smoke check: no UI, no credentials, no file mutations.
if CommandLine.arguments.contains("--check-package") {
    print("Myorii Uninstaller: ready (macOS 14+, default optional removals: off)")
    exit(0)
}
let app = NSApplication.shared
app.setActivationPolicy(.regular)
app.finishLaunching()
app.activate(ignoringOtherApps: true)
let home = FileManager.default.homeDirectoryForCurrentUser
var plan = RemovalPlan(home: home, applications: URL(fileURLWithPath: "/Applications"))
let data = NSButton(checkboxWithTitle: "묘리 데이터도 제거 (대화·할일·메모·설정)", target: nil, action: nil)
let ollama = NSButton(checkboxWithTitle: "Ollama 앱도 제거", target: nil, action: nil)
let models = NSButton(checkboxWithTitle: "기본 위치의 Ollama 전체 모델도 제거", target: nil, action: nil)
data.state = .off
ollama.state = .off
models.state = .off

while true {
    let alert = NSAlert()
    alert.messageText = "묘리 제거"
    alert.informativeText = "묘리 앱을 휴지통으로 옮깁니다. 대화·할일·메모·설정과 저장된 API 키는 데이터 제거를 선택한 경우에만 삭제합니다.\n\nOllama와 모델은 다른 앱에서도 사용할 수 있습니다. 함께 지울 항목만 선택하세요. 기본 모델 위치는 ~/.ollama/models입니다.\n\n먼저 묘리를 종료해주세요. Ollama 항목을 선택했다면 Ollama도 종료해주세요."
    let stack = NSStackView(views: [data, ollama, models])
    stack.orientation = .vertical
    stack.alignment = .leading
    stack.spacing = 12
    stack.frame = NSRect(x: 0, y: 0, width: 390, height: 92)
    alert.accessoryView = stack
    alert.addButton(withTitle: "제거 대상 확인")
    alert.addButton(withTitle: "취소")
    alert.addButton(withTitle: "다른 위치의 묘리 선택…")
    let response = alert.runModal()
    if response == .alertSecondButtonReturn { break }
    if response == .alertThirdButtonReturn {
        let panel = NSOpenPanel()
        panel.title = "제거할 Myorii.app 선택"
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowedContentTypes = [.applicationBundle]
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let selected = panel.url {
            do {
                try plan.validate(RemovalTarget(url: selected, label: "묘리 앱", bundleID: "app.myorii.desktop"))
                if !plan.extraApps.contains(selected) { plan.extraApps.append(selected) }
            } catch { message("앱 확인 실패", error.localizedDescription) }
        }
        continue
    }
    plan.removeData = data.state == .on
    plan.removeOllama = ollama.state == .on
    plan.removeModels = models.state == .on
    do {
        try checkStopped(ollama: plan.removeOllama || plan.removeModels)
        if plan.removeModels, let custom = try customModels(),
           URL(fileURLWithPath: custom).standardizedFileURL.path != home.appendingPathComponent(".ollama/models").standardizedFileURL.path {
            throw RemovalError(message: "별도 모델 저장 위치가 설정되어 있습니다: \(custom)\n이 도구는 기본 위치만 처리합니다. 모델 선택을 해제하고 별도 위치는 직접 확인해주세요.")
        }
        let targets = try plan.targets()
        let confirmation = NSAlert()
        confirmation.alertStyle = .warning
        confirmation.messageText = "다음 항목을 제거할까요?"
        confirmation.informativeText = (targets.isEmpty ? "선택한 제거 대상이 없습니다. 다른 위치의 앱은 직접 선택해주세요." : targets.map { "• \($0.label)\n\($0.url.path)" }.joined(separator: "\n\n")) + "\n\n저장된 API 키는 데이터 제거를 선택한 경우에만 삭제됩니다. 키체인 확인창이 나오면 본인이 실행한 제거 작업인지 확인해주세요.\n\n앱·DB·모델은 휴지통을 비우기 전까지 복구할 수 있습니다. 저장된 API 키 삭제는 되돌릴 수 없습니다."
        confirmation.addButton(withTitle: "제거")
        confirmation.addButton(withTitle: "취소")
        confirmation.buttons[0].keyEquivalent = ""
        confirmation.buttons[1].keyEquivalent = "\r"
        guard confirmation.runModal() == .alertFirstButtonReturn else { continue }
        try checkStopped(ollama: plan.removeOllama || plan.removeModels)
        let removed = try plan.execute(targets) { url in
            var trashed: NSURL?
            try FileManager.default.trashItem(at: url, resultingItemURL: &trashed)
        }
        let keyErrors = plan.removeData ? removeCredentials() : []
        if !keyErrors.isEmpty {
            message("파일 제거 완료 · API 키 확인 필요", "선택한 파일 \(removed.count)개를 휴지통으로 옮겼습니다.\n키체인에서 일부 API 키를 삭제하지 못했습니다: \(keyErrors.joined(separator: ", "))\n‘키체인 접근’에서 ‘Myorii API’를 검색해 남은 항목을 확인해주세요.")
        } else {
            message("묘리 제거 완료", "선택한 파일 \(removed.count)개를 휴지통으로 옮겼습니다. \(plan.removeData ? "묘리 API 키도 정리했습니다." : "묘리 데이터와 API 키는 보존했습니다.")\n완전히 삭제하고 공간을 확보하려면 휴지통을 비워주세요.\n\n다른 Mac 계정의 데이터, 별도 모델 경로, Homebrew 등으로 설치한 Ollama는 자동으로 제거하지 않습니다.")
        }
        break
    } catch { message("제거하지 못했습니다", error.localizedDescription) }
}
