import AppKit
import AVFoundation
import ImageIO

struct CaptionSpec: Decodable { let text: String; let audio: String }
struct SceneSpec: Decodable { let images: [String]; let captions: [CaptionSpec] }
struct Manifest: Decodable { let output: String; let scratch: String; let scenes: [SceneSpec] }
struct Clip { let image: CGImage; let text: NSAttributedString; let asset: AVURLAsset; let duration: Double; let offset: Double }
struct Scene { let clips: [Clip]; let start: Double; let frames: Int }
struct TrackMetadata: Encodable { let mediaType: String; let codecs: String; let size: String; let fps: Float }
struct BeatMetadata: Encodable { let index: Int; let text: String; let start: Double; let duration: Double; let visualStart: Double; let preview: String }
struct SceneMetadata: Encodable { let index: Int; let start: Double; let duration: Double; let beats: [BeatMetadata] }
struct MovieMetadata: Encodable { let output: String; let captions: String; let durationSeconds: Double; let tracks: [TrackMetadata]; let scenes: [SceneMetadata] }
enum VideoError: Error { case failed(String) }

@main
struct Encoder {
    static func main() async throws {
        guard CommandLine.arguments.count == 2 else { throw VideoError.failed("Usage: encode <manifest.json>") }
        let manifest = try JSONDecoder().decode(Manifest.self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        let scratch = URL(fileURLWithPath: manifest.scratch, isDirectory: true)
        try FileManager.default.createDirectory(at: scratch, withIntermediateDirectories: true)
        var scenes: [Scene] = []
        var elapsed = 0.0
        let paragraph = NSMutableParagraphStyle()
        paragraph.alignment = .center
        paragraph.lineSpacing = 3
        let shadow = NSShadow()
        shadow.shadowColor = NSColor.black.withAlphaComponent(0.8)
        shadow.shadowBlurRadius = 5
        shadow.shadowOffset = NSSize(width: 0, height: -2)
        for spec in manifest.scenes {
            guard !spec.captions.isEmpty, spec.images.count == spec.captions.count else {
                throw VideoError.failed("Each scene needs one image per spoken caption")
            }
            var clips: [Clip] = []
            var offset = 0.35
            for (imagePath, caption) in zip(spec.images, spec.captions) {
                guard let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: imagePath) as CFURL, nil),
                      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
                    throw VideoError.failed("Cannot read beat image: \(imagePath)")
                }
                let asset = AVURLAsset(url: URL(fileURLWithPath: caption.audio))
                let duration = try await asset.load(.duration).seconds
                guard duration.isFinite, duration > 0 else {
                    throw VideoError.failed("Narration contains no audio: \(caption.audio)")
                }
                let text = NSAttributedString(string: caption.text, attributes: [
                    .font: NSFont.systemFont(ofSize: 38, weight: .medium),
                    .foregroundColor: NSColor(red: 0.94, green: 0.96, blue: 0.99, alpha: 1),
                    .paragraphStyle: paragraph, .shadow: shadow
                ])
                clips.append(Clip(image: image, text: text, asset: asset, duration: duration, offset: offset))
                offset += duration + 0.15
            }
            let frames = Int(ceil((offset - 0.15 + 0.65) * 30))
            scenes.append(Scene(clips: clips, start: elapsed, frames: frames))
            elapsed += Double(frames) / 30
        }
        let silentURL = scratch.appendingPathComponent("video-silent.mp4")
        if FileManager.default.fileExists(atPath: silentURL.path) { try FileManager.default.removeItem(at: silentURL) }
        try render(scenes: scenes, total: elapsed, destination: silentURL)
        let output = URL(fileURLWithPath: manifest.output)
        if FileManager.default.fileExists(atPath: output.path) { try FileManager.default.removeItem(at: output) }
        try mux(scenes: scenes, silent: silentURL, output: output)
        try writeCaptions(scenes: scenes, output: output.deletingPathExtension().appendingPathExtension("vtt"))
        try await inspect(output: output, scenes: scenes, scratch: scratch)
    }

    static func startFFmpeg(arguments: [String], input: Pipe?) throws -> Process {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = [ProcessInfo.processInfo.environment["FFMPEG"] ?? "ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + arguments
        process.standardInput = input ?? FileHandle.nullDevice
        try process.run()
        return process
    }

    static func finishFFmpeg(_ process: Process) throws {
        process.waitUntilExit()
        guard process.terminationStatus == 0 else {
            throw VideoError.failed("FFmpeg exited with status \(process.terminationStatus)")
        }
    }

    static func render(scenes: [Scene], total: Double, destination: URL) throws {
        guard let context = CGContext(data: nil, width: 1920, height: 1080,
            bitsPerComponent: 8, bytesPerRow: 1920 * 4, space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue),
            let pixels = context.data else { throw VideoError.failed("Cannot create frame drawing context") }
        let input = Pipe()
        let encoder = try startFFmpeg(arguments: ["-f", "rawvideo", "-pixel_format", "bgra",
            "-video_size", "1920x1080", "-framerate", "30", "-i", "pipe:0", "-an",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", destination.path], input: input)
        defer { if encoder.isRunning { encoder.terminate() } }
        for (sceneIndex, scene) in scenes.enumerated() {
            for localFrame in 0..<scene.frames {
                try autoreleasepool {
                    let time = Double(localFrame) / 30
                    let beatIndex = scene.clips.lastIndex(where: { time >= $0.offset }) ?? 0
                    let clip = scene.clips[beatIndex]
                    let visualStart = beatIndex == 0 ? 0 : clip.offset
                    let dissolve = min(1, (time - visualStart) / 0.2)
                    let previousImage = beatIndex > 0 ? scene.clips[beatIndex - 1].image
                        : sceneIndex > 0 ? scenes[sceneIndex - 1].clips.last?.image : nil
                    let frame = CGRect(x: 0, y: 0, width: 1920, height: 1080)
                    context.setFillColor(CGColor(red: 0.031, green: 0.055, blue: 0.094, alpha: 1))
                    context.fill(frame)
                    if dissolve < 1, let previousImage { context.draw(previousImage, in: frame) }
                    context.saveGState()
                    context.setAlpha(dissolve)
                    context.draw(clip.image, in: frame)
                    context.restoreGState()
                    if time >= clip.offset && time < clip.offset + clip.duration {
                        NSGraphicsContext.saveGraphicsState()
                        NSGraphicsContext.current = NSGraphicsContext(cgContext: context, flipped: false)
                        let bounds = clip.text.boundingRect(with: NSSize(width: 1720, height: 120), options: [.usesLineFragmentOrigin, .usesFontLeading])
                        clip.text.draw(with: CGRect(x: 100, y: 83 + (110 - bounds.height) / 2, width: 1720, height: bounds.height + 2), options: [.usesLineFragmentOrigin, .usesFontLeading])
                        NSGraphicsContext.restoreGraphicsState()
                    }
                    context.setFillColor(CGColor(red: 139.0 / 255, green: 92.0 / 255, blue: 246.0 / 255, alpha: 1))
                    context.fill(CGRect(x: 0, y: 0, width: 1920 * (scene.start + time) / total, height: 5))
                    context.flush()
                    try input.fileHandleForWriting.write(contentsOf: Data(bytesNoCopy: pixels, count: 1920 * 1080 * 4, deallocator: .none))
                }
            }
            print("Rendered scene \(sceneIndex + 1)/\(scenes.count)")
            fflush(stdout)
        }
        try input.fileHandleForWriting.close()
        try finishFFmpeg(encoder)
    }

    static func mux(scenes: [Scene], silent: URL, output: URL) throws {
        var arguments = ["-i", silent.path]
        var filters: [String] = []
        var audioLabels: [String] = []
        for scene in scenes {
            for clip in scene.clips {
                let index = audioLabels.count + 1
                let delay = Int(((scene.start + clip.offset) * 1000).rounded())
                arguments += ["-i", clip.asset.url.path]
                filters.append("[\(index):a]adelay=\(delay):all=1[a\(index)]")
                audioLabels.append("[a\(index)]")
            }
        }
        let duration = scenes.reduce(0.0) { $0 + Double($1.frames) / 30 }
        filters.append("\(audioLabels.joined())amix=inputs=\(audioLabels.count):duration=longest:dropout_transition=0:normalize=0,apad,atrim=duration=\(duration)[narration]")
        arguments += ["-filter_complex", filters.joined(separator: ";"), "-map", "0:v:0", "-map", "[narration]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", output.path]
        try finishFFmpeg(startFFmpeg(arguments: arguments, input: nil))
    }

    static func writeCaptions(scenes: [Scene], output: URL) throws {
        var cues = ["WEBVTT\n"]
        for (sceneIndex, scene) in scenes.enumerated() {
            for (beatIndex, clip) in scene.clips.enumerated() {
                let start = scene.start + clip.offset
                cues.append("\(sceneIndex + 1)-\(beatIndex + 1)\n\(timestamp(start)) --> \(timestamp(start + clip.duration))\n\(clip.text.string)\n")
            }
        }
        try cues.joined(separator: "\n").write(to: output, atomically: true, encoding: .utf8)
    }

    static func timestamp(_ seconds: Double) -> String {
        let milliseconds = Int((seconds * 1000).rounded())
        return String(format: "%02d:%02d:%02d.%03d", milliseconds / 3_600_000,
            milliseconds / 60_000 % 60, milliseconds / 1000 % 60, milliseconds % 1000)
    }

    static func inspect(output: URL, scenes: [Scene], scratch: URL) async throws {
        let asset = AVURLAsset(url: output)
        let duration = try await asset.load(.duration).seconds
        var tracks: [TrackMetadata] = []
        for track in try await asset.load(.tracks) {
            let descriptions = try await track.load(.formatDescriptions)
            let codecs = descriptions.map { description in
                let code = CMFormatDescriptionGetMediaSubType(description)
                return String(bytes: [UInt8((code >> 24) & 255), UInt8((code >> 16) & 255), UInt8((code >> 8) & 255), UInt8(code & 255)], encoding: .ascii) ?? "unknown"
            }
            let size = try await track.load(.naturalSize)
            let fps = try await track.load(.nominalFrameRate)
            tracks.append(TrackMetadata(mediaType: track.mediaType.rawValue, codecs: codecs.joined(separator: ","), size: "\(Int(size.width))x\(Int(size.height))", fps: fps))
        }
        var sceneMetadata: [SceneMetadata] = []
        for (sceneIndex, scene) in scenes.enumerated() {
            var beats: [BeatMetadata] = []
            for (beatIndex, clip) in scene.clips.enumerated() {
                let start = scene.start + clip.offset
                let previewTime = start + min(1.5, clip.duration / 2)
                let name = String(format: "preview-%02d-%02d.png", sceneIndex + 1, beatIndex + 1)
                let url = scratch.appendingPathComponent(name)
                try finishFFmpeg(startFFmpeg(arguments: ["-ss", "\(previewTime)", "-i", output.path,
                    "-frames:v", "1", "-update", "1", url.path], input: nil))
                beats.append(BeatMetadata(index: beatIndex + 1, text: clip.text.string, start: start, duration: clip.duration,
                    visualStart: beatIndex == 0 ? scene.start : start, preview: name))
            }
            sceneMetadata.append(SceneMetadata(index: sceneIndex + 1, start: scene.start, duration: Double(scene.frames) / 30, beats: beats))
        }
        let metadata = MovieMetadata(output: output.path, captions: output.deletingPathExtension().appendingPathExtension("vtt").path,
            durationSeconds: duration, tracks: tracks, scenes: sceneMetadata)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(metadata)
        try data.write(to: scratch.appendingPathComponent("metadata.json"))
        print(String(decoding: data, as: UTF8.self))
    }
}
