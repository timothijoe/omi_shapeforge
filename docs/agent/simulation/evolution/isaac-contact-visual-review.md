# Isaac接触峰值与图像清晰度复核

2026-11-22。用户要求测试接触问题并改善图像真实感/清晰度。本轮保留[第一版同源实验](isaac-contact.md)，在新输出目录进行控制与渲染对照，不修改原mesh或碰撞参数。

## 接触诊断与改进

第一版seed7的控制采样峰值21.317 N出现在插入第180步：深度从51.223 mm接近台阶，随后产生85.451 N的物理子步峰值。原目标比名义机械终点多推进0.15 mm，临近台阶仍可请求约0.49 mm的轴向增量。

新增可选`--contact-recipe gentle`：距台阶2 mm内逐步限制轴向增量，每个100 ms控制周期最多0.10 mm，接近终点降至0.01 mm；名义终点后的控制目标余量改为0.03 mm。横向/旋转对准逻辑、成功/失败几何阈值、摩擦、弹性触点、碰撞体和驱动增益均保留。退回动作不受此减速器限制。

这是减速与目标余量的组合修改，没有单独拆分两者贡献。seed7前173个未限速控制步的请求动作、实际插入深度与原基线逐值一致，限速从第174步开始；见运行根的`prefix_equivalence.json`。

新方案默认实际启用10 N控制采样停止门控，超限会立即将该回合判失败，不能只看几何到位。

| 检查 | 插入/退出控制步 | 控制采样峰值 | 物理子步峰值 | 结果 |
| --- | --- | --- | --- | --- |
| gentle seed7，0.2 ms | 219/187 | 3.041 N | 10.598 N | 插入退出及控制采样门控通过 |
| gentle seed19，0.2 ms | 220/187 | 2.797 N | 12.499 N | 同上 |
| gentle seed41，0.2 ms | 216/187 | 2.648 N | 8.626 N | 同上 |
| gentle seed7，0.1 ms | 230/187 | 2.705 N | 18.838 N | 到位/退出结论保持，控制采样门控通过 |

seed7控制采样峰值比原基线下降约85.7%，代价是插入多37步（3.7 s）。**不能把该结果写成全部瞬时力低于10 N。** 子步峰值仍存在，且随步长变化；接触参数未实物标定。本轮是三组小扰动初态与一次半步长检查，不是广范围可靠性或真实机器人安全力认证。

## 图像问题与同位姿对照

旧策略图原生128×128，视频中又放大显示；低分辨率叠加DLSS会损失孔口/螺钉/筋条细节。对照固定相机、视角和几何姿态，输出原生768×768的头部/腕部静态图，以及1280×960全景；使用DLAA，并保留原低分辨率图供比较。原生像素增加与抗锯齿设置共同变化，未将它们的效果单独归因。

实际测试包含：旧128图、原生768/DLAA、直接源法线映射、分材质/区域灯光，以及64采样路径追踪。直接把MuJoCo法线数组写成USD face-varying normals出现折痕，转换尚未验证，**该候选被拒绝**；采用渲染器按几何生成的法线。高分辨率实时图已经明显改善，当前64采样路径追踪没有显示出足以替代它的清晰度收益，不作一般性的渲染器性能结论。

材质区分喷涂机器人、聚合物夹具、PCB、金属和台面，配合宽面积灯光。模块从已有V4-r07 GLB读取金属度、粗糙度和纯色纹理：银灰金属、暗绿拉环、暗灰胶塞。第一版材质转译曾漏掉RGBA背后的纯色贴图，导致胶塞/拉环颜色错误；已保留失败稿并修正。没有添加用户已否定的颗粒纹理。

所有静态对照都检查了网格点/面和原有变换哈希不变；用于拍摄的内存场景冻结物理，不能把这些图片算作新的动力学试验。当前仍使用SIM-r06的旧URDF工具及针孔视角，没有自动替换为WG-r09，也未完成真实鱼眼、相机外参、环境照明或色卡标定。因此可以确认图像更清晰、材质区分更明确，不能宣称与真机照片一致。

## 实时接入与交付

新增`--image-recipe refined --sensor-resolution 512`，实际渲染512×512双相机与1280×960全景，视频以高分辨率拼接显示；策略接口仍显式下采样为128×128及10帧因果历史，不能把显示分辨率增加当成策略输入分辨率已改变或训练收益已验证。取图保持零时间增量，并检查关节位置不被渲染改变。

修正版完整实时回合已完成：插入219步、退出187步，实际512×512双相机，视频1792×1024、406帧、40.6秒。插入深度、控制采样力、区间子步力峰值和最大侵入的全部406条记录，与无渲染seed7试验逐值一致；详见`render_physics_equivalence.json`。策略张量仍为10×3×128×128。没有运行新BC/RL训练。

- [腕部图像前后对比](/data/omi_runtime/runs/isaac_contact_visual_review_20261122/comparison_final/wrist_rgb_comparison.png) · [头部对比](/data/omi_runtime/runs/isaac_contact_visual_review_20261122/comparison_final/head_rgb_comparison.png) · [全景对比](/data/omi_runtime/runs/isaac_contact_visual_review_20261122/comparison_final/overview_comparison.png)。
- [新版完整视频](/data/omi_runtime/runs/isaac_contact_visual_review_20261122/gentle_refined_video_r03/cycle.mp4) · [原生腕部图](/data/omi_runtime/runs/isaac_contact_visual_review_20261122/image_refined_r03/refined_768/wrist_rgb.png)。
- [接触力对比图](/data/omi_runtime/runs/isaac_contact_visual_review_20261122/comparison_final/contact_force_comparison.png) · [PDF](/data/omi_runtime/runs/isaac_contact_visual_review_20261122/comparison_final/contact_force_comparison.pdf)。
- [本轮登记](../../../../manifests/isaac_contact_visual_review_20261122.json)：五份完整任务报告，控制采样门控、子步峰值和进程收尾分别记录。

额外核对：1294份顶点/面数组与旧传递包逐值一致；648份机器人源文件哈希不变；视觉候选与源USD的4464项物理属性/绑定一致。胶塞、绿色拉环和银灰金属的PBR颜色检查通过。控制环境38项中14项执行通过、24项跳过；仿真环境另执行4项FK/限速测试通过。

收尾限制：seed19和半步长的工具会话在完整轨迹/报告落盘后返回143，原因未诊断，不能写成所有进程正常退出。登记中`task_results_all_passed=true`与`execution_all_clean=false`有意分开；任务内到位/退出/力门控结果可检查，自动批处理的收尾仍需串行复核。其余三个工具会话退出0。

运行根：`/data/omi_runtime/runs/isaac_contact_visual_review_20261122/`。`image_ablation/`保存初始全部对照；`image_refined_r02/`保留漏贴图颜色候选，`image_refined_r03/`为修正后的静态候选；直接源法线失败和启动停滞也保留，不以目录名代替验收。

入口：`scripts/simulation/review_isaac_images.py`、`summarize_isaac_review.py`及既有`run_isaac_contact.py`。源码实现为`isaac_contact_approach.py`与`isaac_appearance.py`；[操作说明](../../../../tutorials/isaac_contact_insertion.md)。

渲染设置参考[NVIDIA路径追踪说明](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/rtx-renderer_pt.html)与[UsdPreviewSurface说明](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/templates/UsdPreviewSurface.html)；实际API以本机5.1.0扩展为准。
