from pathlib import Path

from stackops.utils.cloud.target_conflict import apply_target_conflict_action


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
    if overwrite:
        apply_target_conflict_action(staged_path=staged_path, target_path=output_path, on_conflict="overwrite-target")
    else:
        staged_path.replace(output_path)
