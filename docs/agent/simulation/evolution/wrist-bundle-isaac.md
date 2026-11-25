# WG-r10＋OM-r08：固定版本接入Isaac

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

后续已在右臂停放版完成[Isaac规则反馈RL链路运行](isaac-rule-feedback-rl.md)，其数据/更新和0/2自主评估独立记录，不改本页早期装配验证范围。

后续按用户要求已创建[右臂水平停放副本](right-arm-park-and-hil.md)，腕部视野已检查；本页原场景保留。

2026-11-22，按用户要求读取[资产交接](wrist-assets-handoff.md)、固定清单与复现教程，将WG-DAIMON-OBS-r10和OM-001/V4 r08接入**独立的完整机械臂Isaac场景**。原资产、原MuJoCo/Isaac任务场景和旧成绩保留。

## 固定来源与复现

使用`manifests/wrist_visual_asset_handoff_20261122.json`确定身份和SHA256，未按mtime或“latest”选择。工具90个文件、模块66个文件全部校验，复制到本轮`inputs/tool`与`inputs/module`；固定静态场景的675个依赖逐文件校验通过。复现后原156个资产文件哈希仍一致。

按教程复制渲染脚本和trials.json到独立目录后，实际完成MuJoCo静态鱼眼复现：1080×1920×3，与原参考图平均绝对通道差约1.61e−7。没有覆盖交接中的6个源输出。

## 挂载与模块映射

旧`wrist_tool_scene.py`已扩展`camera/camera_mount`组件，和base一起绑定`TCP_Link_L`；两指分别绑定`Arm_L10_Link`、`Arm_L11_Link`。MuJoCo颜色优先读`mujoco_rgba`，Isaac使用资产的线性PBR颜色、金属度和粗糙度，避免再将黄色件错误转成偏红色。

使用固定的`T_TCP_from_module`，重新求解−5 mm预插入位姿。模型内IK残差约3.5e−10 mm、3.1e−12 rad，仅说明数值求解一致，不是实际工具标定精度。新的TCP位置约(0.369334,0.206564,0.808375) m；不复用旧r04的195 mm安装解。

模块按`source_part_index`保留16件，删除旧绿色视觉索引8/10，加入连续U形件，显示角−35°。旧两侧绿色碰撞代理也从派生场景移除；新U形件仅用于外观，未虚构专用碰撞/铰链。主体碰撞仍来源于SIM-r06。原文件没有变化。

## 本轮实际检查

| 检查 | 结果 | 边界 |
| --- | --- | --- |
| 载入和件数 | 49件工具、17件模块；旧左臂工具外观移除 | 原非活动臂仍用旧URDF |
| 参考装配 | 工具/模块表面无相交，最近间隙约0.04597 mm | 固定附着，不是真实夹紧 |
| 静态插入路径 | 22个IK采样点无工具/插槽表面相交；最小约5.0703 mm | 不是连续路径、整机自碰撞或动态插入验收 |
| 开合映射 | 参考关节0.0313 m，打开目标0.0193 m；几何对应两指各向外12 mm | 不是硬件开度标定 |
| Isaac开合预览 | 2个指关节实际驱动；21个观察状态和视频已生成 | 工具碰撞关闭、惯量沿用旧URDF占位 |
| 相机/模块绑定 | 相机相对TCP矩阵差0；模块绑定最大矩阵元素差约2.52e−6 | 数值变换检查，不作毫米精度解释 |
| 投影实现 | 765个前向工具点，Isaac装配与固定镜头变换最大投影差约3.37e−5 px | 仅检查同一候选模型的实现一致性 |
| 测试 | 14项控制检查、2项挂载测试、2项鱼眼测试执行通过；控制环境28项跳过 | 跳过项不计通过 |

预览报告原`physics_steps=10003`漏计显式attach后的1个初始化步；实际总数为10004，其中10000步是夹指驱动（2秒物理时间）。保留原报告并另存`report_correction.json`；后续代码改为读取实际累计时间。

## 腕部观测和查看

保持清单中的K/D及1920×1080域。Isaac从同一镜头位置渲染六个2048方形视图，再按同一鱼眼射线模型重投影，已输出闭合、打开、再次闭合的鱼眼图。原生`wrist_rgb`和开合视频右下角仍是针孔检查视角，不能把它称作最终鱼眼观测。

完整Isaac GUI已打开，默认时间线暂停，可查看新工具与机械臂的安装。未在本轮启用自动插入或旧策略；不继承原SIM-r06的规则成功率、10 N结果或BC/RL成绩。

- [完整USD](/data/omi_runtime/runs/wg_r10_om_r08_isaac_20261122/isaac_preview/WG-r10_OM-r08_robot.usdc)
- [闭合腕部鱼眼原图](/data/omi_runtime/runs/wg_r10_om_r08_isaac_20261122/isaac_preview/closed_wrist_fisheye_1920.png) · [局部查看](/data/omi_runtime/runs/wg_r10_om_r08_isaac_20261122/isaac_preview/closed_wrist_detail.png)
- [开合预览视频](/data/omi_runtime/runs/wg_r10_om_r08_isaac_20261122/isaac_preview/jaw_preview.mp4) · [桌面确认](/data/omi_runtime/runs/wg_r10_om_r08_isaac_20261122/desktop_isaac_front.png)
- [本轮登记](../../../../manifests/wrist_bundle_isaac_20261122.json) · [操作](../../../../tutorials/wrist_bundle_isaac.md)

## 讨论与后续边界

已结合主体内沿修订、点云来源、U形件开发和成像记录梳理背景：r10保持r09镜头，改善黄色外缘但局部点云残差有小幅退步；模块夹持变换只代表参考关系，不能作为287个样本的真值。相机外参/K-D绑定、真实开度、惯量/摩擦与抓取尚未认证。

本轮完成的是新资产装配、开合展示与观测接入。后续若进入插入或训练，应重新做动态接触、工具质量与碰撞、连续净空和新观测合同检查；不把静态无相交或鱼眼观感当作这些验收。
