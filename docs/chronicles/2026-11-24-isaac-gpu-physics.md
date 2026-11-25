# 2026-11-24：GPU物理接入与单环境对照

用户询问是否能使用GPU物理。本阶段启用Isaac 5.1的GPU动力学与GPU broadphase，保持当前PGS、20子步、原厂IK、接触规则及真实双相机，实际验证现有单环境控制路径的兼容性。

原生场景统计确认GPU求解器、关节仿真和broadphase分配了GPU内存；NumPy tensor frontend继续报告CPU设备，说明状态经host回读。这是GPU物理与CPU控制兼容模式，不是CUDA张量常驻或多环境向量化。

GPU正常、±1 mm恢复3/3通过，步数388／572／575；CPU同种子正常388步通过。完整子进程及shutdown均退出0。原厂IK约0.57 ms不变；同批正常均值物理循环CPU23.666／GPU69.229 ms，完整step RPC CPU64.707／GPU111.180 ms。当前小场景回读模式开启GPU更慢，因此保持CPU默认。

worker和批量入口提供`--physics-device gpu`。启动检查场景配置及原生GPU求解器／关节内存统计，拒绝配置与执行证据不一致。GPU使用新的`physx-gpu-host-readback-v1`执行合同；CPU旧合同字段布局不变。75项轻量测试中21通过、54可选依赖跳过；实际GPU运行另有独立证据。

后端切换导致约0.011 mm量级的正常轨迹深度差，以及接触力／奖励差异，不能重标记旧CPU数据。后续吞吐优化需要多环境批量推进与减少CPU同步；本阶段未重训BC／RL，也未连接真机。

能力、使用及范围见[GPU物理兼容模式](../agent/simulation/evolution/isaac-gpu-physics.md)。实验根目录：`/data/shapeforge/runtime/runs/isaac_gpu_physics_20261124`；来源、摘要与进程回执见[清单](../../manifests/isaac_gpu_physics_20261124.json)。
