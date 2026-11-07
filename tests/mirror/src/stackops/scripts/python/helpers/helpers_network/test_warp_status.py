import pytest

from stackops.scripts.python.helpers.helpers_network.warp_status import WarpRejection, WarpStatus, parse_warp_rejection, parse_warp_status


@pytest.mark.parametrize(
    ("raw_output", "expected"),
    [
        ("""{"status": "Connected", "reason": "NetworkHealthy"}""", WarpStatus(state="connected", detail="NetworkHealthy")),
        ("""{"status": "Connected"}""", WarpStatus(state="connected", detail=None)),
        ("""{"status": "Connecting", "reason": "CheckingNetwork"}""", WarpStatus(state="connecting", detail="CheckingNetwork")),
        ("""{"status": "Disconnected", "reason": "ManualDisconnection"}""", WarpStatus(state="disconnected", detail="ManualDisconnection")),
        ("""{"status": "Unable", "reason": "NoNetwork"}""", WarpStatus(state="unable", detail="NoNetwork")),
        ("""{"status": "Unable", "reason": {"RegistrationMissing": "DaemonStartup"}}""", WarpStatus(state="registration_missing", detail="DaemonStartup")),
        (
            """{"status": "Unable", "reason": {"RegistrationMissing": {"Invalidated": "ApiMismatch"}}}""",
            WarpStatus(state="registration_missing", detail="""{"Invalidated": "ApiMismatch"}"""),
        ),
        (
            """{"code": "FailedToConnectToDaemon", "error": "No such file or directory (os error 2)"}""",
            WarpStatus(state="daemon_down", detail="FailedToConnectToDaemon: No such file or directory (os error 2)"),
        ),
    ],
)
def test_parse_warp_status_classifies_daemon_output(raw_output: str, expected: WarpStatus) -> None:
    assert parse_warp_status(raw_output) == expected


def test_parse_warp_status_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="Unrecognized warp-cli status output"):
        parse_warp_status("""{"status": "Teleporting"}""")


def test_parse_warp_rejection_reads_code_and_message() -> None:
    raw_output = """{"code": "ApiError", "error": "Failed to communicate with the WARP API."}"""
    assert parse_warp_rejection(raw_output) == WarpRejection(code="ApiError", message="Failed to communicate with the WARP API.")
