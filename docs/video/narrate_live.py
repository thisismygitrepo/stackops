# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "openai[realtime]>=3.28.0",
# ]
# ///
import asyncio
import base64
import json
import re
import sys
import wave
from array import array
from pathlib import Path
from typing import TypedDict, cast

from openai import AsyncOpenAI
from openai.resources.live.live import AsyncLiveConnection
from openai.types.live.session_config_param import SessionConfigParam

from live_constants import (
    LIVE_INPUT_SECONDS,
    LIVE_INSTRUCTIONS,
    LIVE_LEADING_SECONDS,
    LIVE_MODEL,
    LIVE_QUIET_TAIL_SECONDS,
    LIVE_SAMPLE_RATE,
    LIVE_SAMPLE_WIDTH,
    LIVE_SILENCE_THRESHOLD,
    LIVE_TIMEOUT_SECONDS,
    LIVE_TRAILING_SECONDS,
    LIVE_VOICE,
)


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


def normalize_transcript(text: str) -> str:
    spoken = text.lower().replace("99", "ninety nine").replace("%", "percent")
    normalized = re.sub(r"[^a-z0-9]", "", spoken)
    return normalized


async def stream_silence(connection: AsyncLiveConnection, stopped: asyncio.Event) -> None:
    chunk = bytes(round(LIVE_SAMPLE_RATE * LIVE_INPUT_SECONDS) * LIVE_SAMPLE_WIDTH)
    encoded = base64.b64encode(chunk).decode("ascii")
    loop = asyncio.get_running_loop()
    next_tick = loop.time()
    while not stopped.is_set():
        await connection.session.input_audio.append(audio=encoded)
        next_tick += LIVE_INPUT_SECONDS
        await asyncio.sleep(max(0, next_tick - loop.time()))


async def narrate_caption(client: AsyncOpenAI, script: str, audio_path: Path) -> tuple[float, str]:
    session: SessionConfigParam = {
        "model": LIVE_MODEL,
        "instructions": LIVE_INSTRUCTIONS,
        "audio": {
            "format": {"type": "audio/pcm", "rate": LIVE_SAMPLE_RATE},
            "output": {"voice": LIVE_VOICE},
        },
        "delegation": {"type": "client"},
        "store": False,
    }
    captured = bytearray()
    transcript = ""
    expected = normalize_transcript(script)
    first_speech_frame: int | None = None
    last_speech_frame = 0
    stopped = asyncio.Event()
    finalized = False
    try:
        async with asyncio.timeout(LIVE_TIMEOUT_SECONDS), client.live.connect(max_retries=0) as connection:
            async with asyncio.TaskGroup() as tasks:
                await connection.session.start(session=session, event_id="start")
                try:
                    async for event in connection:
                        if event.type == "session.started":
                            tasks.create_task(stream_silence(connection, stopped))
                            await connection.session.instructions.append(
                                event_id="narrate",
                                delegation_id=None,
                                content=f"""Read this video script aloud verbatim now in English.
Say only the script, then remain silent:
<script>{script}</script>""",
                            )
                        elif event.type == "session.output_audio.delta":
                            chunk = base64.b64decode(event.delta, validate=True)
                            samples = array("h")
                            samples.frombytes(chunk)
                            if sys.byteorder != "little":
                                samples.byteswap()
                            offset = len(captured) // LIVE_SAMPLE_WIDTH
                            active = [index for index, sample in enumerate(samples) if abs(sample) > LIVE_SILENCE_THRESHOLD]
                            if active:
                                if first_speech_frame is None:
                                    first_speech_frame = offset + active[0]
                                last_speech_frame = offset + active[-1] + 1
                            captured.extend(chunk)
                        elif event.type == "session.output_transcript.delta":
                            transcript += event.delta
                        elif event.type == "error":
                            raise RuntimeError(f"""GPT-Live narration failed: {event.error.message}""")
                        elif event.type == "session.closed":
                            if event.reason != "close_requested" or not stopped.is_set():
                                raise RuntimeError(f"""GPT-Live session ended unexpectedly: {event.reason}""")
                            finalized = True
                            break
                        quiet_frames = len(captured) // LIVE_SAMPLE_WIDTH - last_speech_frame
                        if (
                            not stopped.is_set()
                            and first_speech_frame is not None
                            and normalize_transcript(transcript) == expected
                            and quiet_frames >= LIVE_SAMPLE_RATE * LIVE_QUIET_TAIL_SECONDS
                        ):
                            stopped.set()
                            await connection.session.close(event_id="close")
                finally:
                    stopped.set()
    except TimeoutError as error:
        raise RuntimeError(f"""GPT-Live narration timed out. Expected: {script} Received: {transcript}""") from error
    if not finalized or first_speech_frame is None or normalize_transcript(transcript) != expected:
        raise RuntimeError(f"""Incomplete GPT-Live narration. Expected: {script} Received: {transcript}""")
    start_frame = max(0, first_speech_frame - round(LIVE_LEADING_SECONDS * LIVE_SAMPLE_RATE))
    end_frame = last_speech_frame + round(LIVE_TRAILING_SECONDS * LIVE_SAMPLE_RATE)
    audio = captured[start_frame * LIVE_SAMPLE_WIDTH : end_frame * LIVE_SAMPLE_WIDTH]
    with wave.open(str(audio_path), "wb") as recording:
        recording.setnchannels(1)
        recording.setsampwidth(LIVE_SAMPLE_WIDTH)
        recording.setframerate(LIVE_SAMPLE_RATE)
        recording.writeframes(audio)
    audio_path.with_suffix(".txt").write_text(transcript, encoding="utf-8")
    return len(audio) / (LIVE_SAMPLE_RATE * LIVE_SAMPLE_WIDTH), transcript


async def main() -> None:
    manifest_path = Path(sys.argv[1])
    manifest = cast(Manifest, json.loads(manifest_path.read_text(encoding="utf-8")))
    async with AsyncOpenAI(max_retries=0) as narrator:
        for scene_index, scene in enumerate(manifest["scenes"], start=1):
            for caption_index, caption in enumerate(scene["captions"], start=1):
                duration, transcript = await narrate_caption(narrator, caption["text"], Path(caption["audio"]))
                print(f"""Narrated scene {scene_index}, beat {caption_index}: {duration:.1f}s — {transcript}""", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
