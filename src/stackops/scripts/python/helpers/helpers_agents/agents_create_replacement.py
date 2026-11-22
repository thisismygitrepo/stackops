import shutil
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from stackops.scripts.python.helpers.helpers_agents.agents_create_inputs import validate_agents_output_dir_cleanup


@contextmanager
def replace_owned_job(*, repo_root: Path, agents_dir: Path, layout_path: Path) -> Generator[Path]:
    # Launchers embed their final paths, so move the previous job aside while writing the new one.
    previous_job = agents_dir.with_name(f".stackops-previous-{uuid4().hex}")
    validate_agents_output_dir_cleanup(repo_root=repo_root, agents_dir_obj=agents_dir)
    agents_dir.rename(previous_job)
    try:
        agents_dir.mkdir()
    except FileExistsError as error:
        raise ValueError(f"Another create reserved {agents_dir}. The previous job is at {previous_job}.") from error
    except OSError:
        previous_job.rename(agents_dir)
        raise
    try:
        if layout_path.is_relative_to(agents_dir):
            yield layout_path
        else:
            layout_path.parent.mkdir(parents=True, exist_ok=True)
            with TemporaryDirectory(dir=layout_path.parent) as staging_dir:
                staged_layout = Path(staging_dir) / layout_path.name
                yield staged_layout
                if layout_path.is_file():
                    shutil.copymode(layout_path, staged_layout)
                staged_layout.replace(layout_path)
    except BaseException:
        if agents_dir.exists():
            shutil.rmtree(agents_dir)
        previous_job.rename(agents_dir)
        raise
    shutil.rmtree(previous_job)
