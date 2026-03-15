# """G

# """

# from IPython.core.magic import register_line_magic
# from machineconfig.utils.utils2 import randstr
# from machineconfig.utils.path_reduced import P as PathExtended
# from rich import inspect
# from typing import Any


# def get_names():
#     res: dict[str, list[str]] = {}
#     for item in globals().keys():
#         if item.startswith("_") or item in ("open", "In", "Out", "quit", "exit", "get_ipython"):
#             continue
#         if item in ("P", "randstr", "Struct", "print_code", "print_dir_func", "print_program_func", "run_python_file_in_this_namespace"):
#             continue
#         type_ = repr(type(eval(item)))  # pylint: disable=eval-used
#         if "typing." in type_: continue
#         if type_ in res: res[type_].append(item)
#         else: res[type_] = [item]
#     return res


# @register_line_magic("codei")
# def print_code_interactive(_):
#     res = get_names()
#     from machineconfig.utils.utils import choose_from_options
#     choice = choose_from_options(multi=False, options=res["<class 'function'>"], msg="Choose a type to inspect", tv=True)
#     obj = eval(choice, globals(), locals())  # pylint: disable=eval-used
#     from rich.syntax import Syntax
#     import inspect
#     q: str = inspect.getsource(obj)
#     from rich import console
#     console.Console().print(Syntax(code=q, lexer="python"))


# @register_line_magic("print_dir")
# def print_dir_func(line: Any):
#     """Pretty print and categorize dir() output."""
#     _ = line  # ipython caller assumes there is at least one argument, an passes '' worstcase.
#     res = get_names()
#     inspect(res, value=False, title="""
# 📂 Objects Defined in Current Directory
# =======================================
# """)


# @register_line_magic("code")
# def print_program_func(obj_str: str):
#     """Inspect the code of an object."""
#     obj = eval(obj_str, globals(), locals())  # pylint: disable=eval-used
#     from rich.syntax import Syntax
#     import inspect
#     q: str = inspect.getsource(obj)
#     from rich import console
#     console.Console().print(Syntax(code=q, lexer="python"))


# @register_line_magic("play")
# def run_python_file_in_this_namespace(a_path: str, module: bool=False):
#     """Given a potentially dirty path of python file, run it in this namespace."""
#     from machineconfig.utils.utils import match_file_name, sanitize_path
#     path = sanitize_path(PathExtended(a_path))
#     if not path.exists():
#         path = match_file_name(a_path, search_root=PathExtended.cwd())
#     from IPython import get_ipython  # this gets the same instance, its in the namespace anyway even if not imported.
#     if module:
#         result = PathExtended.tmp().joinpath(f"tmp_scripts/python/{randstr()}.py")
#         result.parent.mkdir(parents=True, exist_ok=True)
#         result.write_text(f"""
# import sys
# sys.path.append(r'{path.parent}')
# from {path.stem} import *
# """, encoding="utf-8")
#         print("""💡 IPyExtension: Remember that reload fails for imported modules that import other varying modules.""")
#         get_ipython().run_line_magic(magic_name="load", line=result)
#     return

#     result = path.as_posix()
#     print(f"➡️ Running magic: %run {result}")
#     get_ipython().run_line_magic(magic_name="run", line=result)
#     globals().update(locals())
