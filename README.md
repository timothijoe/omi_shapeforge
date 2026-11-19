# OMI ShapeForge

OMI 的三维重建与位姿估计主项目，Python 包名及 Git 仓库目录统一为 `omi_shapeforge`。

`main` 保留为空分支，代码在 `dev`。后续功能从 `dev` 创建新的开发分支。

```bash
git clone --branch dev git@github.com:timothijoe/omi_shapeforge.git
cd omi_shapeforge
git switch -c feature/你的功能名
```

本仓库维护数据处理流程、算法调用接口、配准、评估、配置和文档。两个现有算法仓库继续独立维护：

| 目录 | 职责 |
| --- | --- |
| `../FoundationStereo` | 双目模型、推理实现和底层适配 |
| `../BundleSDF` | 跟踪、神经重建、CUDA/C++ 实现 |
| 当前仓库 | 项目流程、实验管理及后续业务功能 |

## 本机使用

```bash
cd /home/linux/omi_folder/omi_shapeforge
source .venv/bin/activate
omi-shapeforge doctor
omi-shapeforge smoke stereo
omi-shapeforge smoke bundlesdf
```

也可使用 `python -m omi_shapeforge`。`doctor` 检查配置路径、解释器及后端 Git 状态；GPU 运行能力通过对应 `smoke` 验证。

`doctor` 可以理解为“环境体检”：检查算法源码目录、Python 启动器、模型权重及 CUDA 编译器是否位于配置的路径，并显示后端代码的提交与本地改动。它只做检查和报告，不安装依赖、不修改代码，也不执行模型推理。

`smoke stereo` 调用 FoundationStereo 的官方双目样例，输出视差预览、深度数组和点云；`smoke bundlesdf` 检查原生绑定、CUDA 运算和真实图像 LoFTR 匹配。二者均运行于各自的 GPU 环境。完整视频在线跟踪、光模块重建和旧实验复现尚未接入本项目。

每次运行默认创建 `/data/omi_runtime/runs/omi_shapeforge/<UTC时间>_<算法>/`，保存：

- `run_manifest.json`：命令、配置、主项目和后端 Git 提交及工作区状态、开始/结束时间。
- `run.log`：后端执行日志。
- `report.json` 与算法输出：后端报告和结果文件。

可使用 `--output /新的/结果目录` 指定输出；已有目录会被拒绝，保护旧实验结果。

## 安装与配置

主项目只依赖 Python 标准库，要求 Python 3.11 及以上。GPU 依赖保留在后端环境中。

```bash
uv venv --python 3.11 --seed .venv
uv pip install --python .venv/bin/python --no-build-isolation -e .
```

默认配置是 `configs/workspace.toml`，使用同级算法仓库和本机 `/data/omi_runtime`。迁移机器时复制为忽略 Git 的 `configs/local.toml`，修改路径后运行：

```bash
omi-shapeforge --config configs/local.toml doctor
omi-shapeforge --config configs/local.toml smoke stereo
```

也可通过环境变量 `OMI_SHAPEFORGE_CONFIG` 指定配置文件。配置中的相对路径以配置文件所在目录为基准。使用非 editable 安装时，请显式指定 `--config`。

当前后端的初始化状态在 `manifests/backends.lock.json`。后端已有本地适配及尚未提交的验证脚本，清单同时记录提交号、工作区差异哈希和入口脚本哈希；仅克隆当前 GitHub HEAD 尚不能得到这些本地适配。待相应改动提交到各自仓库后，再更新依赖基线。

## 开发

```text
src/omi_shapeforge/   Python 包及命令入口
configs/             工作区配置
manifests/           后端版本与来源记录
tests/               调度、失败记录和结果保护测试
docs/                当前状态和开发约定
```

```bash
.venv/bin/python -m unittest discover -s tests -v
```

数据、权重和运行结果放在 `/data`，代码、配置和文档提交到 Git。开始新功能时创建分支；需要修改算法实现时，在对应算法仓库提交，再在本项目更新所使用的版本。

详见 [开发约定](docs/development.md) 和 [当前状态](docs/current.md)。既有环境构建记录继续保存在 `../local_setup/README.md`；迁移交接入口为 `/data/nov_19_folder/HANDOFF.md`。

两条主项目 GPU 调度入口已实际跑通，初始化验证见 [验证记录](manifests/initial_validation.json)。

## 许可证

本仓库采用 [MIT License](LICENSE)。FoundationStereo、BundleSDF 及相关权重分别遵循各自的许可证。
