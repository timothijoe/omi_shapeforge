# GC-r01：黑胶垫双面接触修订

**本次夹持工作的主阅读入口就是本页。** 这里集中记录问题、修订方式、接触验证、资产路径和窗口操作；过程按时间记录在[对应编年体](../chronicles/2026-11-22-wrist-contact-closure.md)。

2026-11-22已实际打开MuJoCo交互窗口，默认显示`gravity_hold`双侧夹紧状态。用户查看后反馈“感觉好很多”，并要求归档。该反馈记录为对当前展示效果的认可；接触数值结论仍以以下仿真验证为准，未扩展为真机、插槽接触或策略验收。

用户指出光模块并非永远固定在夹爪同一位置，但夹紧后应随夹爪一起运动，两侧黑胶垫必须真正接触模块。该问题成立：WVA-01参考装配左右最近表面间隙分别约0.046／0.602 mm，且工具碰撞关闭。“无相交”不能代替“已夹住”。

在WVA-01基础上新增 **GC-r01「黑胶垫双面接触修订候选」**。源r15夹爪、r08模块和WVA-01全部保留，49件工具mesh没有修改；变化是场景运动关系、双指关节和接触模型。它是已通过局部夹持检查的候选，尚未替换WVA-01固定视觉清单或现有机器人训练任务。

## 三种状态与接触关系

- **张开**：模块为6自由度自由刚体，可以与夹爪分离，允许不同初始夹持位置。
- **闭合**：两指沿各自Y轴运动，用限力位置伺服闭合；实际停止位置由模块接触决定。两块黑色凸胶垫使用各自原始可见凸网格参与碰撞，模块使用既有SIM-r06分解碰撞件。
- **夹持／移动**：模块通过接触力和摩擦随夹爪运动，逐次读取实际相对变换。没有给模块设置weld、固定关节或每步强写位置。只有工具基座通过weld跟踪mocap目标，以提供正确的基座速度；这不是把模块焊到手上。

加载原资产时的`tool_to_module`只是参考初始放置值，不能代表每次真实夹持，也不能作为接触成立的依据。新场景的`module_free`保留自由度，`jaw_left/right`负责开合。`scripts/grasp_status.py`根据两侧实际模块接触和法向力判断`held`，同时返回当前`T_TCP_from_module`；查看器在应保持阶段失去双侧接触时停止运动，不凭固定变换假装夹住。

## 验证结果

| 检查 | 结果 |
| --- | --- |
| 名义闭合后双指位移 | 左约−0.323 mm，右约−0.330 mm；负号表示沿各自开合轴向内闭合 |
| 稳定夹持法向力 | 每侧约2.35 N（仿真值） |
| 可见表面核对 | 原胶垫mesh对原OM-r08 mesh检查，双侧接触；数值压入约0.0014～0.0026 mm；没有其他工具部件穿入模块 |
| 初态变化 | 名义、横向±0.4 mm、轴向±1.5 mm并绕工具X轴±1°，共5例通过 |
| 重力保持及移动 | 夹爪平移22.36 mm，5例最大相对滑移约0.00464 mm，最大相对转角约0.0078° |
| 双侧接触持续性 | 保持／移动阶段每10 ms检查，两侧法向力均超过0.1 N，5例采样通过率100% |
| 释放 | 张开后两侧法向力为0，模块在重力下脱离；不是隐含固定附着 |
| 半步长 | 0.2 ms→0.1 ms名义复验通过，最大滑移约0.00464 mm |
| 交互入口复核 | 已夹紧关键帧加载后双侧法向力约2.349／2.344 N；名义重放逐0.2 ms检查接触门控通过，张开后`held=false` |
| 源资产保护 | r15、r08及WVA-01快照哈希不变；新场景独立保存 |

这里的微小滑移和压入是仿真数值，不是真机精度承诺。胶垫按刚性凸网格建模，没有模拟橡胶弹性形变；20 g模块质量、摩擦系数1、每指4 N力限、接触刚度／求解参数未实物标定。这里只验收上述小范围初态。插槽作为视觉上下文，其碰撞在本夹持单测中关闭；未运行新的插入任务或BC／RL，不能把5/5夹持通过称为插入成功。

## 失败与纠正

第一次仅启用较软接触时，两侧已有力但重力下滑移，未通过。提高接触约束精度后静止保持稳定，但直接移动mocap工具缺少正确的动态切向速度，运动时丢失夹持。最终改为有自由关节的动态工具基座跟踪mocap目标，使接触求解看到真实速度；模块始终保持自由刚体。失败场景／轨迹保存在运行目录`attempt01_soft_slip`和`attempt02_mocap_velocity`，不改写为成功。

## 文件与接入

- [独立清单](../../../../manifests/wrist_contact_closure_20261122.json)
- [旧／新腕部图与接触力对比](/data/omi_runtime/assets/daimon/wrist_grasp_contact_r01/evidence/contact_comparison.png)
- [5例验证](/data/omi_runtime/assets/daimon/wrist_grasp_contact_r01/evidence/cases_report.json) · [半步长](/data/omi_runtime/assets/daimon/wrist_grasp_contact_r01/evidence/half_dt_report.json)
- [真实可见表面审计](/data/omi_runtime/assets/daimon/wrist_grasp_contact_r01/evidence/surface_audit.json)
- [最终入口／连续接触门控／文件校验](/data/omi_runtime/runs/wrist_contact_closure_20261122/final_verification.json)

资产目录`/data/omi_runtime/assets/daimon/wrist_grasp_contact_r01/`按路径引用原网格，不是全量复制包。`contact_scene.xml`包含已夹紧关键帧；加载后调用`mj_resetDataKeyframe(model,data,model.key('gravity_hold').id)`及`mj_forward`。如果仅载入XML默认状态，仍是闭合前初始放置，不能当成已夹紧。`initial_closure_scene.xml`用于从头闭合测试，初始重力为0，夹紧后再启用重力。

交互检查：

```bash
MUJOCO_GL=glfw /data/omi_runtime/envs/omi_mesh_audit/bin/python /data/omi_runtime/assets/daimon/wrist_grasp_contact_r01/scripts/view_contact.py
```

默认停在双侧接触状态；空格或R重放闭合→重力保持→平移→张开释放；1自由视角，2腕部针孔检查视角（不是最终鱼眼）。完整鱼眼证据来自闭合后的实际物理状态，未使用真实手部像素覆盖。

后续接入不同模块姿态，应更新自由模块初态、让双指闭合，再检验双侧法向力及滑移；不直接复用同一个夹持矩阵，不以增大碰撞margin伪造跨空隙接触。本场景margin为0，可见表面和碰撞接触已分别检查。新姿态超出测试范围或接触门控失败时，应报失败并重新调整，不能继续宣称稳定夹持。

完整实验在`/data/omi_runtime/runs/wrist_contact_closure_20261122/`，包含最终重建脚本、初次失败、状态轨迹和渲染。复制脚本时注意固定输出目录并另建运行路径。WVA-01视觉版本说明见[原版本纪传体](wrist-visual-wva01.md)。

## 2026-11-23 独立感知训练接入

用户再次认可视觉修订后，已在独立[接触版腕部表面学习](../../perception/evolution/contact-wrist-surface-learning.md)中接入本夹持机制。采集256段／3072帧、逐轨迹接触门控、逐帧可见网格检查与25轮感知微调完成。源GC-r01文件不改；机器人为FK视觉上下文，模块保持自由刚体。插槽碰撞仍关闭，尚未开展该场景的插入或RL验收。
