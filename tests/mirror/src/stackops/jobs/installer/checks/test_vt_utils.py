from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, cast

from stackops.jobs.installer.checks.vt_utils import scan_file

if TYPE_CHECKING:
    import vt


@dataclass(frozen=True)
class _QueuedAnalysis:
    id: str
    status: str


class _CancellingClient:
    def __init__(self, stop: Event) -> None:
        self.stop = stop
        self.uploads = 0
        self.polls = 0

    def scan_file(self, file: BytesIO) -> _QueuedAnalysis:
        assert file.read() == b"dummy-file"
        self.uploads += 1
        return _QueuedAnalysis(id="dummy-analysis", status="queued")

    def get_object(self, path: str, analysis_id: str) -> _QueuedAnalysis:
        assert path == "/analyses/{}"
        assert analysis_id == "dummy-analysis"
        self.polls += 1
        self.stop.set()
        return _QueuedAnalysis(id=analysis_id, status="queued")


def test_cancelled_scan_never_reads_file_or_sends_requests() -> None:
    stop = Event()
    stop.set()
    client = _CancellingClient(stop)

    result = scan_file(path=Path("missing-dummy-file"), client=cast("vt.Client", client), progress=None, task_id=None, stop=stop, request_lock=None)

    assert result == (None, [])
    assert client.uploads == 0
    assert client.polls == 0


def test_cancellation_interrupts_analysis_polling(tmp_path: Path) -> None:
    sample_path = tmp_path / "dummy-file"
    sample_path.write_bytes(b"dummy-file")
    stop = Event()
    client = _CancellingClient(stop)

    result = scan_file(path=sample_path, client=cast("vt.Client", client), progress=None, task_id=None, stop=stop, request_lock=None)

    assert result == (None, [])
    assert client.uploads == 1
    assert client.polls == 1
