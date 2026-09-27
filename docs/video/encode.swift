import AppKit
import AVFoundation
import ImageIO

struct CaptionSpec: Decodable { let text: String; let audio: String }
struct SceneSpec: Decodable { let image: String; let captions: [CaptionSpec] }
struct Manifest: Decodable { let output: String; let scratch: String; let scenes: [SceneSpec] }
struct Clip { let text: NSAttributedString; let asset: AVURLAsset; let duration: Double; let offset: Double }
struct Scene { let image: CGImage; let clips: [Clip]; let start: Double; let frames: Int }
struct TrackMetadata: Encodable { let mediaType: String; let codecs: String; let size: String; let fps: Float }
struct SceneMetadata: Encodable { let index: Int; let start: Double; let duration: Double }
struct MovieMetadata: Encodable { let output: String; let durationSeconds: Double; let tracks: [TrackMetadata]; let scenes: [SceneMetadata] }
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
            guard let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: spec.image) as CFURL, nil),
                  let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
                throw VideoError.failed("Cannot read scene image: \(spec.image)")
            }
            var clips: [Clip] = []
            var offset = 0.35
            for caption in spec.captions {
                let asset = AVURLAsset(url: URL(fileURLWithPath: caption.audio))
                let duration = try await asset.load(.duration).seconds
                let text = NSAttributedString(string: caption.text, attributes: [
                    .font: NSFont.systemFont(ofSize: 38, weight: .medium),
                    .foregroundColor: NSColor(red: 0.94, green: 0.96, blue: 0.99, alpha: 1),
                    .paragraphStyle: paragraph, .shadow: shadow
                ])
                clips.append(Clip(text: text, asset: asset, duration: duration, offset: offset))
                offset += duration + 0.15
            }
            let frames = Int(ceil((offset - 0.15 + 0.65) * 30))
            scenes.append(Scene(image: image, clips: clips, start: elapsed, frames: frames))
            elapsed += Double(frames) / 30
        }
        let silentURL = scratch.appendingPathComponent("video-silent.mp4")
        if FileManager.default.fileExists(atPath: silentURL.path) { try FileManager.default.removeItem(at: silentURL) }
        try await render(scenes: scenes, total: elapsed, destination: silentURL)
        let output = URL(fileURLWithPath: manifest.output)
        if FileManager.default.fileExists(atPath: output.path) { try FileManager.default.removeItem(at: output) }
        try await mux(scenes: scenes, silent: silentURL, output: output)
        try await inspect(output: output, scenes: scenes, scratch: scratch)
    }

    static func render(scenes: [Scene], total: Double, destination: URL) async throws {
        let writer = try AVAssetWriter(outputURL: destination, fileType: .mp4)
        let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
            AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: 1920, AVVideoHeightKey: 1080,
            AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 7_000_000,
                AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
                AVVideoExpectedSourceFrameRateKey: 30, AVVideoMaxKeyFrameIntervalKey: 60]
        ])
        let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
            kCVPixelBufferWidthKey as String: 1920, kCVPixelBufferHeightKey as String: 1080,
            kCVPixelBufferCGImageCompatibilityKey as String: true,
            kCVPixelBufferCGBitmapContextCompatibilityKey as String: true
        ])
        writer.add(input)
        guard writer.startWriting() else { throw writer.error ?? VideoError.failed("Video writer failed to start") }
        writer.startSession(atSourceTime: .zero)
        guard let pool = adaptor.pixelBufferPool else { throw VideoError.failed("No pixel buffer pool") }
        var frameNumber: Int64 = 0
        for (sceneIndex, scene) in scenes.enumerated() {
            for localFrame in 0..<scene.frames {
                while !input.isReadyForMoreMediaData {
                    if writer.status == .failed { throw writer.error ?? VideoError.failed("Video encoding failed") }
                    try await Task.sleep(nanoseconds: 2_000_000)
                }
                try autoreleasepool {
                    var buffer: CVPixelBuffer?
                    guard CVPixelBufferPoolCreatePixelBuffer(nil, pool, &buffer) == kCVReturnSuccess,
                          let buffer else { throw VideoError.failed("Cannot allocate video frame") }
                    CVPixelBufferLockBaseAddress(buffer, [])
                    defer { CVPixelBufferUnlockBaseAddress(buffer, []) }
                    guard let context = CGContext(data: CVPixelBufferGetBaseAddress(buffer), width: 1920, height: 1080,
                        bitsPerComponent: 8, bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
                        space: CGColorSpaceCreateDeviceRGB(),
                        bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)
                    else { throw VideoError.failed("Cannot create frame drawing context") }
                    let time = Double(localFrame) / 30
                    let duration = Double(scene.frames) / 30
                    let fade = min(1, min(time / 0.4, (duration - time) / 0.4))
                    context.setFillColor(CGColor(red: 0.031, green: 0.055, blue: 0.094, alpha: 1))
                    context.fill(CGRect(x: 0, y: 0, width: 1920, height: 1080))
                    context.saveGState()
                    context.setAlpha(fade)
                    let zoom = 1 + 0.008 * time / duration
                    context.draw(scene.image, in: CGRect(x: -960 * (zoom - 1), y: -540 * (zoom - 1), width: 1920 * zoom, height: 1080 * zoom))
                    context.restoreGState()
                    if let clip = scene.clips.first(where: { time >= $0.offset && time < $0.offset + $0.duration + 0.15 }) {
                        NSGraphicsContext.saveGraphicsState()
                        NSGraphicsContext.current = NSGraphicsContext(cgContext: context, flipped: false)
                        let bounds = clip.text.boundingRect(with: NSSize(width: 1720, height: 120), options: [.usesLineFragmentOrigin, .usesFontLeading])
                        clip.text.draw(with: CGRect(x: 100, y: 83 + (110 - bounds.height) / 2, width: 1720, height: bounds.height + 2), options: [.usesLineFragmentOrigin, .usesFontLeading])
                        NSGraphicsContext.restoreGraphicsState()
                    }
                    context.setFillColor(CGColor(red: 0.25, green: 0.84, blue: 0.80, alpha: 0.85))
                    context.fill(CGRect(x: 0, y: 0, width: 1920 * (scene.start + time) / total, height: 5))
                    guard adaptor.append(buffer, withPresentationTime: CMTime(value: frameNumber, timescale: 30)) else {
                        throw writer.error ?? VideoError.failed("Cannot append video frame")
                    }
                }
                frameNumber += 1
            }
            print("Rendered scene \(sceneIndex + 1)/\(scenes.count)")
            fflush(stdout)
        }
        input.markAsFinished()
        await writer.finishWriting()
        guard writer.status == .completed else { throw writer.error ?? VideoError.failed("Video writing incomplete") }
    }

    static func mux(scenes: [Scene], silent: URL, output: URL) async throws {
        let composition = AVMutableComposition()
        let videoAsset = AVURLAsset(url: silent)
        guard let sourceVideo = try await videoAsset.loadTracks(withMediaType: .video).first,
              let video = composition.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid),
              let audio = composition.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)
        else { throw VideoError.failed("Cannot create movie composition") }
        let duration = try await videoAsset.load(.duration)
        try video.insertTimeRange(CMTimeRange(start: .zero, duration: duration), of: sourceVideo, at: .zero)
        for scene in scenes {
            for clip in scene.clips {
                guard let source = try await clip.asset.loadTracks(withMediaType: .audio).first else {
                    throw VideoError.failed("Narration has no audio track")
                }
                try audio.insertTimeRange(CMTimeRange(start: .zero, duration: CMTime(seconds: clip.duration, preferredTimescale: 60000)), of: source,
                    at: CMTime(seconds: scene.start + clip.offset, preferredTimescale: 60000))
            }
        }
        guard let exporter = AVAssetExportSession(asset: composition, presetName: AVAssetExportPreset1920x1080) else {
            throw VideoError.failed("Cannot create MP4 exporter")
        }
        exporter.shouldOptimizeForNetworkUse = true
        try await exporter.export(to: output, as: .mp4)
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
        let generator = AVAssetImageGenerator(asset: asset)
        generator.appliesPreferredTrackTransform = true
        generator.requestedTimeToleranceBefore = .zero
        generator.requestedTimeToleranceAfter = .zero
        for (index, scene) in scenes.enumerated() {
            let previewTime = scene.start + (scene.clips.first.map { $0.offset + min(1.5, $0.duration / 2) } ?? 0.5)
            let (frame, _) = try await generator.image(at: CMTime(seconds: previewTime, preferredTimescale: 60000))
            let url = scratch.appendingPathComponent(String(format: "preview-%02d.png", index + 1))
            guard let destination = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) else {
                throw VideoError.failed("Cannot create preview PNG")
            }
            CGImageDestinationAddImage(destination, frame, nil)
            guard CGImageDestinationFinalize(destination) else { throw VideoError.failed("Cannot write preview PNG") }
        }
        let metadata = MovieMetadata(output: output.path, durationSeconds: duration, tracks: tracks,
            scenes: scenes.enumerated().map { SceneMetadata(index: $0.offset + 1, start: $0.element.start, duration: Double($0.element.frames) / 30) })
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(metadata)
        try data.write(to: scratch.appendingPathComponent("metadata.json"))
        print(String(decoding: data, as: UTF8.self))
    }
}
