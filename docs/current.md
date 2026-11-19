# 当前状态

初始化日期：2026-11-19。

主项目骨架已建立，包括 Python 包、命令入口、同级后端配置、Git 来源记录、独立运行目录和调度测试。当前为本地 Git 仓库，GitHub 远端尚未创建或关联。

主项目入口已通过实际验证：`doctor` 检查通过，`smoke stereo` 和 `smoke bundlesdf` 均成功调用各自 GPU 环境并保存有效报告。4 项控制层测试通过，覆盖已有结果保护、失败记录、缺失结果报告及配置路径处理。验证记录见 `../manifests/initial_validation.json`。

此前已验证的本机基础能力：

- FoundationStereo 官方 960×540 样例成功，输出约 47 万个点；两次视差和深度数组一致。
- BundleSDF 的 C++ 绑定、CUDA 射线采样、哈希编码与梯度、PyTorch3D CUDA 最近邻、Kaolin 八叉树、Warp GPU 内核通过检查；LoFTR 得到 2,893 组匹配。
- 项目 EGL 离屏渲染和两套 GPU 环境的依赖检查通过。

这些结果的原始报告保存在 `/data/omi_runtime/runs/`。由主项目调度生成的新报告位于 `/data/omi_runtime/runs/omi_shapeforge/`，每次运行单独记录配置与版本。

尚未完成的工作：旧光模块实验复现、真实视频完整跟踪与重建、旧自定义工程的迁入。相关资产和小样本需等待 01 工程包；后续完整原始数据实验还需要 02、03 数据包。
