# GPU PhysX兼容模式

2026-11-24，用户询问能否使用GPU物理。本阶段在固定WG-r10＋OM-r08插入场景上启用GPU动力学与GPU broadphase，保留PGS、20个5 ms物理子步、原厂IK、原接触门控和真实双相机。SDK／几何／摩擦／驱动参数未改，没有连接真机或重训BC／RL。

## 接入与实际执行证据

worker和批量研究入口新增`--physics-device cpu|gpu`，默认仍为CPU。GPU选项在attach场景前写入`physxScene:enableGPUDynamics=true`与`broadphaseType=GPU`。这两项是物理场景设置，与RTX相机使用GPU不同。

启动后查询原生`IPhysxStatistics`的场景统计。GPU试验中，求解器GPU heap为22,257,616 bytes，关节仿真GPU heap为858,472 bytes，broadphase GPU heap为8,586,616 bytes。生产入口同时检查配置与原生求解器／关节GPU统计；请求GPU却没有这些执行证据时直接报错，CPU请求出现GPU求解器也报错。`physics_backend.json`和worker metadata保存实际证据，不以渲染显存占用判断物理设备。

这是**GPU物理＋CPU回读兼容模式**。当前tensor frontend仍是NumPy，原生tensor设备报告`cpu`、ordinal −1；控制状态、逐子步胶垫读数、接触报告、SDK IK及图像处理保留CPU路径。引擎GPU求解器存在与NumPy数据驻留CPU不矛盾。本阶段没有实现CUDA张量常驻、多环境向量化或tiled camera。

GPU执行合同新增`physics_backend.version=physx-gpu-host-readback-v1`，明确动力学设备、broadphase与frontend。CPU保留旧执行合同字段布局。旧CPU数据、检查点及成功率不被重新标记为GPU结果。

## 实际闭环与同批计时

GPU模式正常91000、+1 mm受阻恢复91001、−1 mm受阻恢复91002分别388／572／575步成功，最终深度均约51.281 mm。恢复案例均实际受阻，并完成退出、重对准和重插；每例一次reset。CPU同配置正常91000为388步成功。GPU／CPU两组的client、shutdown和worker全部退出0。

串行、单环境、真实双RGB、同一20子步及PGS配置，以正常回合排除最初10步后的均值比较：

| 每控制动作耗时 | CPU动力学＋MBP | GPU动力学＋GPU broadphase，CPU回读 |
| --- | --- | --- |
| 20子步物理循环 | 23.666 ms | 69.229 ms |
| 原厂IK | 0.568 ms | 0.567 ms |
| 完整step RPC | 64.707 ms | 111.180 ms |

当前GPU兼容模式物理循环约慢2.93倍，完整step约慢1.72倍。因此本阶段提供可选GPU路径，生产默认仍使用CPU，不将“GPU开关已接入”表述为“吞吐已改善”。这一组CPU计时比上一阶段69～71 ms略低；表中采用同批复测值，原历史记录保留。

同种子正常轨迹的最大控制时刻TCP位置分量差约0.01097 mm，最大深度差0.01097 mm、关节位置差约0.00003982 rad；接触力及奖励也有差异。两种后端均通过任务判据，但没有逐值物理等价性承诺。GPU的±偏移恢复比此前CPU参考各少一步，也保留原始结果。

轻量测试75项中21通过、54因可选依赖跳过；新增检查覆盖GPU配置不匹配、原生求解器证据缺失、错误CPU／GPU执行状态。真实后端验证独立于这些配置测试。正式生产入口以`--physics-device gpu`另跑正常回合：388步成功、step RPC均值110.584 ms，原生GPU执行证据和新合同均核对通过，client／shutdown／worker全部退出0。

## 使用

在原有worker或批量研究命令后添加：

```bash
--physics-device gpu
```

其余选项继续适用，例如`--physics-substeps 20 --ik-backend tianji --tianji-sdk <Arm_control>`。原厂SDK配置见[原厂IK操作说明](../../../../tutorials/tianji_native_ik.md)。输出目录必须新建；GPU物理轨迹可能与CPU不同，不能将新后端当作逐值等价替换。

## 性能解释边界

本次先检查既有单环境接触任务能否迁移，保留了每动作20次`simulate/fetch`、逐子步CPU读取以及CPU控制／接触判定。GPU求解在这种小场景里增加了调度、同步及回读成本，是否更快必须测量，不能从“已启用GPU”推导吞吐提升。后续提速方向是同一仿真实例中批量推进环境、减少CPU同步并尽量保留GPU张量，而不是单独启动更多完整Isaac进程。

[PhysX GPU说明](https://nvidia-omniverse.github.io/PhysX/physx/5.6.1/docs/GPURigidBodies.html)说明GPU动力学与GPU broadphase可以分别开启，也说明多对象场景的扩展优势及混合CPU路径；[Isaac Sim 5.1性能指南](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/reference_material/sim_performance_optimization_handbook.html)要求按实际负载选择CPU／GPU。当前本机CPU状态路径的上一阶段性能见[完整控制步排查](isaac-step-profile.md)。

运行证据保存在`/data/shapeforge/runtime/runs/isaac_gpu_physics_20261124`，包括独立计时源码、场景GPU统计、RGB、逐步接触和动作、CPU对照及退出回执。GPU控制回调能收到接触信号不代表每项接触生成或整个控制管线均在GPU上运行。
