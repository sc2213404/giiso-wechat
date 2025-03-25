from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

# 添加 wcferry 库的所有子模块
hiddenimports = collect_submodules('wcferry')

# 如果有额外的数据文件需要包含，可以使用 collect_data_files
datas = collect_data_files('wcferry')

# 如果有动态链接库（DLL）需要包含，可以使用 collect_dynamic_libs
binaries = collect_dynamic_libs('wcferry')