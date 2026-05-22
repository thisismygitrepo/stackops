
from typing import Literal, TypeAlias

BACKENDS: TypeAlias = Literal["marimo", "jupyter", "vscode", "visidata", "auto1", "auto2", "python", "ipython"]
BACKENDS_LOOSE: TypeAlias = Literal[
    "marimo",
    "m",
    "jupyter",
    "j",
    "vscode",
    "c",
    "visidata",
    "v",
    "auto1",
    "a1",
    "auto2",
    "a2",
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
    "auto1": "auto1",
    "a1": "auto1",
    "auto2": "auto2",
    "a2": "auto2",
    "python": "python",
    "p": "python",
    "ipython": "ipython",
    "i": "ipython",
}
