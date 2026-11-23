# 双目与后端组件

## 架构和入口

`workspace.py` 读取 TOML，`workflows.py` 准备输入与后端命令，`runner.py` 管理独立进程和 v1 记录。标准输出与错误写 `run.log`，原 report 及数组位于 backend/；零退出码还需文件、哈希、内容与限定任务指标通过。检查器在后端环境运行，控制层仍只用标准库。

| 主入口 | 后端实际入口 | 结果范围 |
| --- | --- | --- |
| `omi-shapeforge smoke stereo` | FoundationStereo 的 `scripts/run_local_smoke.py` | 官方左右图 → 视差／米制深度／点云 |
| `omi-shapeforge smoke bundlesdf` | BundleSDF 的 `smoke_local.py` | C++、CUDA、几何组件和 LoFTR 样例 |

后端入口路径由配置决定。环境隔离决定见 [ADR 001](../decisions/001-backend-processes.md)，操作见[双目教程](../../../../tutorials/stereo_sample.md)。

## 当前验证

本机使用 Python 3.11、PyTorch 2.6.0+cu124、NumPy 1.26.4 和 RTX 4090。FoundationStereo 加载已核对 SHA256 的 11-33-40 模型，使用仓库 `assets/left.png`、`right.png`、`K.txt`：960×540，32 次迭代，输出 470,018 点。初次独立前向约 1.59 秒，仅作本机单样本运行记录；不是通用性能基准。第二进程生成的视差与深度数组逐元素一致。

BundleSDF 检查覆盖 C++ YAML 绑定、CUDA 占用区间采样、哈希编码及梯度、SO(3) 往返、PyTorch3D CUDA 最近邻与梯度、Kaolin 八叉树、Warp GPU 内核，以及真实图像 LoFTR。该图像缩放为 640×448，得到 2,893 组匹配，垂直差中位数约 0.197 像素。主项目两个调度入口实际运行记录见[初始化验证](../../../../manifests/initial_validation.json)。

## 源码适配和约束

FoundationStereo 使用仓库内 DINOv2，严格加载完整 checkpoint；样例关闭会被完整 checkpoint 覆盖的 EdgeNeXt 初始权重下载，并显式处理 PyTorch checkpoint 的 NumPy 元数据。

BundleSDF 适配了现代 PCL 指针、头文件、pybind11 与 CUDA 构建，并修复 LoFTR NCHW 通道判断。本机采用传统 OpenCV 描述子匹配的 CPU 编译选项；LoFTR 和对应 CUDA 核仍走 GPU。传统描述子视频路径尚未验收。

原[后端来源快照](../../../../manifests/backends.lock.json)保留初始化时点。ENG-001 已将全部现有适配与两个入口分别提交为 FoundationStereo `e46fa70`、BundleSDF `b1a5587`，并通过 bundle 独立克隆核对；见[源码基线](../../../design/source-baseline.md)。新跑官方双目仍输出 470,018 点，BundleSDF 组件得到 2,893 组 LoFTR 匹配，运行清单对应干净的主项目 `eb8da42` 与上述后端版本。

提交与 bundle 尚未推送；本轮验证使用既有环境与原生扩展，不代表从零重编译通过。新[基线清单](../../../../manifests/source_baseline_20261120.json)记录源码版本、恢复证据和运行报告，仍不是运行时强制版本锁或自动部署方案。

## 已知限制

ENG-003 已接入[运行合同 v1](../../interfaces/run-contract.md)，两项新 smoke 的进程、产物和验收均通过，v1 清单也通过离线结构与关系检查；见[运行验证](../../../../manifests/workflow_validation_20261120.json)。双目仍为 470,018 点，LoFTR 仍为 2,893 组匹配；没有扩展到完整重建。旧格式批量转换器尚未实现。

该阶段没有重新运行旧光模块的原始左右 IR／全部录制，没有外部深度真值比较，也没有完成官方 BundleSDF 视频在线跟踪与 textured mesh 全链路。组件成功不能推导这些能力已通过。旧机 PyTorch 2.7.1+cu128 的恢复结果属于原交接背景。

历史见[本机基线阶段](../chronicles/2026-11-19-backend-baseline.md)。

## 新增真实光模块双目样本推理（2026-11-21）

已对近距离光模块录制中的 11 对 1280×720 左右 IR 图重新运行 FoundationStereo，含反向一致性检查共 22 次前向；米制深度用于新的点云位姿匹配和 RGB 轮廓联合精修。后端入口为 `scripts/run_stereo_pose_inputs.py`，新结果在 `/data/omi_runtime/runs/stereo_pixel_pose_20261121/fresh_stereo`。不覆盖旧缓存，不等同于全 59 帧重建或实物精度验证，详见[阶段记录](../chronicles/2026-11-21-stereo-cloud-pixel-trial.md)。
