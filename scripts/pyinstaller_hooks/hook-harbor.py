from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files(
    "harbor",
    include_py_files=True,
    subdir="cli/template-task",
)
