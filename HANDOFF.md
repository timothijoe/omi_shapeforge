# OMI ShapeForge 交接文档

交接更新日期：2026-11-20。主项目为本文所在的 `omi_shapeforge` 仓库，展示名 OMI ShapeForge。ENG-001 已保存本地源码基线并复验控制层与两项 GPU smoke；仿真和训练未重跑。原始完整交接快照保留不变。

## 1. 接手先读

1. [AGENTS.md](AGENTS.md)：分支、资源与验证约定。
2. [当前总览](docs/current.md)：全项目当前状态的唯一摘要。
3. [完整进展快照](docs/chronicles/2026-11-20-workspace-handoff.md)：全部环境、数据恢复、复现与仿真的详细交接记录。
4. [能力总表](docs/capabilities.md)：已运行、未接入和未验收的区别。
5. [教程目录](tutorials/README.md)及[资源清单](manifests/README.md)：按任务定位真实命令和输入。

本文是接续工作的导航与注意事项。能力细节由领域纪传体维护，后续变化更新 current／evolution 并追加阶段记录，不回写旧报告或旧编年。

## 2. 用户目标与开发分工

目标是继续光模块感知、模型与点云配准，并在 Isaac Sim 和 MuJoCo 中建立可追溯仿真场景，逐步接入已有机械臂、夹爪和夹具资产。

主项目承载流程、配置、评估、文档及仿真脚本；同级自有 FoundationStereo／BundleSDF 仓库承载对应算法实现。`omi_proj` 提供机器人资产、资料及离线预检；本项目没有调用其硬件控制系统。

用户偏好中文交流，希望助手实际执行建模、验证和可视化。HTML 操作采用左键旋转、Shift+左键平移和滚轮缩放，不要求鼠标中键；浏览器交互本身尚未验收。

## 3. Git 状态与可恢复基线

- `main` 继续保持空树；本地 `dev` 已整合原仿真、知识库及本轮源码基线，后续从 `dev` 建功能分支。
- ShapeForge 的已验证源码提交为 `eb8da42`；此后的交付提交只更新文档和小型元数据。准确交付 HEAD 用 `git rev-parse dev` 查看，完整记录见[源码基线](docs/design/source-baseline.md)。
- FoundationStereo 的适配与入口保存为 `e46fa7098730674bfc9f96047b4d2ffe9a87e1b4`；BundleSDF 保存为 `b1a55878264e8c28841507bb578835c94a63d475`，均位于各自 `feature/local-runtime-baseline`。
- omi_proj 保持 `963a7c29f8e39bff59ba4eb285693976b224961e`，没有修改其代码。
- 原有未提交文件已保存为本地提交，包含 PROMPTS 原文；四个仓库另有 Git bundle，且已独立克隆核对。整理前补丁、原文件与 Git 历史保存在外部备份中。
- 尚未 push，不能假定远端 dev／后端默认分支包含本轮提交。首次恢复使用[基线清单](manifests/source_baseline_20261120.json)与 bundle，再配置外部环境和资源。

当前状态以 `git status --short --branch` 为准；保留后续用户工作树，不执行 reset／clean。旧交接中的“未提交”描述属于当时快照，不能继续用作当前结论。

## 4. 数据已经齐全恢复，不要再按“缺包”处理

目前 00–05 加 OMI／portable／quick 共 9 个上传包均已解压，原包保留在 `/data/nov_19_folder`。以[最终解压索引](manifests/extracted_archives.json)为准，早期报告中的“未到达／未解压”仅代表当时状态。

```text
/data/omi_runtime/
  baselines/reconstruction_20261119/
    workspace/BundleSDF_trial/                 旧自定义工程、模型及 02 data
    workspace/FoundationStereo/               旧工程与 03 DATA
    environment_runtime/foundation_stereo/     04 旧 Conda 环境，未重定位
  baselines/omi_transfer_20261120_004618/
    omi_proj/local/                           机器人资产、示范和权重
  inputs/optical_packages_20261120_001316/
    optical_module_portable_20261119/
    optical_module_quick/
  envs/                                       当前使用的独立环境
  assets/                                     导出的光模块及单模块／方阵场景
  tools/                                      Blender 等工具
  runs/                                       日志、报告、渲染图与新实验输出
```

当前工作区的 `omi_proj/local` 指向上述 OMI 基线 local。恢复内容没有覆盖现有 Git 源码。重建基线与当前算法开发目录独立；历史 JSON 的旧机器来源路径保留，实际运行应使用显式输入参数或受控路径映射。

02 的 2,121 个成员、03 的 397 个成员、04 的 61,829 个条目全部恢复校验通过。04 的 1,154 个内部链接无缺失目标，03 补齐一个大小写别名。检查时 `/data` 剩余约 55 GiB，未删除源包。

## 5. 环境与最小接续检查

以下相对 envs 目录均位于 `/data/omi_runtime`：

