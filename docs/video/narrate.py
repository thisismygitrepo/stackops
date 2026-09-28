# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "espeakng-loader>=0.2.4",
#     "kokoro-onnx>=0.6.1",
#     "soundfile>=0.14.0",
# ]
# ///
import json
import sys
from pathlib import Path
from shutil import copytree
from typing import TypedDict, cast

import espeakng_loader
import soundfile as sf
from kokoro_onnx import Kokoro
from kokoro_onnx.config import EspeakConfig


class Caption(TypedDict):
    text: str
    audio: str


class Scene(TypedDict):
    images: list[str]
    captions: list[Caption]


class Manifest(TypedDict):
    output: str
    scratch: str
    scenes: list[Scene]


def main() -> None:
    manifest_path = Path(sys.argv[1])
    manifest = cast(Manifest, json.loads(manifest_path.read_text(encoding="utf-8")))
    scratch = Path(manifest["scratch"])
    espeak_data = scratch / "espeak-ng-data"
    copytree(espeakng_loader.get_data_path(), espeak_data, dirs_exist_ok=True)
    narrator = Kokoro(
        str(scratch / "kokoro-v1.0.onnx"),
        str(scratch / "voices-v1.0.bin"),
        espeak_config=EspeakConfig(lib_path=espeakng_loader.get_library_path(), data_path=str(espeak_data)),
    )
    for scene_index, scene in enumerate(manifest["scenes"], start=1):
        for caption_index, caption in enumerate(scene["captions"], start=1):
            spoken = caption["text"].replace("StackOps", "Stack Ops").replace("OS-agnostic", "O S agnostic").replace("CLI", "C L I").replace("MCP", "M C P").replace("SSH", "S S H").replace("tmux", "tee mux").replace("uv", "U V")
            samples, sample_rate = narrator.create(spoken, voice="af_sarah", speed=0.95, lang="en-us")
            if len(samples) < sample_rate:
                raise RuntimeError(f"""Empty or truncated narration for scene {scene_index}, beat {caption_index}""")
            sf.write(caption["audio"], samples, sample_rate, subtype="PCM_16")
            print(f"""Narrated scene {scene_index}, beat {caption_index}: {len(samples) / sample_rate:.1f}s""", flush=True)


if __name__ == "__main__":
    main()
