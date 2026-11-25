# 2026-11-24：原厂IK之后的控制步排查与优化

用户要求继续排查IK之外约96 ms的开销。按同一输入、原厂IK、20子步、双RGB与规则控制，依次串行运行原基线、单变量线程／子帧试验、重复计算优化、默认预览关闭及组合验证。

基线step RPC 96.195 ms，worker内部93.930 ms；渲染40.867、物理循环24.727、三次接触测量14.194、取图／采样／缩放7.472 ms。发现奖励势函数两次额外执行完整几何检查、小向量SAT循环、整张腕图转float64，以及无界面运行仍更新的1280×720默认预览。

重复计算优化后，三次测量变一次且SAT批量化，原图以uint8直接参与float64权重运算；RPC降到82.299 ms，正常与±1 mm恢复3/3通过。物理线程8→0单变量仅节省约4 ms；RTX子帧2→1省约9 ms但改变图像收敛，均未更改生产默认。

在SimulationApp启动时直接关闭视口的试验没有完成场景初始化，监督器判定启动失败并SIGTERM结束；没有控制步，保留失败回执。随后改为场景、render products及预热完成后关闭默认视口，单变量RPC降到80.796 ms。生产采用后者，保留真实两路相机、分辨率与双子帧。

最终组合step RPC为68.810 ms，worker内66.419 ms，正常回合含记录47.220→36.429 s。正常388步、+1 mm恢复573步、−1 mm恢复576步全部完成；逐步物理状态、控制目标、奖励、接触指标及判定与原厂IK原始三例一致。新执行合同记录`headless-sensors-only-v1`；旧渲染合同可通过`--keep-preview-viewport`恢复，不能把新图像配方静默套到旧回放或检查点。

原始过程、私有计时快照、逐步RGB与计时、等价性检查及退出状态在`/data/shapeforge/runtime/runs/isaac_step_profile_20261124`。能力与测量口径见[完整控制步耗时](../agent/simulation/evolution/isaac-step-profile.md)，出处见[清单](../../manifests/isaac_step_profile_20261124.json)。没有重训BC／RL，没有连接机器人，也没有改动场景接触几何或任务成功判据。

## 后续：CPU完整周期口径与阻塞归因

用户要求只考虑CPU路径的一次完整控制周期。单独新增原厂IK＋CPU PhysX规则采集计时，正常388步成功，全部退出0。326个未受cProfile影响的完整周期均值90.613 ms；teacher RPC 1.742、step RPC 64.976、客户端记录23.575、整理0.321 ms。记录内每周期4次fsync共16.499 ms；50步详细采样显示200次Kit app.update，来自Replicator同步捕获。确认无帧率限速或人为100 ms等待；CPU时钟不将引擎自旋等同有效计算。没有修改生产代码或削减子步／相机／持久化。原始证据在`/data/shapeforge/runtime/runs/isaac_cpu_cycle_20261124`，见[清单](../../manifests/isaac_cpu_cycle_20261124.json)与能力页新增完整周期一节。
