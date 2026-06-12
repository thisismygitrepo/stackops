from pathlib import Path
from typing import Annotated

import typer


def count_lines_in_repo(repo_path: Annotated[str, typer.Argument(help="Path to the git repository")] = ".") -> None:
    resolved_repo_path = Path(repo_path).expanduser().absolute().resolve()
    if not resolved_repo_path.exists():
        typer.echo(f"❌ Repository path does not exist: {resolved_repo_path}", err=True)
        raise typer.Exit(code=1)
    if not resolved_repo_path.is_dir():
        typer.echo(f"❌ Repository path is not a directory: {resolved_repo_path}", err=True)
        raise typer.Exit(code=1)

    from git import InvalidGitRepositoryError, Repo

    try:
        repo = Repo(resolved_repo_path)
    except InvalidGitRepositoryError as exc:
        typer.echo(f"❌ {resolved_repo_path} is not within a git repository. Pass a path inside a git repo and retry.", err=True)
        raise typer.Exit(code=1) from exc

    if repo.bare or repo.working_tree_dir is None:
        typer.echo(f"❌ {resolved_repo_path} is inside a bare git repository. Pass a working tree path and retry.", err=True)
        raise typer.Exit(code=1)

    from stackops.scripts.python.helpers.helpers_repos import repo_analyzer_1

    try:
        repo_analyzer_1.count_historical_line_edits(repo_path=resolved_repo_path.as_posix())
    except Exception as exc:
        typer.echo(f"❌ Error counting lines in repo {resolved_repo_path}: {exc}", err=True)
        raise typer.Exit(code=1) from exc


def print_python_files_by_size(repo_path: Annotated[str, typer.Argument(..., help="Path to the git repository")]) -> None:
    from stackops.scripts.python.helpers.helpers_repos.repo_analyzer_2 import print_python_files_by_size_impl

    print_python_files_by_size_impl(repo_path=repo_path)


def analyze_repo_development(repo_path: Annotated[str, typer.Argument(..., help="Path to the git repository")]) -> None:
    resolved_repo_path = Path(repo_path).expanduser().absolute().resolve()
    if not resolved_repo_path.exists():
        typer.echo(f"❌ Repository path does not exist: {resolved_repo_path}")
        raise typer.Exit(code=1)
    if not resolved_repo_path.is_dir():
        typer.echo(f"❌ Repository path is not a directory: {resolved_repo_path}")
        raise typer.Exit(code=1)

    def func(repo_path: str) -> None:
        from stackops.scripts.python.helpers.helpers_repos.repo_analyzer_2 import analyze_over_time

        analyze_over_time(repo_path=repo_path)

    from stackops.utils.code import run_lambda_function
    from stackops.utils.ssh_utils.abc import STACKOPS_VERSION

    stackops_plot_requirement = f"stackops[plot]>={STACKOPS_VERSION}"
    run_lambda_function(lambda: func(repo_path=resolved_repo_path.as_posix()), uv_project_dir=None, uv_with=[stackops_plot_requirement, "polars"])


def gource_viz(
    repo: Annotated[str, typer.Option(..., "--repo", "-r", help="Path to git repository to visualize")] = ".",
    output_file: Annotated[
        Path | None, typer.Option(..., "--output", "-o", help="Output video file (e.g., output.mp4). If specified, gource will render to video.")
    ] = None,
    resolution: Annotated[str, typer.Option(..., "--resolution", "-R", help="Video resolution (e.g., 1920x1080, 1280x720)")] = "1920x1080",
    seconds_per_day: Annotated[float, typer.Option(..., "--seconds-per-day", "-D", help="Speed of simulation (lower = faster)")] = 0.1,
    auto_skip_seconds: Annotated[
        float, typer.Option(..., "--auto-skip-seconds", "-A", help="Skip to next entry if nothing happens for X seconds")
    ] = 1.0,
    title: Annotated[str | None, typer.Option(..., "--title", "-t", help="Title for the visualization")] = None,
    hide_items: Annotated[
        list[str] | None,
        typer.Option(
            ..., "--hide", "-h", help="Items to hide: bloom, date, dirnames, files, filenames, mouse, progress, root, tree, users, usernames"
        ),
    ] = None,
    key_items: Annotated[bool, typer.Option(..., "--key", "-k", help="Show file extension key")] = False,
    fullscreen: Annotated[bool, typer.Option(..., "--fullscreen", "-f", help="Run in fullscreen mode")] = False,
    viewport: Annotated[str | None, typer.Option(..., "--viewport", "-v", help="Camera viewport (e.g., '1000x1000')")] = None,
    start_date: Annotated[str | None, typer.Option(..., "--start-date", "-S", help="Start date (YYYY-MM-DD)")] = None,
    stop_date: Annotated[str | None, typer.Option(..., "--stop-date", "-E", help="Stop date (YYYY-MM-DD)")] = None,
    user_image_dir: Annotated[Path | None, typer.Option(..., "--user-image-dir", "-i", help="Directory with user avatar images")] = None,
    max_files: Annotated[int, typer.Option(..., "--max-files", "-M", help="Maximum number of files to show (0 = no limit)")] = 0,
    max_file_lag: Annotated[float, typer.Option(..., "--max-file-lag", "-L", help="Max time files remain on screen after last change")] = 5.0,
    file_idle_time: Annotated[int, typer.Option(..., "--file-idle-time", "-I", help="Time in seconds files remain idle before being removed")] = 0,
    framerate: Annotated[int, typer.Option(..., "--framerate", "-F", help="Frames per second for video output")] = 60,
    background_color: Annotated[str, typer.Option(..., "--background-color", "-B", help="Background color in hex (e.g., 000000 for black)")] = "000000",
    font_size: Annotated[int, typer.Option(..., "--font-size", "-z", help="Font size")] = 22,
    camera_mode: Annotated[str, typer.Option(..., "--camera-mode", "-C", help="Camera mode: overview or track")] = "overview",
    self: Annotated[bool, typer.Option(..., "--self", "-x", help="Clone stackops repository and act on it")] = False,
) -> None:
    """🎬 Visualize repository activity using Gource."""
    from stackops.scripts.python.helpers.helpers_repos.grource import visualize

    if self:
        repo_path = Path.home().joinpath("stackops")
        if not repo_path.exists():
            import git

            repo_url = "https://github.com/thisismygitrepo/stackops.git"
            git.Repo.clone_from(repo_url, to_path=repo_path.as_posix())
        repo = repo_path.as_posix()
    visualize(
        repo=repo,
        output_file=output_file,
        resolution=resolution,
        seconds_per_day=seconds_per_day,
        auto_skip_seconds=auto_skip_seconds,
        title=title,
        hide_items=hide_items,
        key_items=key_items,
        fullscreen=fullscreen,
        viewport=viewport,
        start_date=start_date,
        stop_date=stop_date,
        user_image_dir=user_image_dir,
        max_files=max_files,
        max_file_lag=max_file_lag,
        file_idle_time=file_idle_time,
        framerate=framerate,
        background_color=background_color,
        font_size=font_size,
        camera_mode=camera_mode,
    )
