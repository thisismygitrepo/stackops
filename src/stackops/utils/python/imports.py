import os


def find_repo_root_path(start_path: str) -> str | None:
    root_files = ["setup.py", "pyproject.toml", ".git"]
    path: str = start_path
    trials = 0
    root_path = os.path.abspath(os.sep)
    while path != root_path and trials < 20:
        for root_file in root_files:
            if os.path.exists(os.path.join(path, root_file)):
                return path
        path = os.path.dirname(path)
        trials += 1
    return None


def get_import_module_code(module_path: str) -> str:
    root_path = find_repo_root_path(module_path)
    if root_path is None:
        module_name = module_path.lstrip(os.sep).replace(os.sep, ".")
        if module_name.endswith(".py"):
            module_name = module_name[:-3]
    else:
        relative_path = module_path.replace(root_path, "")
        module_name = relative_path.lstrip(os.sep).replace(os.sep, ".")
        if module_name.endswith(".py"):
            module_name = module_name[:-3]
        if module_name.startswith("src."):
            module_name = module_name[4:]
        if module_name.startswith("myresources."):
            module_name = module_name[12:]
        if module_name.startswith("resources."):
            module_name = module_name[10:]
        if module_name.startswith("source."):
            module_name = module_name[7:]
    if any(char in module_name for char in "- :/\\"):
        module_name = "IncorrectModuleName"
    return f"from {module_name} import *"
