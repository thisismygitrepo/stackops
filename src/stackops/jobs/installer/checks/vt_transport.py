import time
from asyncio import get_event_loop, timeout
from collections.abc import Coroutine, Mapping
from io import BytesIO
from typing import cast

import aiohttp
import vt

from stackops.jobs.installer.checks.vt_utils import get_vt_client


class VtTransport:
    def __init__(self, api_key: str) -> None:
        self._client = get_vt_client(api_key=api_key)

    def get_object(self, path: str, object_id: str, deadline: float) -> vt.Object:
        return _run_before_deadline(self._client.get_object_async(path, object_id), deadline)

    def get_upload_url(self, deadline: float) -> str:
        response: object = _run_before_deadline(self._client.get_data_async("/files/upload_url"), deadline)
        if not isinstance(response, str) or not response.startswith("https://"):
            raise ValueError("VirusTotal returned an invalid upload URL.")
        return response

    def upload_file(self, upload_url: str, file_bytes: bytes, deadline: float) -> vt.Object:
        return _run_before_deadline(_upload_file(self._client, upload_url, file_bytes), deadline)

    def close(self) -> None:
        self._client.close()


def _run_before_deadline[T](operation: Coroutine[object, object, T], deadline: float) -> T:
    async def run() -> T:
        async with timeout(max(0.0, deadline - time.monotonic())):
            return await operation

    return get_event_loop().run_until_complete(run())


async def _upload_file(client: vt.Client, upload_url: str, file_bytes: bytes) -> vt.Object:
    with BytesIO(file_bytes) as file, aiohttp.MultipartWriter("form-data") as form_data:
        part = aiohttp.get_payload(file)
        part.set_content_disposition("form-data", name="file", filename="unknown", quote_fields=False)
        form_data.append_payload(part)
        response = await client.post_async(upload_url, data=form_data)  # type: ignore[arg-type]
        error = await client.get_error_async(response)
        if error is not None:
            raise error
        raw_response = cast(object, await response.json_async())
        if not isinstance(raw_response, Mapping):
            raise ValueError("VirusTotal upload response must be a mapping.")
        data = cast(Mapping[str, object], raw_response).get("data")
        if not isinstance(data, dict):
            raise ValueError("VirusTotal upload returned invalid analysis data.")
        return vt.Object.from_dict(cast(dict[str, object], data))
