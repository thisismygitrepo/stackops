


PLOTLY_RUNTIME_DEPENDENCIES = ("plotly", "kaleido")

def render_plotly(
    *,
    view: str,
    path: str | None,
    output: str | None,
    height: int = 900,
    width: int = 1200,
    template: str = "plotly_dark",
    max_depth: int | None,
) -> None:
    from machineconfig.scripts.python.graph.visualize.graph_data import (
        GraphNode,
        build_graph,
        iter_nodes,
    )
    from machineconfig.scripts.python.graph.visualize.plotly_browser import write_plotly_image
    KIND_COLORS = {
        "root": "#1f2937",
        "group": "#2563eb",
        "command": "#059669",
    }

    SUPPORTED_VIEWS = {"sunburst", "treemap", "icicle"}
    IMAGE_EXTENSIONS = {".png", ".svg", ".pdf", ".jpg", ".jpeg", ".webp"}

    def build_figure(
        root: "GraphNode",
        *,
        view: str,
        template: str = "plotly_dark",
        max_depth: int | None,
    ):
        view_key = view.lower().strip()
        if view_key not in SUPPORTED_VIEWS:
            raise ValueError(f"Unsupported view '{view}'. Choose from {sorted(SUPPORTED_VIEWS)}.")
        import plotly.graph_objects as go
        ids, labels, parents, values, customdata, colors = _build_plotly_payload(root, max_depth=max_depth)

        hovertemplate = (
            "<b>%{label}</b><br>"
            "Command: %{customdata[0]}<br>"
            "Kind: %{customdata[1]}<br>"
            "Aliases: %{customdata[2]}<br>"
            "%{customdata[3]}<extra></extra>"
        )

        trace = None
        if view_key == "sunburst":
            trace = go.Sunburst(
                ids=ids,
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                marker={"colors": colors},
                customdata=customdata,
                hovertemplate=hovertemplate,
            )
        elif view_key == "treemap":
            trace = go.Treemap(
                ids=ids,
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                marker={"colors": colors},
                customdata=customdata,
                hovertemplate=hovertemplate,
            )
        elif view_key == "icicle":
            trace = go.Icicle(
                ids=ids,
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                marker={"colors": colors},
                customdata=customdata,
                hovertemplate=hovertemplate,
            )

        fig = go.Figure(trace)
        fig.update_layout(
            template=template,
            margin={"l": 20, "r": 20, "t": 50, "b": 20},
            title={"text": f"CLI Graph - {view_key.title()}", "x": 0.5},
            height=900,
        )
        return fig


    def _build_plotly_payload(root: "GraphNode", *, max_depth: int | None = None):
        ids: list[str] = []
        labels: list[str] = []
        parents: list[str] = []
        values: list[int] = []
        customdata: list[list[str]] = []
        colors: list[str] = []

        for node, parent in iter_nodes(root):
            if max_depth is not None and node.depth > max_depth:
                continue
            if parent is not None and max_depth is not None and parent.depth > max_depth:
                continue

            ids.append(node.id)
            labels.append(node.name or node.command or node.id)
            parents.append(parent.id if parent is not None else "")
            values.append(node.leaf_count)

            alias_text = ", ".join(node.aliases) if node.aliases else "-"
            description = node.long_description or node.description or ""
            customdata.append([node.command, node.kind, alias_text, description])
            colors.append(KIND_COLORS.get(node.kind, "#94a3b8"))

        return ids, labels, parents, values, customdata, colors

    root = build_graph(path)
    fig = build_figure(root, view=view, template=template, max_depth=max_depth)
    if output is None:
        fig.show()
    else:
        from pathlib import Path
        output_path = Path(output)
        suffix = output_path.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            write_plotly_image(fig=fig, output=output_path, width=width, height=height)
        else:
            fig.write_html(output_path, include_plotlyjs="cdn")
        print(f"Wrote {output_path}")


def use_render_plotly(
    *,
    view: str,
    path: str | None,
    output: str | None,
    height: int = 900,
    width: int = 1200,
    template: str = "plotly_dark",
    max_depth: int | None,
    uv_with: list[str] | None,
) -> None:
    from machineconfig.utils.code import run_lambda_function
    # from machineconfig.utils.source_of_truth import REPO_ROOT

    resolved_uv_with = [] if uv_with is None else list(uv_with)
    for dependency in PLOTLY_RUNTIME_DEPENDENCIES:
        if dependency not in resolved_uv_with:
            resolved_uv_with.append(dependency)

    # resolved_uv_project_dir = str(REPO_ROOT) if REPO_ROOT.joinpath("pyproject.toml").exists() else None

    run_lambda_function(
        lambda: render_plotly(
            view=view,
            output=output,
            template=template,
            path=path,
            max_depth=max_depth,
            height=height,
            width=width,
        ),
        uv_with=resolved_uv_with,
        uv_project_dir=None,
    )


if __name__ == "__main__":
    # from machineconfig.scripts.python.graph.visualize.graph_data import (
    #     GraphNode,
    #     # build_graph,
    #     iter_nodes,
    # )
    # from machineconfig.scripts.python.graph.visualize.plotly_browser import write_plotly_image
    pass
