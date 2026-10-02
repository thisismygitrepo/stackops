import typer

from stackops.scripts.python.helpers.helpers_devops.cli_repos_viz import analyze_repo_development, count_lines_in_repo, gource_viz
from stackops.utils.cli_utils.ordered_group import ordered_group


def get_app() -> typer.Typer:
    stats_app = typer.Typer(
        cls=ordered_group(("viz", "count-lines", "analyze")),
        help="📊 <S> Visualize and analyze repository statistics",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    stats_app.command(name="viz", help="🎬 <v> Visualize repository activity using Gource")(gource_viz)
    stats_app.command(name="v", help="Visualize repository activity using Gource", hidden=True)(gource_viz)
    stats_app.command(name="count-lines", help="📄 <c> Count python lines of code in current repo + historical edits.")(count_lines_in_repo)
    stats_app.command(name="c", help="Count python lines of code in current repo + historical edits.", hidden=True)(count_lines_in_repo)
    stats_app.command(name="analyze", help="📊 <z> Analyze repository development over time")(analyze_repo_development)
    stats_app.command(name="z", help="Analyze repository development over time", hidden=True)(analyze_repo_development)
    return stats_app
