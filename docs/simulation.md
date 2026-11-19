# Blender 与光模块仿真原型

本轮在 `feature/optical-simulation` 开发。原始便携包和大资源保留在 `/data/omi_runtime`，代码进入本仓库。当前场景包含光模块外观、桌面和示意支撑轨道，机械臂、真实夹爪及真实夹具尚未接入。

## Blender

便携包 `docs/03_跨电脑运行.md` 指明原机使用 Blender 4.5.16 LTS。已安装同版本，来源为 [Blender 官方发布目录](https://download.blender.org/release/Blender4.5/)，并与官方 SHA256 清单核对：

```text
23432b064977908beb1ab4b7f32f024e7331105c875c187dce002aff84b10c11
```

本机执行文件为 `/data/omi_runtime/tools/blender-4.5.16-linux-x64/blender`，命令入口为 `~/.local/bin/blender`，应用菜单入口为 `Blender 4.5 LTS (OMI)`。

```bash
blender --version
blender /data/omi_runtime/inputs/optical_packages_20261120_001316/optical_module_portable_20261119/models/connected_groove.blend
```

四个保存模型已在独立 Blender 后台进程中打开，检查通过：照片已内嵌、无外部 `.blend` 库引用，米制模型的单位比例为 1。照片初稿本身仍是未定标模型。报告位于 `/data/omi_runtime/runs/blender_validation_20261120/saved_models.json`。

## 实际可用的仿真资产

通过 Blender 对 `connected_groove.blend` 的实际求值几何导出 15 个部件，包括曲线转网格后的外观部分。以米为单位，保留部件颜色，生成 OBJ 和来源清单。导出不会保存修改到输入 `.blend`。

```bash
PACKAGE=/data/omi_runtime/inputs/optical_packages_20261120_001316/optical_module_portable_20261119
blender --background "$PACKAGE/models/connected_groove.blend" --disable-autoexec \
  --python-exit-code 1 --python scripts/simulation/export_blender_asset.py -- \
  --package "$PACKAGE" --output /data/omi_runtime/assets/optical_module_new
```

输出目录须不存在。已生成的本机资产位于 `/data/omi_runtime/assets/optical_module_sim_20261120/`。

## 场景生成与 MuJoCo

新环境为 `/data/omi_runtime/envs/simulation`，依赖见 `requirements/simulation.txt`，完整版本见 `requirements/simulation.lock.txt`。它与模型推理环境及 Isaac Sim 自带 Python 分开。

```bash
uv venv --python 3.11 --seed /data/omi_runtime/envs/simulation
uv pip install --python /data/omi_runtime/envs/simulation/bin/python -r requirements/simulation.txt
```

下面的目录均应使用新的名称：

```bash
SIMPY=/data/omi_runtime/envs/simulation/bin/python
"$SIMPY" scripts/simulation/build_scenes.py \
  --asset /data/omi_runtime/assets/optical_module_sim_20261120 \
  --output /data/omi_runtime/assets/new_scene --rows 1 --columns 1

MUJOCO_GL=egl "$SIMPY" scripts/simulation/run_mujoco.py \
  --scene /data/omi_runtime/assets/new_scene/scene.xml \
  --output /data/omi_runtime/runs/new_mujoco_scene
```

`build_scenes.py` 同时生成 MuJoCo 的 `scene.xml` 和 Isaac 可读取的 `scene.usda`，附带 `meshes/` 与 `scene_manifest.json`。`--rows 2 --columns 2` 可生成 2×2 方阵，当前最多 16 个模块。

MuJoCo 3.3.7 已实际完成单模块和 2×2 场景的加载、240 步／2 秒仿真、EGL 离屏渲染、落台接触与稳定性检查。结果分别位于：

- `/data/omi_runtime/runs/mujoco_optical_v3_20261120/`
- `/data/omi_runtime/runs/mujoco_optical_array_v2_20261120/`

各目录包含 `initial.png`、`settled.png`、状态轨迹和 `report.json`。

## Isaac Sim

本机存在 Isaac Sim 5.1.0 和 6.0.1。本轮使用 5.1.0 的自带 Python 与 PhysX CPU，采用本地扩展和无 RTX 渲染器的后台启动。启动器显式清除外部 Python/Conda 库路径，保持供应商 Python 运行时独立。

```bash
env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH \
  /data/isaac-sim-5.1.0/python.sh scripts/simulation/run_isaac.py \
  --isaac-root /data/isaac-sim-5.1.0 \
  --scene /data/omi_runtime/assets/optical_scene_v2_20261120/scene.usda \
  --output /data/omi_runtime/runs/new_isaac_scene
```

单模块和 2×2 方阵均已实际加载 USD、执行 240 步／2 秒 PhysX 仿真并验证下落、稳定和台面支撑。报告和保存的末态 USD 位于：

- `/data/omi_runtime/runs/isaac_optical_v3_20261120/`
- `/data/omi_runtime/runs/isaac_optical_array_20261120/`

本轮未运行 Isaac RTX 相机渲染，未做 Isaac/Blender GUI 交互验收。MuJoCo 的渲染图不能作为 Isaac 的渲染验收证据。

## 物理边界

- 外观使用真实建模资产，但碰撞采用刚性配准网格的单个包围盒，不保留凹槽的接触结构。
- 质量暂设 20 g，摩擦系数暂设 0.6；未做实物标定。
- 拉手等外观部件暂时刚性附着，未建柔性动力学。
- 支撑轨道是示意结构，并非根据真实夹具 CAD 重建。
- 这轮验证证明资源可导入、米制场景和基本刚体接触能运行，不证明插接、夹持、凹槽接触或跨引擎物理精度一致。

## 机械臂与夹爪资产

已阅读同级 `omi_proj` 的资源清单、仿真文档、模型回放记录和迁移清单。它们描述的是 Git 外资源；当前这份检出未包含 `local/`。

| 资源 | 相对 `omi_proj` 的预期位置 | 当前状态 |
| --- | --- | --- |
| Marvin 双臂 MJCF | `local/assets/robot_assets/mujoco/right_chopping_scene.xml` | 缺少 |
| 机械臂及基座网格 | `local/assets/MarvinCCS/`，与 `robot_assets/` 保持相邻 | 缺少 |
| Stand 派生 URDF、网格与来源 | `local/models/omi_marvin_stand_axis_corrected_v1/` | 缺少；原文仅作可视化对照，运动学和工具仍待核对 |
| 夹爪相关厂商资源 | `local/vendor/optical_module_pu/` | 缺少；收到后还需核实实际模型文件 |

机器可读记录见 `manifests/robot_assets.json`。Git 内自带的 `tianji_7dof_surrogate.xml` 只是接口测试代理，不能作为现场机械臂或夹爪模型。

完整资源到齐后，先核对 MJCF/URDF 引用的 mesh、关节、单位、惯量和工具坐标，再接入光模块场景。旧文档提到的刀具与灵巧手不能直接代替当前触觉夹爪。
