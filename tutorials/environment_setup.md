# 安装环境与填写路径

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

适用：当前 Linux x86_64 工作区。主项目要求 Python 3.11 以上，已验证控制环境为 Python 3.11；GPU、Blender 和 Isaac 各用独立运行时。

## 1. 主环境

在仓库根目录执行。已有 `.venv` 时保留：

```bash
if [ ! -x .venv/bin/python ]; then
  uv venv --python 3.11 --seed .venv
fi
uv pip install --python .venv/bin/python --no-build-isolation -e .
.venv/bin/omi-shapeforge --help
```

预期显示 `doctor`、`smoke`。首次下载 Python／构建依赖需要网络。若已有 venv 缺少 setuptools，应先满足 `pyproject.toml` 的构建要求，而不是混用系统 pip。

## 2. 主配置

```bash
if [ ! -e configs/local.toml ]; then
  cp configs/workspace.toml configs/local.toml
fi
```

编辑 `configs/local.toml` 的资源根、结果根、两个算法仓库、两个 venv、模型和 CUDA 路径。模板按本机布局提供默认值；换机器时逐项填写。相对路径以配置文件所在目录为基准。

```bash
.venv/bin/omi-shapeforge --config configs/local.toml doctor
```

预期 JSON 的路径检查为 true；GPU 实际验证下一步再做。也可设置 `OMI_SHAPEFORGE_CONFIG` 指向该文件。`doctor` 不会安装或修复依赖。

## 3. 已有 GPU 后端

本机的 `envs/foundation_stereo` 与 `envs/bundlesdf` 位于 `/data/omi_runtime`，版本和来源由[环境快照说明](../manifests/README.md)记录。后端适配已保存为本地版本，具体提交和 bundle 见[源码基线](../docs/design/source-baseline.md)。远端尚未同步；现有环境 smoke 通过不等于从零安装或编译通过。

主项目尚未提供完整可移植的 GPU 后端安装器。构建笔记原件仍在同级 `local_setup`；参考包清单和 freeze 保留在 `manifests/environments/`。freeze 中的 editable／本地 URL 是来源记录，不能直接在另一台机器 pip 安装。原生扩展还需对应系统库和机器编译，旧 venv 不应复制使用。

现有环境可通过[样例教程](stereo_sample.md)验证。完整 GPU 从零恢复仍应先保存后端代码版本，再按适用平台的构建过程逐项复验。

## 4. 独立仿真环境

```bash
RUNTIME_ROOT=/data/omi_runtime
if [ ! -x "$RUNTIME_ROOT/envs/simulation/bin/python" ]; then
  uv venv --python 3.11 --seed "$RUNTIME_ROOT/envs/simulation"
fi
uv pip install --python "$RUNTIME_ROOT/envs/simulation/bin/python" -r requirements/simulation.lock.txt
"$RUNTIME_ROOT/envs/simulation/bin/python" -m pip check
```

预期没有依赖冲突。此环境包含 MuJoCo／OpenUSD；Blender 与 Isaac 使用各自安装程序，不装进这个 venv。安装或路径问题见[排错](troubleshooting.md)。
