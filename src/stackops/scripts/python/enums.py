
from typing import Literal, TypeAlias

BACKENDS: TypeAlias = Literal["marimo", "jupyter", "vscode", "visidata", "terminal1", "terminal2", "python", "ipython"]
BACKENDS_LOOSE: TypeAlias = Literal[
    "marimo",
    "m",
    "jupyter",
    "j",
    "vscode",
    "c",
    "visidata",
    "v",
    "terminal1",
    "t",
    "terminal2",
    "T",
    "python",
    "p",
    "ipython",
    "i",
]
BACKENDS_MAP: dict[BACKENDS_LOOSE, BACKENDS] = {
    "marimo": "marimo",
    "m": "marimo",
    "jupyter": "jupyter",
    "j": "jupyter",
    "vscode": "vscode",
    "c": "vscode",
    "visidata": "visidata",
    "v": "visidata",
    "terminal1": "terminal1",
    "t": "terminal1",
    "terminal2": "terminal2",
    "T": "terminal2",
    "python": "python",
    "p": "python",
    "ipython": "ipython",
    "i": "ipython",
}
