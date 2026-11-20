# 项目能力总表

此表按证据范围分类，不以“文件存在”代替运行验证。

| 能力 | 实现与已验证状态 | 主要限制／证据入口 |
| --- | --- | --- |
| 工作区诊断 | CLI 已运行，检查路径、解释器及 Git 信息 | 不验证 GPU、动态库或全部资产；[接口](agent/interfaces/cli.md) |
| 样例进程调度 | 两个 smoke 与 MuJoCo 已经 v1 共用运行层实际执行；14 项控制层测试通过 | 三项新工作流的执行、内容检查与限定验收通过；尚未推送或从零重编译；[能力](agent/perception/evolution/stereo-and-backends.md) |
| 双目深度与点云 | 官方 960×540 样例，约 47 万点；两次独立推理数组一致 | 不是光模块原始录包或外部深度真值验收 |
| BundleSDF 基础组件 | C++ 绑定、CUDA 编码／采样、梯度、Kaolin、Warp、LoFTR 检查通过 | 不代表完整视频跟踪和 mesh 重建通过 |
| 光模块 CPU 配准 | 10 万点样例中已确认区域的刚体配准及独立检查通过 | 已知 ROI／方向先验；残差不是真实位姿误差；[能力](agent/perception/evolution/confirmed-registration.md) |
| Blender 保存模型 | 四份模型重开、内嵌资源／单位检查与一张后台渲染通过 | 照片初稿未定标；照片／尺寸／槽的完整重新构建未在本机复验 |
| 仿真资产导出 | 当前米制模型实际导出 15 个外观部件 | 颜色近似，原始复杂材质和柔性不完整保留；[能力](agent/simulation/evolution/asset-pipeline.md) |
| MuJoCo 场景 | 单模块及 2×2：加载、240 步、落台稳定、EGL 图像通过 | 包围盒碰撞，20 g／摩擦 0.6 为假设；[能力](agent/simulation/evolution/engine-scenes.md) |
| Isaac Sim 场景 | 5.1.0 的本地 USD 与 PhysX CPU：单模块及 2×2 运行通过 | 无 RTX 图像或 GUI 交互验收 |
| 机械臂与夹爪资产 | OMI 资源包已恢复；双臂 MJCF 编译、预检、静态渲染通过；完整 URDF 含滑动指关节且网格引用齐全 | 未接入当前光模块场景，工具／惯量／限位未实物校准；[资源](agent/simulation/evolution/robot-assets.md) |
| 数据／环境归档恢复 | 9 个包均已解压，02／03 全部成员恢复和代表数据检查通过，04 链接完整 | 04 未重定位或运行验收；[数据与回放](agent/perception/evolution/data-and-replay.md) |
| V2 冻结几何回放 | 01 包恢复后实际执行，64 个源文件校验及粗／细几何比较通过 | 不从原始传感器重新估计；[迁移验证](../manifests/transfer_validation.json) |
| 全场景自动识别、59 帧尺寸重估、完整在线重建 | 当前项目未验收 | 数据已恢复，仍需入口适配和逐阶段重跑／独立验收 |
| 真机控制和生产操作 | 本项目未接入 | 不把其他仓库的控制记录当成本项目能力 |

历史阶段见[感知编年](agent/perception/chronicles/README.md)和[仿真编年](agent/simulation/chronicles/README.md)。
