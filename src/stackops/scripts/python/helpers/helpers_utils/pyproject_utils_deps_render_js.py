from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_bootstrap import (
    DEPENDENCY_REPORT_JS_BOOTSTRAP,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_interaction import (
    DEPENDENCY_REPORT_JS_INTERACTION,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_layout import (
    DEPENDENCY_REPORT_JS_LAYOUT,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_shared import (
    DEPENDENCY_REPORT_JS_SHARED,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_js_svg import (
    DEPENDENCY_REPORT_JS_SVG,
)

DEPENDENCY_REPORT_JS = "\n".join(
    (
        DEPENDENCY_REPORT_JS_BOOTSTRAP,
        DEPENDENCY_REPORT_JS_LAYOUT,
        DEPENDENCY_REPORT_JS_SVG,
        DEPENDENCY_REPORT_JS_INTERACTION,
        DEPENDENCY_REPORT_JS_SHARED,
        "})();\n",
    )
)
