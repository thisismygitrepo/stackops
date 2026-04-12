from typing import get_args

import machineconfig.scripts.python.enums as target


def test_backends_map_covers_all_loose_literals() -> None:
    assert set(target.BACKENDS_MAP) == set(get_args(target.BACKENDS_LOOSE))


def test_backends_map_resolves_every_canonical_backend() -> None:
    canonical_backends = set(get_args(target.BACKENDS))
    assert set(target.BACKENDS_MAP.values()) == canonical_backends
    for backend in canonical_backends:
        assert target.BACKENDS_MAP[backend] == backend
