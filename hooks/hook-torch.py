from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules, collect_data_files

# Collect all torch submodules and their DLLs
hiddenimports = collect_submodules('torch')
binaries = collect_dynamic_libs('torch')
datas = collect_data_files('torch')
