# 2026-11-26 插口随机性与BC数据覆盖核查

用户怀疑插口位姿随机性过强。确认当前只在reset时采样世界XY每轴±3mm，Z和朝向固定，回合内目标不跳动。追加冻结BC／RL模型的原位单例诊断，保持同一机器人种子220000和原物理合同，只将socket pose显式设为零。

BC 66步入口资格失败，末横向误差约0.228mm；RL 491个已执行步后请求被IK拒绝，末横向误差约2.127mm。teacher均0，初始关节逐值一致，两个模型哈希保持。结果只能说明已有模型在该原位单例仍失败，不是固定目标重新训练的对照，不能排除训练随机化带来的难度。

数据审核发现5条BC训练示范目标的Y偏移全部为正（+0.483～+2.160mm），唯一负侧−0.443mm属于验证集。这项覆盖检查此前遗漏。在线RL的30个起点则包含14个正Y和16个负Y，范围约−2.454～+2.994mm。应区分BC初始化覆盖不足与整个训练范围。后续先固定目标建立合格BC闭环基线，再用分层采样覆盖中心、正负侧及逐级幅度。

产物：`/data/shapeforge/runtime/runs/hier_s0_fixed_target_20261126/`。新增评估专用`--fixed-socket-pose`参数，未修改模型、原数据或训练默认。[汇总](/data/shapeforge/runtime/runs/hier_s0_fixed_target_20261126/summary.json) · [能力页](../agent/simulation/evolution/hierarchical-intervention.md)
