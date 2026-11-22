from pathlib import Path

import tomlkit


def secure_codex_configs(*, user_config_path: Path, project_config_path: Path | None, overwrite: bool) -> None:
    paths = [user_config_path]
    if project_config_path is not None and project_config_path.parent.is_dir():
        paths.append(project_config_path)

    for config_path in paths:
        if config_path.exists():
            if not overwrite:
                continue
            document = tomlkit.parse(config_path.read_text(encoding="utf-8"))
        else:
            document = tomlkit.document()

        document["commit_attribution"] = ""
        document.setdefault("analytics", tomlkit.table())["enabled"] = False
        document.setdefault("history", tomlkit.table())["persistence"] = "none"
        document.setdefault("features", tomlkit.table())["multi_agent"] = True
        if config_path == user_config_path:
            document.setdefault("otel", tomlkit.table()).update(
                {"exporter": "none", "metrics_exporter": "none", "trace_exporter": "none", "log_user_prompt": False}
            )

        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(tomlkit.dumps(document), encoding="utf-8")
        try:
            config_path.chmod(0o600)
        except OSError:
            pass
