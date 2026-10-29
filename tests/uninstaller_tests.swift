import Foundation

@main
struct Tests {
    static let fm = FileManager.default
    static var passed = 0

    static func check(_ condition: @autoclosure () -> Bool, _ detail: String) throws {
        if !condition() { throw RemovalError(message: detail) }
    }
    static func reject(_ action: () throws -> Void) throws {
        do { try action() } catch { return }
        throw RemovalError(message: "Expected rejection")
    }
    static func directory(_ url: URL) throws { try fm.createDirectory(at: url, withIntermediateDirectories: true) }
    static func bundle(_ url: URL, _ id: String) throws {
        try directory(url.appendingPathComponent("Contents"))
        let data = try PropertyListSerialization.data(fromPropertyList: ["CFBundleIdentifier": id], format: .xml, options: 0)
        try data.write(to: url.appendingPathComponent("Contents/Info.plist"))
    }
    static func test(_ name: String, _ action: (URL, RemovalPlan) throws -> Void) throws {
        let root = URL(fileURLWithPath: "/private/tmp").appendingPathComponent("myorii-removal-test-\(UUID())")
        try directory(root)
        defer { try? fm.removeItem(at: root) }
        let home = root.appendingPathComponent("home")
        let apps = root.appendingPathComponent("Applications")
        try directory(home)
        try directory(apps)
        try action(root, RemovalPlan(home: home, applications: apps))
        passed += 1
        print("PASS \(name)")
    }
    static func fixture(_ plan: RemovalPlan) throws {
        try bundle(plan.applications.appendingPathComponent("Myorii.app"), "app.myorii.desktop")
        try bundle(plan.applications.appendingPathComponent("Ollama.app"), "com.electron.ollama")
        let data = plan.home.appendingPathComponent("Library/Application Support/Myorii")
        try directory(data)
        for file in ["myorii.db", "myorii.db-wal", "myorii.db-shm"] {
            try Data("fixture".utf8).write(to: data.appendingPathComponent(file))
        }
        try directory(plan.home.appendingPathComponent(".ollama/models"))
        try Data("shared-key".utf8).write(to: plan.home.appendingPathComponent(".ollama/id_ed25519"))
    }
    static func main() throws {
        try test("default removes app and preserves DB, Ollama, models and shared files") { root, plan in
            try fixture(plan)
            let targets = try plan.targets()
            try check(targets.count == 1, "default targets")
            let trash = root.appendingPathComponent("Trash")
            try directory(trash)
            let result = try plan.execute(targets) { try fm.moveItem(at: $0, to: trash.appendingPathComponent($0.lastPathComponent)) }
            try check(result.count == 1, "removed count")
            try check(plan.exists(plan.home.appendingPathComponent("Library/Application Support/Myorii")), "DB preserved")
            for file in ["myorii.db", "myorii.db-wal", "myorii.db-shm"] {
                try check(plan.exists(plan.home.appendingPathComponent("Library/Application Support/Myorii/\(file)")), "DB sidecars preserved")
            }
            try check(plan.exists(plan.applications.appendingPathComponent("Ollama.app")), "Ollama preserved")
            try check(plan.exists(plan.home.appendingPathComponent(".ollama/models")), "models preserved")
        }
        try test("selected data moves database and sidecars to trash") { root, initial in
            var plan = initial; plan.removeData = true
            try fixture(plan)
            let trash = root.appendingPathComponent("Trash"); try directory(trash)
            let targets = try plan.targets()
            try check(targets.count == 2, "app and data selected")
            _ = try plan.execute(targets) { try fm.moveItem(at: $0, to: trash.appendingPathComponent($0.lastPathComponent)) }
            for file in ["myorii.db", "myorii.db-wal", "myorii.db-shm"] {
                try check(plan.exists(trash.appendingPathComponent("Myorii/\(file)")), "database and sidecars moved")
            }
        }
        for options in [(true, false, 2), (false, true, 2), (true, true, 3)] {
            try test("optional removal \(options)") { root, initial in
                try fixture(initial)
                var plan = initial; plan.removeOllama = options.0; plan.removeModels = options.1
                let targets = try plan.targets()
                try check(targets.count == options.2, "optional targets")
                let trash = root.appendingPathComponent("Trash"); try directory(trash)
                _ = try plan.execute(targets) { try fm.moveItem(at: $0, to: trash.appendingPathComponent($0.lastPathComponent)) }
                try check(plan.exists(plan.applications.appendingPathComponent("Ollama.app")) == !options.0, "Ollama choice")
                try check(plan.exists(plan.home.appendingPathComponent(".ollama/models")) == !options.1, "model choice")
                try check(plan.exists(plan.home.appendingPathComponent(".ollama/id_ed25519")), "shared keys untouched")
            }
        }
        try test("selected data is found without an app, then empty plan") { _, initial in
            var plan = initial; plan.removeData = true
            let data = plan.home.appendingPathComponent("Library/Application Support/Myorii")
            try directory(data)
            try check(tryCount(plan) == 1, "DB found")
            try fm.removeItem(at: data)
            try check(tryCount(plan) == 0, "empty plan")
        }
        try test("user Applications and selected app deduplication") { root, initial in
            var plan = initial
            let app = plan.home.appendingPathComponent("Applications/Myorii.app")
            try bundle(app, "app.myorii.desktop")
            let other = root.appendingPathComponent("Renamed.app"); try bundle(other, "app.myorii.desktop")
            plan.extraApps = [app, other, other]
            try check(tryCount(plan) == 2, "deduplication")
        }
        try test("foreign app rejects complete plan before mutation") { _, plan in
            try fixture(plan)
            try bundle(plan.applications.appendingPathComponent("Myorii.app"), "foreign.application")
            try reject { _ = try plan.targets() }
            try check(plan.exists(plan.home.appendingPathComponent("Library/Application Support/Myorii/myorii.db")), "DB untouched")
        }
        try test("symlink model refuses to follow external data") { root, initial in
            var plan = initial; plan.removeModels = true
            let external = root.appendingPathComponent("external"); try directory(external)
            try directory(plan.home.appendingPathComponent(".ollama"))
            try fm.createSymbolicLink(at: plan.home.appendingPathComponent(".ollama/models"), withDestinationURL: external)
            try reject { _ = try plan.targets() }
            try check(plan.exists(external), "external intact")
        }
        try test("symlink parent refuses DB deletion") { root, initial in
            var plan = initial; plan.removeData = true
            let external = root.appendingPathComponent("external"); try directory(external.appendingPathComponent("Myorii"))
            try directory(plan.home.appendingPathComponent("Library"))
            try fm.createSymbolicLink(at: plan.home.appendingPathComponent("Library/Application Support"), withDestinationURL: external)
            try reject { _ = try plan.targets() }
        }
        try test("symlink app and dangling symlink rejected") { root, plan in
            let external = root.appendingPathComponent("external.app"); try bundle(external, "app.myorii.desktop")
            let link = plan.applications.appendingPathComponent("Myorii.app")
            try fm.createSymbolicLink(at: link, withDestinationURL: external)
            try reject { _ = try plan.targets() }
            try fm.removeItem(at: external)
            try reject { _ = try plan.targets() }
        }
        try test("symlink plist rejected") { root, plan in
            try fixture(plan)
            let info = plan.applications.appendingPathComponent("Myorii.app/Contents/Info.plist")
            let other = root.appendingPathComponent("info.plist")
            try fm.moveItem(at: info, to: other)
            try fm.createSymbolicLink(at: info, withDestinationURL: other)
            try reject { _ = try plan.targets() }
        }
        try test("changed target set blocks execution") { _, plan in
            let before = try plan.targets()
            try fixture(plan)
            var called = false
            try reject { _ = try plan.execute(before) { _ in called = true } }
            try check(!called, "zero mutation")
        }
        try test("injected external target blocks execution") { root, plan in
            var called = false
            try reject { _ = try plan.execute([RemovalTarget(url: root, label: "external", bundleID: nil)]) { _ in called = true } }
            try check(!called, "zero mutation")
        }
        try test("permission failure reports partial progress and preserves remaining DB") { root, initial in
            var plan = initial; plan.removeData = true
            try fixture(plan)
            let targets = try plan.targets()
            let trash = root.appendingPathComponent("Trash"); try directory(trash)
            var count = 0
            do {
                _ = try plan.execute(targets) { url in
                    count += 1
                    if count == 2 { throw CocoaError(.fileWriteNoPermission) }
                    try fm.moveItem(at: url, to: trash.appendingPathComponent(url.lastPathComponent))
                }
                throw RemovalError(message: "expected failure")
            } catch {
                try check(error.localizedDescription.contains("이미 휴지통"), "partial progress shown")
            }
            try check(plan.exists(plan.home.appendingPathComponent("Library/Application Support/Myorii/myorii.db")), "remaining DB intact")
        }
        if CommandLine.arguments.contains("--native-trash") {
            try test("native macOS Trash roundtrip with disposable fixtures only") { root, initial in
                var plan = initial; plan.removeData = true
                try fixture(plan)
                var moved: [(URL, URL)] = []
                defer {
                    for (source, destination) in moved {
                        try? fm.moveItem(at: destination, to: source)
                    }
                }
                let targets = try plan.targets()
                let completed = try plan.execute(targets) { source in
                    var destination: NSURL?
                    try fm.trashItem(at: source, resultingItemURL: &destination)
                    guard let destination else { throw RemovalError(message: "Trash destination missing") }
                    moved.append((source, destination as URL))
                }
                try check(completed.count == 2, "native removal")
                try check(!plan.exists(plan.home.appendingPathComponent("Library/Application Support/Myorii")), "native DB removed")
                for (_, destination) in moved { try check(plan.exists(destination), "recoverable item exists") }
            }
        }
        print("\(passed) isolated removal tests passed; no real apps, DB, models or Keychain entries touched.")
    }
    static func tryCount(_ plan: RemovalPlan) -> Int { (try? plan.targets().count) ?? -1 }
}
