# 双目与后端组件

## 架构和入口

`src/omi_shapeforge/workspace.py` 读取工作区 TOML，选定后端解释器，以参数列表启动独立 Python 进程。标准输出与错误写 `run.log`，实际版本写 `run_manifest.json`；零退出码仍须有正确状态的 `report.json` 才能通过。

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

[后端来源快照](../../../../manifests/backends.lock.json)中的 HEAD 不包含这些全部本地修改。运行清单记录实际工作树，但不保存补丁内容；它不是自动版本锁或部署方案。

## 已知限制

该阶段没有重新运行旧光模块的原始左右 IR／全部录制，没有外部深度真值比较，也没有完成官方 BundleSDF 视频在线跟踪与 textured mesh 全链路。组件成功不能推导这些能力已通过。旧机 PyTorch 2.7.1+cu128 的恢复结果属于原交接背景。

历史见[本机基线阶段](../chronicles/2026-11-19-backend-baseline.md)。