| 用途 | 环境／版本 |
| --- | --- |
| 主调度器 | 仓库 .venv；Python 3.11.15；标准库控制层 |
| 双目／BundleSDF 组件 | envs/foundation_stereo、envs/bundlesdf；Python 3.11、Torch 2.6.0+cu124 |
| 光模块仿真 | envs/simulation；Python 3.11、MuJoCo 3.3.7、OpenUSD 26.11 |
| 机械臂资产预检 | envs/omi_assets；Python 3.12、MuJoCo 3.15.0、NumPy 2.5.3 |
| Blender | 4.5.16 LTS；已建立 blender 命令和应用菜单入口 |
| Isaac | 5.1.0 自带 python.sh 验证过；另装有 6.0.1，但未用其验收场景 |

**04 不等于当前开发环境。** 它是 Python 3.11.18／Torch 2.7.1+cu128 的历史快照，尚未执行 conda-unpack、激活或运行兼容性验收；继续使用当前 envs 不以适配旧环境为前置条件。

从仓库根目录先做只读检查：

```bash
git status --short --branch
.venv/bin/omi-shapeforge --help
.venv/bin/omi-shapeforge doctor
```

doctor 仅检查路径、解释器、权重／nvcc 是否存在并显示 Git 信息，不检查全部动态库、GPU 运算、仿真或机器人。主配置为 `configs/workspace.toml`，机器覆盖可用忽略的 local.toml。真正运行前按[教程](tutorials/README.md)选择对应环境和新输出目录。

## 6. 已有本机验证与关键限制

- 官方双目样例：960×540、32 次迭代，470,018 点；两进程视差和深度一致。不是光模块原始录制的重算。
- BundleSDF 组件：C++、CUDA 采样／编码与梯度、PyTorch3D、Kaolin、Warp、真实 LoFTR 检查通过；LoFTR 2,893 组匹配。不是完整视频在线跟踪／重建验收。
- 已确认 ROI 配准：10 万点场景，486 原始点／472 过滤点／121 检查点；检查残差中位数约 0.148 mm、P90 约 0.731 mm，全部原始点 P90 约 2.771 mm。残差不是实物位姿精度，方向仍有近似多解；旧误选目标已撤回。
- V2 回放：64 个源文件及冻结几何检查通过，粗／细差约 1.83e-9／1.77e-9 m。回放参数和保存位移，不是从新传感器重新估计。
- Blender：四份模型后台重开、内嵌资源／单位检查，一张后台渲染及 15 部件导出通过；完整 photo／metric／groove 生成和 59 帧尺寸重估未在本机复跑。
- 光模块仿真：单模块及 2×2 在 MuJoCo 完成 EGL 渲染与 240 步落台，Isaac 5.1 完成对应 PhysX CPU 测试。碰撞是盒，20 g／摩擦 0.6 为假设，拉手刚性附着，轨道为示意；不证明精细夹持／插接。
- 机器人：双臂 MJCF 编译、A 臂 preflight 和静态渲染通过；两份完整 URDF 各有 27 links／26 joints，含四个滑动指关节，网格引用齐全。旧 MJCF 的灵巧手／刀具不等于当前夹爪配置；指关节 velocity=0、TCP、轴、惯量和限位仍需核对。
- OMI 数据：9 个正常原始回合、41 片段、1499 样本，原划分 1174／325；动作是 6 维末端增量且 no_gripper=true，不可直接当 7 维关节／夹爪动作标签。BC6148 用过全部 1499 条，旧验证划分不是该权重的独立测试。

机器人尚未接入光模块场景或 Isaac 机器人任务；本机未运行完整 OMI 数据／Actor 验证与重新训练。Isaac RTX、GUI 交互、真实精度及真机动作均未验收。

主要证据：[初始化](manifests/initial_validation.json)、[便携配准](manifests/portable_validation.json)、[仿真](manifests/simulation_validation.json)、[旧工程／OMI／V2](manifests/transfer_validation.json)、[02 恢复](manifests/restored_data02.json)、[03／04](manifests/data03_04_validation.json)。旧报告保持原样，当前资源状态由最终解压索引和资源清单说明。

## 7. 建议接续顺序

1. 先读源码基线和对应能力文档，检查实际工作树；数据已到齐，不必继续等待 03／04 或重复整包解压。
2. 源码保存已完成；下一项 ENG-002 定版任务记录、产物合同及旧报告适配，再推进共用运行层。
3. 复现路线：从一个固定真实双目样本开始，核对输出和坐标，再推进局部重建、59 帧尺寸或完整跟踪，各项单独验收。
4. 仿真路线：先选择准确机器人／工具配置，核对关节与 TCP，再组合光模块和真实夹具，重建能保留槽接触的碰撞体；不能直接把示意轨道和单盒当最终任务场景。
5. GUI／RTX、完整 Blender 生成、OMI Actor／数据合同及训练是独立待办，需要运行证据才能更新状态。

所有新实验使用新目录；保留 V1／V2／V2.1 和原始数据，不擅自升级全项目版本名。没有连接硬件或执行真实控制的授权记录，不从其他仓库顺手启动控制脚本。本轮基线已本地提交，尚未推送。
