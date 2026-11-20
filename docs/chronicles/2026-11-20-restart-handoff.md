# 2026-11-20：重启前完整接续交接

本记录承接[早期工作区交接](2026-11-20-workspace-handoff.md)，补齐其后的工程规范化、运行层、可视化、原生查看及 Blender V3 决定。旧快照保留原时点结论；当前摘要仍以 [current](../current.md) 和领域能力文档为准。

本轮只完成会话保存、文档与备份，不重复运行 GPU／物理实验，也没有执行重启或推送。

## 1. 接续时最重要的决定

用户正式指定：**Blender 模型线叫 V3，以 Blender 为主要编辑工具，V2 作为 V3 的辅助参考和对比。**

- 主资产 `OM-001/V3`，当前修订 r01；旧目录名 `OM-001/GROOVE-r01` 保留为兼容别名。
- V3 工作文件：`/data/omi_runtime/assets/optical_module_v3/work/OM-001-V3.blend`。
- V3-r01 冻结副本：`/data/omi_runtime/assets/optical_module_v3/releases/r01/OM-001-V3-r01.blend`。
- 原迁移文件：`/data/omi_runtime/inputs/optical_packages_20261120_001316/optical_module_portable_20261119/models/connected_groove.blend`。
- 三者登记时相同 SHA256：`016ac93da1f252e2f13325ac20454d1a02b82e31a840ac4f95bffa4218d0b8d2`。本轮重启前磁盘工作文件仍匹配该值。
- V2 是结构先验结合观测细化的历史路线；Open3D 当前加载它作参考。`v2_reference.blend` 是参考封装，不能因扩展名为 blend 就当成新照片建模路线。
- V3 路线从照片稿、米制尺寸稿演进到连通槽模型；局部槽结构参考了 V2，因此当前 V3 不是完全独立于 V2 的几何。
- 名称决定没有改变几何或认证实物尺寸，也不改变 Python 包版本。原 V1／V2／V2.1、照片稿和尺寸稿保留。

版本、父子关系和实例身份见[资产版本](../asset-versions.md)、[资产登记](../../manifests/optical_assets.json)与 [ADR 002](../agent/simulation/decisions/002-blender-v3-primary.md)。未来编辑 V3 工作副本，形成新几何时冻结 r02／r03，重新导出到新目录并验证。

## 2. 本轮已经完成的工程工作

| 工作包 | 交付与证据 |
| --- | --- |
| ENG-001 源码基线 | 保存主项目原未提交文档与后端适配；四库 bundle 验证、独立克隆；原工作区及恢复副本的控制层测试通过；[基线说明](../design/source-baseline.md) |
| ENG-002 合同 v1 | 分开 execution、validation、acceptance；三项流程规则、11 个示例、27 个反例；严格 JSON 检查；[合同](../agent/interfaces/run-contract.md) |
| ENG-003 共用运行层 | runner/workflows、原子记录、独占输出、进程组中断与后代回收；两个 smoke 迁移，新增 simulate mujoco；14 项控制层测试及三项实跑通过；[最终证据](../../manifests/workflow_final_validation_20261120.json) |
| 全部历史图册 | 2,496 个可视化文件、78 组，按实验生成外部图册；保留旧结果和失败尝试；[目录](../visual-results.md) |
| 模型对照 | 四模型真实求值几何、部件名称和实例编号；当前标记 V3 主模型／V2 辅助，默认选 V3；原模型哈希未变 |
| 桌面兼容 | 实际 Chrome 无 WebGL，最初测试用了软件 WebGL，导致桌面空白；现已增加 CPU 逐像素深度渲染后备并在真实桌面确认；[记录](../../manifests/viewer_compatibility_validation_20261120.json) |
| 原生查看 | 恢复旧机 Open3D GUI，历史 V2 mesh 实际显示，可使用原有 V1 切换、点云叠加与局部放大入口；[教程](../../tutorials/native_mesh_viewer.md) |
| Blender V3 | 已在实际桌面打开 V3 工作文件、显示 15 部件；建立工作副本与冻结副本；[指定记录](../../manifests/asset_v3_designation_20261120.json) |

