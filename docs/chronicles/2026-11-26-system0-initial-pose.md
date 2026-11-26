# 2026-11-26：初始偏移、俯仰与朝向误差测试

用户在多demo展示之后要求末端不要一开始正对插口。新增显式初态reset，按夹爪中心改变位置和方向，固定原插口目标及已训练模型。9种新初态经过离线IK核对，并在真实PhysX中验证位置／朝向和初始无重叠；原始近距初态作为第十个条件。

选用较强的无路径种子341000及其配对路径模型。原始起点与10 mm后退对照均2/2，横移±2 mm两组均2/2；俯仰±2°、偏航±2°及两个组合扰动路径6/6、无路径0/6。总体10/10对4/10，无接管，不重训。无路径失败记录保留接触保护／IK拒绝；只是一组冻结模型、10个单次条件，不能作广泛鲁棒性保证。

新增reset能力独立于运行时schema，冻结模型严格加载；初态第0步日志及逐例实现误差可核验。相关28测试通过，轻量29通过／69跳过，真实两个worker均正常结束。视频按真实第0步及后续状态制作，避免用对正后的画面代替带偏差起点。

- [能力与完整条件](../agent/simulation/evolution/system0-initial-pose-robustness.md)
- 评估根：`/data/shapeforge/runtime/runs/s0_initial_pose_20261126/`
- 协议与结果：`protocol.json`、`cases.json`、`summary.json`
- 视频根：`/data/shapeforge/runtime/runs/s0_initial_pose_videos_20261126/`

模块与夹爪固定相连；没有测试模块相对夹爪滑移、视觉估计误差、插口朝向变化或真机。

四段视频和73.8秒合集已完成、解码检查通过并交付Downloads；每段从真实第0步停留3秒后继续，左右按控制步同步，原始模型／状态哈希保持。交付路径：`/home/linux/Downloads/Tilted_Starts_Demos_20261126/Tilted_Starts_4_Demos.mp4`。
