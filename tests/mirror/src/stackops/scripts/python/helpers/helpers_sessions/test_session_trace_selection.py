import pytest

from stackops.scripts.python.helpers.helpers_sessions import session_trace_selection
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import TraceTarget


def test_resolve_trace_session_names_preserves_selector_and_discovery_order_with_deduplication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    targets = [
        TraceTarget(label="Build API", session_name="build-api", match_names=("build-api",)),
        TraceTarget(label="Build worker", session_name="build-worker", match_names=("build-worker",)),
        TraceTarget(label="QA A", session_name="qa-a", match_names=("qa-a",)),
        TraceTarget(label="QA B", session_name="qa-b", match_names=("qa-b",)),
    ]

    def fake_load_trace_targets(backend: session_trace_selection.TraceBackend) -> list[TraceTarget]:
        assert backend == "tmux"
        return targets

    monkeypatch.setattr(session_trace_selection, "_load_trace_targets", fake_load_trace_targets)

    resolved_session_names = session_trace_selection.resolve_trace_session_names(
        backend="tmux",
        session_selectors=" qa-? , build-* , build-api , qa-a ",
    )

    assert resolved_session_names == ["qa-a", "qa-b", "build-api", "build-worker"]


def test_resolve_trace_session_names_uses_only_star_and_question_mark_as_wildcards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    targets = [
        TraceTarget(label="No gap", session_name="blahvalues", match_names=("blahvalues",)),
        TraceTarget(label="Middle", session_name="blah-mid-values", match_names=("blah-mid-values",)),
        TraceTarget(label="Wrong suffix", session_name="blah-mid-value", match_names=("blah-mid-value",)),
        TraceTarget(label="One character", session_name="job-a", match_names=("job-a",)),
        TraceTarget(label="Two characters", session_name="job-ab", match_names=("job-ab",)),
        TraceTarget(label="Literal dot", session_name="release.1", match_names=("release.1",)),
        TraceTarget(label="Nonliteral dot", session_name="releaseX1", match_names=("releaseX1",)),
    ]

    def fake_load_trace_targets(backend: session_trace_selection.TraceBackend) -> list[TraceTarget]:
        assert backend == "herdr"
        return targets

    monkeypatch.setattr(session_trace_selection, "_load_trace_targets", fake_load_trace_targets)

    resolved_session_names = session_trace_selection.resolve_trace_session_names(
        backend="herdr",
        session_selectors="blah*values,job-?,release.?",
    )

    assert resolved_session_names == ["blahvalues", "blah-mid-values", "job-a", "release.1"]


def test_resolve_trace_session_names_rejects_an_unmatched_wildcard_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    targets = [TraceTarget(label="Alpha", session_name="alpha", match_names=("alpha",))]

    def fake_load_trace_targets(backend: session_trace_selection.TraceBackend) -> list[TraceTarget]:
        assert backend == "aoe"
        return targets

    monkeypatch.setattr(session_trace_selection, "_load_trace_targets", fake_load_trace_targets)

    with pytest.raises(ValueError) as error:
        session_trace_selection.resolve_trace_session_names(
            backend="aoe",
            session_selectors="missing-*",
        )

    assert str(error.value) == "Session selector 'missing-*' matched no aoe sessions. Available names: ['alpha']"


def test_resolve_trace_session_names_preserves_missing_exact_selectors_without_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_trace_targets_are_loaded(backend: session_trace_selection.TraceBackend) -> list[TraceTarget]:
        raise AssertionError(f"Exact selectors unexpectedly triggered {backend} session discovery.")

    monkeypatch.setattr(session_trace_selection, "_load_trace_targets", fail_if_trace_targets_are_loaded)

    resolved_session_names = session_trace_selection.resolve_trace_session_names(
        backend="tmux",
        session_selectors="missing,known,missing",
    )

    assert resolved_session_names == ["missing", "known"]