## 3. 代码状态与本地备份

交接前主项目功能基线是 `9e14cbeb525bb02b5a8f9077655d23e440505c09`（V3 主线决定），本次交接最终提交将是它的后代；准确 HEAD 看 `git rev-parse dev`，或本轮外部备份的 `delivery.json`，避免文档自引用提交号。

| 仓库 | 分支 | 功能版本 |
| --- | --- | --- |
| omi_shapeforge | 本地 dev；本次由 docs/restart-handoff 整理并 fast-forward 汇入 | 9e14cbe 加本轮交接提交 |
| FoundationStereo | feature/local-runtime-baseline | e46fa7098730674bfc9f96047b4d2ffe9a87e1b4 |
| BundleSDF | feature/local-runtime-baseline | b1a55878264e8c28841507bb578835c94a63d475 |
| omi_proj | oct_26_branch | 963a7c29f8e39bff59ba4eb285693976b224961e |

功能基线核对时四个工作树均干净。主项目 dev 当时领先本地 origin/dev 14 个提交；加交接提交后会变化。没有推送或刷新远端引用，不能把本地 ahead 数当作实时 GitHub 状态。`main` 保持空树；两个后端原 master 保留。

本轮持久备份目录：

```text
/data/omi_runtime/baselines/restart_handoff_20261120T043105Z/
  V3-live-session.blend             已打开 Blender 会话的独立保存副本
  V3-working-file-before.blend      保存会话前的磁盘工作文件副本
  blender-session.json              copy=True 保存回执
  session_reopen_validation.json    两个文件重开与可见求值几何对比
  comparison-fragment.html          最新 V3／V2 对照的独立备份
  comparison-desktop.html           桌面可打开的对照备份
  repositories_before.json         本次交接开始时的代码版本
  <仓库>.bundle                    本次最终 Git 源码历史备份
  delivery.json                     最终提交、bundle 哈希及验证回执
```

旧源码恢复目录 `/data/omi_runtime/baselines/source_baseline_20261120T014740Z/` 仍在；其中的主项目 source.bundle／delivery.bundle 只覆盖早期阶段。恢复最新代码优先使用本轮 bundle，不能用早期 bundle 覆盖当前 dev。

bundle 不包含外部环境、数据、模型工作目录及全部历史输出。重启同一机器无需重新克隆；只有源码损坏或搬迁时才考虑从 bundle 克隆到新目录。

## 4. Blender 未保存会话已经留存

交接检查发现 Blender 标题带星号，`bpy.data.is_dirty=true`。通过当前会话执行 `save_as_mainfile(copy=True)`，成功写入本轮备份中的 `V3-live-session.blend`；原 V3 工作文件路径与内容没有覆盖，当前会话仍显示 dirty。回执保存时间为 2026-11-20 04:43:43 UTC（上海时间 12:43:43）。

两个文件均通过独立后台重开；对所有未隐藏渲染的 MESH／CURVE 求值并应用世界变换后，可见几何摘要完全一致。没有穷举对比隐藏对象、材质、全部场景设置或 UI 差异；会话副本整体保留作为恢复点。

重启后需要恢复窗口会话时先打开 **V3-live-session.blend**；继续开发时再另存到 V3 工作目录或新修订，保持冻结 r01 和本次备份可追溯。如果用户在上述保存时间之后继续编辑，需要在重启前另存最新文件；本次快照不会自动追踪后续操作。

## 5. 最新运行证据与范围

最终已验证运行代码提交为 `b3aa2fbefff2eb2d94bdebcf20de8926cfcd6f8d`，其后的模型命名、查看兼容和交接记录没有修改调度代码。新输出位于：

`/data/omi_runtime/runs/eng003_final_20261120T023314Z/`

