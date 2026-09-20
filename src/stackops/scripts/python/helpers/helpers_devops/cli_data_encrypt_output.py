import shutil
from pathlib import Path
from tempfile import mkdtemp

from stackops.utils.path_core import tmp


def validate_output(*, source: Path, output_path: Path, overwrite: bool) -> None:
    source_locations = (source, source.parent.resolve() / source.name, source.resolve())
    output_locations = (output_path, output_path.parent.resolve() / output_path.name, output_path.resolve())
    if any(
        source_location.is_relative_to(output_location) or output_location.is_relative_to(source_location)
        for source_location in source_locations
        for output_location in output_locations
    ):
        raise ValueError(f"""Source and output paths overlap: {source} ==> {output_path}. Choose a separate --output path.""")
    if (output_path.exists() or output_path.is_symlink()) and not overwrite:
        raise FileExistsError(f"""Output path already exists: {output_path}. Use --overwrite to replace it or --output to choose another path.""")


def publish_output(*, source: Path, staged_path: Path, output_path: Path, overwrite: bool) -> None:
    validate_output(source=source, output_path=output_path, overwrite=overwrite)
    if not (output_path.exists() or output_path.is_symlink()):
        _move_output(staged_path=staged_path, output_path=output_path)
        return

    backup_root = Path(mkdtemp(prefix=".stackops-replaced-", dir=tmp(folder="stackops/data", file=None, root="~/tmp_results")))
    backup_path = backup_root / "output"
    shutil.move(output_path, backup_path)
    try:
        _move_output(staged_path=staged_path, output_path=output_path)
    except BaseException:
        if output_path.exists() or output_path.is_symlink():
            raise RuntimeError(f"""Could not remove incomplete output: {output_path}. Previous output is preserved at {backup_path}.""")
        shutil.move(backup_path, output_path)
        shutil.rmtree(backup_root)
        raise
    shutil.rmtree(backup_root)


def _move_output(*, staged_path: Path, output_path: Path) -> None:
    try:
        shutil.move(staged_path, output_path)
    except BaseException:
        if output_path.is_symlink() or output_path.is_file():
            output_path.unlink()
        elif output_path.exists():
            shutil.rmtree(output_path)
        raise
