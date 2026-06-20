import os
import pathlib
import textwrap


def secure_codex_configs() -> None:
    project_config_content = textwrap.dedent(
        """
        commit_attribution = ""
        [analytics]
        enabled = false
        [history]
        persistence = "none"
        [features]
        multi_agent = true
        """
    )
    user_config_content = project_config_content + textwrap.dedent(
        """
            [otel]
            exporter = "none"
            metrics_exporter = "none"
            trace_exporter = "none"
            log_user_prompt = false
            """
    )
    user_config_path = pathlib.Path.home() / ".codex" / "config.toml"
    project_config_path = pathlib.Path.cwd() / ".codex" / "config.toml"
    configs = ((user_config_path, user_config_content), (project_config_path, project_config_content))
    for config_path, config_content in configs:
        if config_path == user_config_path or config_path.parent.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(config_content, encoding="utf-8")
            try:
                os.chmod(config_path, 0o600)
            except Exception:
                pass
