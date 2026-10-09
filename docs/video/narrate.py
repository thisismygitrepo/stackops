# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "openai>=3.28.0",
# ]
# ///
import base64
import json
import re
import sys
import wave
from io import BytesIO
from pathlib import Path
from typing import TypedDict, cast

from openai import OpenAI

from constants import NARRATION_INSTRUCTIONS, NARRATION_MODEL, NARRATION_VOICE


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
    with OpenAI(max_retries=0) as narrator:
        for scene_index, scene in enumerate(manifest["scenes"], start=1):
            for caption_index, caption in enumerate(scene["captions"], start=1):
                completion = narrator.chat.completions.create(
                    model=NARRATION_MODEL,
                    modalities=["text", "audio"],
                    audio={"voice": NARRATION_VOICE, "format": "wav"},
                    messages=[
                        {"role": "system", "content": NARRATION_INSTRUCTIONS},
                        {"role": "user", "content": f"""Read this video script excerpt aloud, verbatim:

{caption["text"]}"""},
                    ],
                )
                choice = completion.choices[0]
                audio = choice.message.audio
                if choice.finish_reason != "stop" or audio is None:
                    raise RuntimeError(f"""Incomplete narration for scene {scene_index}, beat {caption_index}""")
                normalized = [re.sub(r"[\W_]+", "", text.casefold().replace("99%", "ninety nine percent")) for text in (caption["text"], audio.transcript)]
                if normalized[0] != normalized[1]:
                    raise RuntimeError(f"""Narration changed the script for scene {scene_index}, beat {caption_index}: {audio.transcript}""")
                audio_path = Path(caption["audio"])
                with wave.open(BytesIO(base64.b64decode(audio.data, validate=True)), "rb") as recording:
                    channels = recording.getnchannels()
                    sample_width = recording.getsampwidth()
                    sample_rate = recording.getframerate()
                    samples = recording.readframes(recording.getnframes())
                with wave.open(str(audio_path), "wb") as recording:
                    recording.setnchannels(channels)
                    recording.setsampwidth(sample_width)
                    recording.setframerate(sample_rate)
                    recording.writeframes(samples)
                audio_path.with_suffix(".txt").write_text(audio.transcript, encoding="utf-8")
                duration = len(samples) / (channels * sample_width * sample_rate)
                print(f"""Narrated scene {scene_index}, beat {caption_index}: {duration:.1f}s — {audio.transcript}""", flush=True)


if __name__ == "__main__":
    main()
