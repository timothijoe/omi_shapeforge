# 当前状态

初始化日期：2026-11-19。

主项目骨架已建立，包括 Python 包、命令入口、同级后端配置、Git 来源记录、独立运行目录和调度测试。已关联 GitHub 远端 `git@github.com:timothijoe/omi_shapeforge.git`；`main` 只保留空提交，代码在 `dev`，后续功能在新建开发分支中迭代。

主项目入口已通过实际验证：`doctor` 检查通过，`smoke stereo` 和 `smoke bundlesdf` 均成功调用各自 GPU 环境并保存有效报告。4 项控制层测试通过，覆盖已有结果保护、失败记录、缺失结果报告及配置路径处理。验证记录见 `../manifests/initial_validation.json`。

此前已验证的本机基础能力：

- FoundationStereo 官方 960×540 样例成功，输出约 47 万个点；两次视差和深度数组一致。
- BundleSDF 的 C++ 绑定、CUDA 射线采样、哈希编码与梯度、PyTorch3D CUDA 最近邻、Kaolin 八叉树、Warp GPU 内核通过检查；LoFTR 得到 2,893 组匹配。
- 项目 EGL 离屏渲染和两套 GPU 环境的依赖检查通过。

这些结果的原始报告保存在 `/data/omi_runtime/runs/`。由主项目调度生成的新报告位于 `/data/omi_runtime/runs/omi_shapeforge/`，每次运行单独记录配置与版本。

2026-11-20 已收到光模块 portable/quick 两包。哈希校验通过，便携包的已圈选目标刚体配准在当前机器实际重跑并通过独立检查，检查点中位数约 0.148 mm、P90 约 0.731 mm，与旧参考一致；这些是表面残差，不是实物位姿真值误差。报告位于 `/data/omi_runtime/runs/optical_portable_20261120_001316/inspection_report.json`。

Blender 4.5.16 LTS 已安装，四份模型的后台重开与内嵌资源检查通过，当前连通槽模型已完成一张后台渲染。已导出 15 个可视部件，并生成同源的单模块及 2×2 光模块场景。MuJoCo 3.3.7 的加载、240 步刚体落台及离屏渲染通过；Isaac Sim 5.1.0 的本地 USD 加载和 PhysX CPU 落台通过，未验证 Isaac RTX 渲染。入口、版本和物理简化见 [Blender 与仿真原型](simulation.md)，结果索引见 `../manifests/simulation_validation.json`。

已核对同级 `omi_proj` 的文档与资源清单，但机械臂/夹爪的 Git 外 `local/` 资源尚未出现在本机相应目录，见 `../manifests/robot_assets.json`。当前仿真未接入这些真实机器人资产。

尚未完成的工作：完整 59 帧尺寸重估、真实视频完整跟踪与重建、旧自定义工程的迁入，以及机器人/真实夹具接入。完整工程仍需 01 包，后续原始数据实验还需要 02、03 数据包。
