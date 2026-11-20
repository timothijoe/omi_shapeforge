# 配置和路径解析

默认模板为 [configs/workspace.toml](../../../configs/workspace.toml)。优先级为显式 `--config` → `OMI_SHAPEFORGE_CONFIG` → 源码工作区默认模板。非 editable 安装应明确给配置路径。

| 区块／字段 | 用途 |
| --- | --- |
| storage.runtime_root | 主调度器缓存根目录 |
| storage.run_directory | 主 smoke 的默认结果根目录，独立于 runtime_root |
| backends.stereo.repository／environment／entrypoint | 源码、venv 根目录、仓库内脚本 |
| backends.stereo.checkpoint | 当前模型文件 |
| backends.bundlesdf.repository／environment／entrypoint | 另一个后端的对应位置 |
| backends.bundlesdf.cuda_home | CUDA 工具链根目录 |
| simulations.mujoco.environment／entrypoint／scene | 可选 MuJoCo 环境、仓库脚本和默认 MJCF；路径相对配置文件，python 为 environment/bin/python |

两种后端的字段均须在配置中给出。相对路径以配置文件所在目录为基准，并展开 `~` 和已有环境变量；源码入口须位于指定仓库内。解释器路径保留 `<environment>/bin/python`，不把符号链接解析成共享基础解释器。

上述展开针对字段值。配置文件选择参数本身的相对路径以当前工作目录为基准；需要 `~` 或变量时先由 shell 展开，不依赖读取器再次展开该选择字符串。

`configs/local.toml` 被 Git 忽略，适合机器覆盖。没有已实现的 `OMI_RUNTIME_ROOT` 自动覆盖器；教程中的 `RUNTIME_ROOT` 只是操作者 shell 变量。改变 runtime_root 不会自动更新显式 environment、checkpoint 或 run_directory，迁移时应逐项填写。

主调度器设置 HF／Torch 缓存、VIRTUAL_ENV、UTF-8 和后端路径，移除 PYTHONHOME 与旧 PYTHONPATH；BundleSDF 加入源码、mycuda 和 build 目录。它不复制环境或自动安装缺失库。Isaac 的更严格环境清理见[外部系统](external-systems.md)。
