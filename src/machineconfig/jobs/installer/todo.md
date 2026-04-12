

# messy screen after tv use.
› › in devops install when I go --interactive and get the tv option selection, when choosing and exiting, the screen is not cleared and we never go back to the
    orginal terminal, its all messy. the program completes fine, no errors and hands over back to python, but the screen is full with remnanets from tv selection
    stage. the ideal behaviour is that its not clearning the screen which deletes all the history and I can no longer scroll up to older stuff, but start a new
  screen and when exiting from it, we go back to the same old screen. with all history therein.

# create refernce files
# for each one of those files (non python)
cd  ~/code/machineconfig/src/machineconfig fd -t f -E .venv -E docs -E tests -E '*.py'
make sure there is __init__.py file next to them, and in that init file, put variable referencing those files
like this
e.g. for this one utils/schemas/installer/installer_type.schema.json
we create utils/schemas/installer/__init__.py and in that file, we put
INSTALLER_TYPE_SCHEMA_PATH_REFERENCE = "./installer_type.schema.json"
notice "_PATH_REFERENCE" please ensure that this is consistent across all names, and if not consistent add it please to noncompliant instances.
additionally, if __init__.py does exist, then please check that it doen't have stale reference to a file that doens't exit
if so, delete that path reference.


# use reference files:
# $caveman ultra. 
ensure that for any python file, trying to reference any of those files (as a variable or path etc ...)
Then that reference MUST occur via the corresponding variables defined in relevant __init__.py file next to that non-py file.
the code must derive the full absolute path from the reference in init file + module path.

The non-py files can be obtained by running this command:
cd  ~/code/machineconfig/src/machineconfig fd -t f -E .venv -E docs -E tests -E '*.py'

and your check for their reference must go through all py files.

# update toml files
cany ou ensure that my tv toml files are up to date? see if tv cli can dump new ones src/machineconfig/settings/television