- control_tests.log：14 项控制层测试通过，覆盖失败记录、输出保护、输入改变、链接逃逸，以及主进程退出后忽略 SIGINT 的后代回收。
- stereo/：官方 960×540、32 次迭代，470,018 点；执行／产物／限定验收通过。
- bundlesdf/：2,893 组 LoFTR 匹配及 C++／CUDA 等组件检查；三项结果通过。
- mujoco/：2×2 简化场景、240 步；重新读取末态，核对落差、碰撞底部、接触和速度，三项结果通过。
- 三份 v1 清单通过合同结构与字段关系检查。另在复制目录注入损坏深度／未静止状态，正确触发内容失败／验收失败，原结果保留。

v1 文件布局：运行目录下 `run_manifest.json`、`run.log`、`inspection.log`；后端原 report、图像、数组及 inspection.json 在 `backend/`。不要再读取旧顶层 status／output 字段判断新清单。

这些调用复用了现有环境与编译扩展，不是从零编译验收；官方样例、组件、已知 ROI 配准、冻结回放与完整重建分别验收。

## 6. 环境、数据与资产位置

源码根目录 `/home/linux/omi_folder`，资源根目录 `/data/omi_runtime`，原上传包 `/data/nov_19_folder`。9 个包已恢复，不要重复等包或整包解压。`omi_proj/local` 指向 `/data/omi_runtime/baselines/omi_transfer_20261120_004618/omi_proj/local`。

| 用途 | 运行环境 |
| --- | --- |
| 控制层 | omi_shapeforge/.venv，Python 3.11，仅标准库 |
| 双目 | /data/omi_runtime/envs/foundation_stereo，Torch 2.6.0+cu124、Open3D 0.19 |
| BundleSDF | /data/omi_runtime/envs/bundlesdf，Torch 2.6.0+cu124 |
| 光模块仿真 | /data/omi_runtime/envs/simulation，MuJoCo 3.3.7、OpenUSD |
| 机器人离线预检 | /data/omi_runtime/envs/omi_assets，Python 3.12、MuJoCo 3.15 |
| Blender | /data/omi_runtime/tools/blender-4.5.16-linux-x64/blender；本机 blender 命令可用 |
| Isaac | /data/isaac-sim-5.1.0/python.sh；6.0.1 未用于当前验收 |

04 旧 Conda 环境保持历史快照，未 conda-unpack／激活，不作为当前开发前提。主配置为 `configs/workspace.toml`；ignored local.toml 由显式 --config 选择，不是自动合并层。

网页对照原入口 `/data/omi_runtime/runs/optical_asset_versions_20261120/preview.html`，内嵌源 `/home/linux/omi_folder/work/visualizations/optical-module-versions.html`，本轮备份也能恢复。完整图册索引 `/data/omi_runtime/runs/asset_visual_catalog_20261120T020714Z/inventory.json`，项目入口 [visual-results.md](../visual-results.md)。

`/data` 检查时剩余约 55 GiB，没有删除源包。详细资源来源与恢复方法见 [resources.json](../../manifests/resources.json)。

## 7. 重启与下一步

实际可复制的启动命令统一放在[重启后恢复教程](../../tutorials/restart_resume.md)。GUI 窗口、PID、窗口 ID、`/tmp/omi-*` 标记可能在重启后消失；文档和本轮备份都使用持久绝对路径，不靠旧 PID 恢复。

接续优先级：

1. 检查持久文件和工作树，恢复所需 Blender V3 会话；确认主模型 V3、辅助 V2 的决定。
2. 工程任务 ENG-004：CPU 测试与合同检查接入自动流程，规范 GPU／仿真证据关联；当前尚未建立 CI。
3. 资产工作以 Blender V3 为主，形成明确编辑任务、参考 V2 作对比；修改外形后同步碰撞来源与导出流程，不能继续沿用旧单盒代表槽接触。
4. 真实双目样本闭环、完整重建、59 帧尺寸重新估计、机器人／夹具／TCP、OMI 数据与 Actor 检查分别立项；用户未指定下一项几何修改。

当前未验收：精细夹持／插接、实物位姿或尺寸精度、Isaac RTX／GUI 交互、机器人与光模块任务组合、完整视频在线重建及 BC／RL 重训。没有连接或控制真机的授权记录。重启不应自动触发推理、训练、Isaac 或硬件脚本。
