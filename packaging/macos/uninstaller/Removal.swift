import Foundation

struct RemovalError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

struct RemovalTarget {
    let url: URL
    let label: String
    let bundleID: String?
}

struct RemovalPlan {
    let home: URL
    let applications: URL
    var extraApps: [URL] = []
    var removeOllama = false
    var removeModels = false
    let fm = FileManager.default

    func exists(_ url: URL) -> Bool {
        (try? fm.attributesOfItem(atPath: url.path)) != nil
    }

    // Never follow a symlink, including a parent directory, to unrelated data.
    func validatePath(_ url: URL) throws {
        var current = url
        while current.path != "/" {
            if let attrs = try? fm.attributesOfItem(atPath: current.path),
               attrs[.type] as? FileAttributeType == .typeSymbolicLink {
                throw RemovalError(message: "심볼릭 링크는 자동 제거하지 않습니다: \(current.path)")
            }
            current.deleteLastPathComponent()
        }
    }

    func validate(_ target: RemovalTarget) throws {
        try validatePath(target.url)
        if let identifier = target.bundleID {
            let info = target.url.appendingPathComponent("Contents/Info.plist")
            try validatePath(info)
            guard let data = try? Data(contentsOf: info),
                  let plist = try? PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any],
                  plist["CFBundleIdentifier"] as? String == identifier else {
                throw RemovalError(message: "앱의 신원을 확인하지 못했습니다. 제거하지 않습니다: \(target.url.path)")
            }
        }
    }

    func targets() throws -> [RemovalTarget] {
        let userApps = home.appendingPathComponent("Applications")
        var result: [RemovalTarget] = []
        for url in [applications.appendingPathComponent("Myorii.app"), userApps.appendingPathComponent("Myorii.app")] + extraApps {
            if exists(url), !result.contains(where: { $0.url.standardizedFileURL.path == url.standardizedFileURL.path }) {
                result.append(RemovalTarget(url: url, label: "묘리 앱", bundleID: "app.myorii.desktop"))
            }
        }
        if removeOllama {
            for base in [applications, userApps] {
                let url = base.appendingPathComponent("Ollama.app")
                if exists(url) { result.append(RemovalTarget(url: url, label: "Ollama 앱", bundleID: "com.electron.ollama")) }
            }
        }
        if removeModels {
            let url = home.appendingPathComponent(".ollama/models")
            if exists(url) { result.append(RemovalTarget(url: url, label: "Ollama 전체 모델", bundleID: nil)) }
        }
        let database = home.appendingPathComponent("Library/Application Support/Myorii")
        if exists(database) { result.append(RemovalTarget(url: database, label: "묘리 데이터 (대화·할일·메모·설정)", bundleID: nil)) }
        for (path, label) in [
            ("Library/Caches/app.myorii.desktop", "묘리 캐시"),
            ("Library/Caches/Myorii", "묘리 캐시"),
            ("Library/Preferences/app.myorii.desktop.plist", "묘리 환경설정"),
            ("Library/Saved Application State/app.myorii.desktop.savedState", "묘리 저장된 창 상태")
        ] {
            let url = home.appendingPathComponent(path)
            if exists(url) { result.append(RemovalTarget(url: url, label: label, bundleID: nil)) }
        }
        // Validate the entire plan before the first mutation.
        for target in result { try validate(target) }
        return result
    }

    func execute(_ targets: [RemovalTarget], trash: (URL) throws -> Void) throws -> [String] {
        // Rebuild the allowlist at execution time, not from caller-provided paths.
        let expected = try self.targets()
        guard targets.map({ $0.url.standardizedFileURL.path }) == expected.map({ $0.url.standardizedFileURL.path }) else {
            throw RemovalError(message: "제거 대상이 변경되었습니다. 다시 확인해주세요.")
        }
        var completed: [String] = []
        for target in targets {
            do {
                try validate(target)
                try trash(target.url)
                completed.append(target.url.path)
            } catch {
                let report = completed.isEmpty ? "아직 옮긴 파일은 없습니다." : "이미 휴지통으로 옮긴 항목:\n" + completed.joined(separator: "\n")
                throw RemovalError(message: "제거를 완료하지 못했습니다: \(target.url.path)\n\(error.localizedDescription)\n\n\(report)\n권한과 실행 상태를 확인한 뒤 다시 시도해주세요.")
            }
        }
        return completed
    }
}
