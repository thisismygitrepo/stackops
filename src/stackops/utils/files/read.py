


from pathlib import Path
from typing import Any
from collections.abc import Callable
import json


def read_file(path: 'Path', **kwargs: Any) -> Any:
    if Path(path).is_dir():
        raise IsADirectoryError(f"Path is a directory, not a file: {path}")
    suffix = Path(path).suffix[1:]
    if suffix == "":
        raise ValueError(f"File type could not be inferred from suffix. Suffix is empty. Path: {path}")
    reader = READERS.get(suffix)
    if reader is not None:
        return reader(str(path), **kwargs)
    raise AttributeError(f"Unknown file type. failed to recognize the suffix `{suffix}` of file {path}")


def _remove_c_style_comments(text: str) -> str:
    result: list[str] = []
    index = 0
    in_string = False
    escaping = False

    while index < len(text):
        current = text[index]
        next_index = index + 1
        next_character = text[next_index] if next_index < len(text) else ""

        if in_string:
            result.append(current)
            if escaping:
                escaping = False
            elif current == "\\":
                escaping = True
            elif current == '"':
                in_string = False
            index += 1
            continue

        if current == '"':
            in_string = True
            result.append(current)
            index += 1
            continue

        if current == "/" and next_character == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue

        if current == "/" and next_character == "*":
            index += 2
            while index < len(text):
                if text[index] == "*" and index + 1 < len(text) and text[index + 1] == "/":
                    index += 2
                    break
                if text[index] in "\r\n":
                    result.append(text[index])
                index += 1
            continue

        result.append(current)
        index += 1

    return "".join(result)


def remove_c_style_comments(text: str) -> str:
    return _remove_c_style_comments(text)


def read_json(path: 'Path', r: bool = False, **kwargs: Any) -> Any:
    raw_text = Path(path).read_text(encoding="utf-8")
    try:
        mydict = json.loads(raw_text, **kwargs)
    except Exception:
        mydict = json.loads(_remove_c_style_comments(raw_text), **kwargs)
    _ = r
    return mydict


def read_jsonl(path: 'Path', r: bool = False, **kwargs: Any) -> Any:
    raw = Path(path).read_text(encoding="utf-8").splitlines()
    res: list[Any] = []
    import json
    for line in raw:
        try:
            res.append(json.loads(line, **kwargs))
        except json.JSONDecodeError as ex:
            print(f"💥 Failed to parse line as JSON: {line}\nError: {ex}")
            raise ex
    _ = r
    return res


def read_yaml(path: 'Path', r: bool = False) -> Any:
    import yaml
    mydict = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=yaml.FullLoader)
    _ = r
    return mydict


def read_ini(path: 'Path', encoding: str | None = None) -> Any:
    if not Path(path).exists() or Path(path).is_dir():
        raise FileNotFoundError(f"File not found or is a directory: {path}")
    import configparser
    res = configparser.ConfigParser()
    res.read(filenames=[str(path)], encoding=encoding)
    return res


def read_toml(path: 'Path') -> Any:
    import tomllib
    return tomllib.loads(Path(path).read_text(encoding='utf-8'))


def read_npy(path: 'Path', **kwargs: Any) -> Any:
    import numpy as np
    data = np.load(str(path), allow_pickle=True, **kwargs)
    return data


def read_pickle(path: 'Path', **kwargs: Any) -> Any:
    import pickle
    try:
        return pickle.loads(Path(path).read_bytes(), **kwargs)
    except BaseException as ex:
        print(f"💥 Failed to load pickle file `{path}` with error:\n{ex}")
        raise ex


def read_pkl(path: 'Path', **kwargs: Any) -> Any: return read_pickle(path, **kwargs)


def read_py(path: 'Path', init_globals: dict[str, Any] | None = None, run_name: str | None = None) -> Any:
    import runpy
    return runpy.run_path(str(path), init_globals=init_globals, run_name=run_name)


def read_txt(path: 'Path', encoding: str = 'utf-8') -> str: return Path(path).read_text(encoding=encoding)


def read_parquet(path: 'Path', **kwargs: Any) -> Any:
    import polars as pl
    return pl.read_parquet(path, **kwargs)


def read_csv(path: 'Path', **kwargs: Any) -> Any:
    import polars as pl
    return pl.read_csv(path, infer_schema_length=10000, **kwargs)


def read_npz(path: 'Path', **kwargs: Any) -> Any:
    import numpy as np
    return np.load(str(path), **kwargs)


def read_dbms(path: 'Path', **kwargs: Any) -> Any:
    from stackops.utils.files.dbms import DBMS
    _ = kwargs
    res = DBMS.from_local_db(path=Path(path))
    try:
        print(res.describe_db())
    except Exception:
        print("💥 Could not describe the database.")
    return res


def read_image(path: 'Path', **kwargs: Any) -> Any:
    import matplotlib.pyplot as pyplot
    return pyplot.imread(str(path), **kwargs)


_IMAGE_SUFFIXES: list[str] = ['eps', 'jpg', 'jpeg', 'pdf', 'pgf', 'png', 'ps', 'raw', 'rgba', 'svg', 'svgz', 'tif', 'tiff']
_DBMS_SUFFIXES: list[str] = ['sqlite', 'sqlite3', 'db', 'duckdb']

READERS: dict[str, Callable[..., Any]] = {
    "json": read_json,
    "jsonl": read_jsonl,
    "yaml": read_yaml,
    "ini": read_ini,
    "toml": read_toml,
    "npy": read_npy,
    "npz": read_npz,
    "pickle": read_pickle,
    "pkl": read_pkl,
    "py": read_py,
    "txt": read_txt,
    "parquet": read_parquet,
    "csv": read_csv,
    **{s: read_dbms for s in _DBMS_SUFFIXES},
    **{s: read_image for s in _IMAGE_SUFFIXES},
}


if __name__ == '__main__':
    pass
