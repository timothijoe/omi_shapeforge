# 规则示范：预插入老师与视觉策略

2026-11-21 用户要求展示仿真，并用 rule 替代初期人类示范。新增 `sim/rule_teacher.py` 的 `PreinsertRuleTeacher`，生成真实机械臂运动和双相机观测；训练仍使用原 OMI 视觉 Actor／SAC。

## 控制规则

老师读取仿真 TCP 和目标的位姿误差，以插接座的插入轴分解横向／轴向分量。

1. **align**：修正旋转与横向偏差，暂不主动沿轴推进。横向误差低于 1.5 mm、近似旋转误差低于 0.015 rad 后转入 approach。
2. **approach**：修正完整位姿误差，接近孔口前的固定目标；横向或角度误差超过上述阈值的两倍则回到 align。
3. **结束**：由环境原有成功／超时条件决定。成功仍是 TCP 位置误差小于 3 mm、旋转误差小于 0.02 rad。若 align 阶段已满足成功，允许直接结束，不为画面强行延长轨迹。

归一化控制为 `clip(0.8 × error / action_scale, ±0.85)`，每轴每步变化最多 0.35。所有动作经过现有 6D→IK→关节伺服→MuJoCo 步进；控制器不能写 qpos、直接移动模型或改成功标记。初始化允许在关节初态上施加显式扰动，本批每关节 ±0.015 rad，限于 reset，不是运动过程中瞬移。

老师读取真值是仿真中的明确先验。视觉策略只读取双 RGB 历史，state／tactile 仍补零；相位、目标误差和关节真值只保存在审计记录，不进入网络观测。这些示范只覆盖无接触预插入，尚无接触抓取、插入力或弹片让位示范。

## 数据来源和训练

OMI `training/collect_shapeforge_rules.py` 通过 `EpisodeSpool`／`FrameWriter` 保存实际执行动作及相邻观测，使用 **`origin=scripted_demo`、`action_source=scripted`、`policy_version=-1`**。成功完整回合才生成 ready；失败回合保留 discarded，不能当成功示范。此 origin 仅允许 MuJoCo 合同。

`ScriptedDemonstrations` 是独立只读示范数据源。它核对合同、manifest／transition／帧哈希、连续历史和 padding，严格按回合划分训练／验证／测试。原真人 `TransitionReplay` 拒绝 scripted 标签；没有将机器规则改名为 human，也没有把规则数据塞进真人池。

训练入口支持 `--rule-dataset`：

- 先用规则动作对已有视觉 Actor 做行为克隆，验证组动作误差选择 checkpoint；留出测试组仅在选好后评估。
- 再用 BC Actor 初始化新的 SAC，保留冻结 BC 参考。正式版本在 SAC 阶段冻结 BC 编码器、前 8 次只更新 Critic，后续 Actor 带权重 1 的规则动作模仿项，初始探索 std=0.1 为显式设定。
- SAC 每批 16 条采用 8 条规则训练样本＋8 条在线策略 transition。规则数据独立、不会被在线环形池覆盖；验证／测试组不参与混合。日志含 `scripted_samples`、`online_samples`、`imitation_source`。
- 续训自动读取训练目录的 `training_settings.json`，校验原数据集哈希并恢复完整 learner；不会再次执行 BC。

## 本批实测

16 个初始化均成功，共 824 条规则 transition。种子 100–107 为训练：8 回合／393 条；108–111 为验证：4 回合／180 条；112–115 为测试：4 回合／251 条。轨迹长度 23–103 步，终点约 2.68–2.99 mm，均在原有任务成功阈值内。

正式 BC 执行 200 次更新，以第 175 次的验证误差选模：验证动作 MSE 从 0.6315 降到 0.04457；留出动作 MSE 为 0.04689。独立闭环四个扰动初态仍为 0/4 成功。一次近默认初态在线采集成功不能替代留出评估；动作拟合改善也不能代替稳定的闭环能力。

规则辅助 SAC、完整恢复和数据来源审计见[新清单](../../../../manifests/rule_demonstrations_20261121.json)。最初调试训练保留在 `rule_assisted_train_20261121_v1`；正式冻结编码器／Critic 预热版本位于 `rule_assisted_train_20261121_final`。旧的无示范运行仍保留。

展示包含真正渲染的机械臂全景、头部与腕部视角。全景只用于查看，不是额外策略输入。视频和操作见[规则示范教程](../../../../tutorials/rule_demonstrations.md)。后续应补充偏离示范轨迹后的纠偏数据、扩大初态覆盖并重做独立闭环评估，再推进接触插入。
