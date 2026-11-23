# 2026-11-22：光模块mesh、仿真、腕部视觉与训练进展汇总

本页汇总截至本轮真机／r07对比完成时的状态。最新材质展示为 **V4-r07「纯色银灰材质候选」**；已明确暂定采用的几何基线仍为 **V4-r05「双窗尾槽版」**。新尺寸规则接触仿真已通过，最新材质与真实夹爪混合图尚未接入实时训练。这里整理已有证据，本轮没有重新训练或修改物理模型。

## 用户要求与保留的决定

- 新建仿真资产和后续修订，保留原mesh、V3及各历史版本。采用Blender编辑，生成物放在`/data/omi_runtime/`，仓库管理代码、文档和登记。
- 实测模块参考截面18.1 × 8.2 mm，宽度允许按8.1～8.2 mm理解；当前建模采用8.2 mm。下部前伸片向上倾斜，尖端厚度8.0 mm；底部同样为金属。
- 插孔18.8 × 8.8 mm；左侧孔内壁到插座外缘约6.9 mm。当前按正对孔口、白色外框窄边解释，方向和所指外缘仍待进一步确认。
- 尾端上侧缺一个小长方形；黑色胶件向内延伸且位置下沉，三个金属端之间同高度的两个窗口必须为空，不能用胶件填满。
- 实际夹持模块的是白色指尖壳内侧的黑色接触面，橙黄色内衬在后方。模块尾端胶塞与夹爪接触面是不同对象。
- 用户认为改色后“颜色差不多”，明确不要额外颗粒感；当前r07遵守此要求。附加marker贴纸忽略，不作为建模或视觉策略依赖。
- 对比应包含真机照片，不能只给两个仿真版本。文档同时维护mesh专门页与仿真器页。

## 当前资产和用途

| 标识 | 内容及当前角色 | 入口 |
| --- | --- | --- |
| OM-001/V4 r05 · 双窗尾槽版 | 用户暂定采用的18件几何基线；17个主体件＋1个双脚胶件 | [Blender](/data/omi_runtime/assets/optical_module_v4/r05/OM-001-V4-r05.blend) |
| OM-001/V4 r06 | 在r05上改银灰／绿色／胶件色调，曾加入颗粒；颗粒已被用户否定，保留历史 | [材质开发](../agent/simulation/evolution/module-material-r06.md) |
| OM-001/V4 r07 | 保留r06颜色，去掉新增颗粒；最新独立展示候选，几何不变 | [Blender](/data/omi_runtime/assets/optical_module_v4/r07/OM-001-V4-r07.blend) · [GLB](/data/omi_runtime/assets/optical_module_v4/r07/OM-001-V4-r07.glb) |
| OS-001/M1888-r01 | 18.8 × 8.8 mm实测孔口、6.9 mm窄边候选的独立插槽 | [Blender](/data/omi_runtime/assets/optical_socket/measured/r01/OS-001-M1888-r01.blend) |
| SIM-OM001-OS001-r06 | V4-r05模块与新尺寸插槽的物理接触装配 | [Blender](/data/omi_runtime/assets/sim_insertion/r06/SIM-OM001-OS001-r06.blend) |
| WG-DAIMON-VIS-r04 | 视频参考相机／夹爪，31个工具外观件，非已核对厂家CAD | [Blender](/data/omi_runtime/assets/daimon/wrist_gripper_video_r04/WG-DAIMON-VIS-r04.blend) |
| SIM-OM001-OS001-r03 | 旧尺寸物理资产，已有BC／RL训练成绩保留在这套场景 | [训练记录](2026-11-21-contact-policy-improvement.md) |

模块V4-r06与仿真装配SIM-r06是两个命名空间。r07没有自动替换SIM-r06中的模块、实时场景或旧训练数据。版本身份见[资产目录](../asset-versions.md)与[机器登记](../../manifests/optical_assets.json)。

## Mesh开发、材质修正和验证

V3经实测截面修订后，V4逐版补充尾部缺口、下沉胶件、三个宽短金属端和两处空窗。r04曾误把空窗填成胶件上部延伸，r05已删除错误填充。r05含16个闭合实体及2个开放装饰折缝；280个空窗点检查、31个离散胶件拔出位置和文件重开均通过。局部缺口尺寸、胶件形状及斜面长度仍包含照片拟合或旧模型假设。

r06只改UV／材质／颜色；r07把三张程序颗粒图换成2×2恒定色图，保持底色、金属度、粗糙度和MuJoCo材质参数。几何没有为了颜色重建或缩放。上下壳同为银灰金属，绿色拉手降低饱和度，胶塞使用暗灰色。

r07验证：18件OBJ顶点／面与r06一致，GLB可重开为18件，三张颜色纹理空间恒定，1397个受保护旧文件哈希未变。交付包含Blender、GLB、整件及逐件OBJ／MTL、纹理、MuJoCo材质适配、构建脚本和清单。验证详见[r07报告](/data/omi_runtime/assets/optical_module_v4/r07/validation.json)。材质近似未经过色卡或跨光照标定。

持续维护入口：[Mesh开发记录](../mesh-development.md)、[Blender资产管线](../agent/simulation/evolution/asset-pipeline.md)、[V4几何演进](../agent/simulation/evolution/module-v4.md)、[r06/r07材质演进](../agent/simulation/evolution/module-material-r06.md)。

## 腕部相机、真实夹爪像素与当前图片

已从用户视频建立31件相机／夹爪外观，并绑定到机器人TCP与夹指关节。外观安装场景镜头位置与渲染相机一致；最终握持安装变换沿TCP的Z为195 mm，21个名义路径位置无工具／插槽表面相交，最小距离约1.961 mm。该场景规则插入／退出2/2通过，但模块仍固定附着，新增工具未启用接触抓取和附加质量，实时相机仍是90°估计针孔模型。

另做了独立的真实夹爪像素＋仿真模块／插槽合成：使用真实腕部首帧、SAM2提示分割与人工修整掩码，用MuJoCo六面渲染重投影到原始鱼眼图域。用户提供的内参文件为`/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json`；使用其K／D并不意味着重新标定了外参。相机位姿仍来自首帧粗配准先验。

首版漏掉黑色夹爪接触面，已根据两张照片补回左右核心647／543个真实像素；核心与源图一致，和模块边缘最近距离各1个源像素。这只是图像邻接，不能换算为物理夹持力或毫米间隙。r06和r07预览继续使用修正掩码。

- **[真机与r07当前对比](/data/omi_runtime/runs/module_v4_plain_material_20261122/real_vs_r07_plain_comparison.png)**：左为真实腕部照片，右为r07仿真模块与真实夹爪像素；相同区域裁剪，不额外调色，下方放大金属表面。
- [r07整体预览](/data/omi_runtime/runs/module_v4_plain_material_20261122/r07_plain_material_preview.png)：可见模块、夹爪和插槽。
- [r06有颗粒／r07无颗粒对比](/data/omi_runtime/runs/module_v4_plain_material_20261122/r06_vs_r07_grain_comparison.png)：保留为材质变更证据。
- [真机源帧](/data/omi_runtime/runs/wrist_module_outline_20261120T095830Z/frame_000.png) · [裁剪来源记录](/data/omi_runtime/runs/module_v4_plain_material_20261122/real_vs_r07_plain_comparison.json)。

对比仍能看到模块局部形状、拉手轮廓、插槽细节和光照差异。用户要求忽略的贴纸没有建模；没有为了掩盖差异给左右图单独调色。当前成果是固定开度、单帧静态混合预览，未接入`ContactInsertionEnv._capture()`，未验证随动作的映射、开合同步、动态遮挡或时序连续性。详见[混合腕部图像](../agent/simulation/evolution/hybrid-wrist-preview.md)。

## 物理仿真和训练链路

`omi_shapeforge`负责资产、MuJoCo场景／接触与双相机环境，`omi_proj`负责BC／SAC训练及接管经验。已形成规则示范→双相机观测→BC→带规则接管RL→关闭接管独立评估的初步链路。头部／腕部输入为真实渲染RGB（128×128、10帧历史）；状态与触觉仍padding，仿真真值供规则老师、奖励和评估使用。

新SIM-r06包含156件模块凸碰撞件、113件插槽外观、335件插槽凸碰撞件和7个等效弹性触点。原CoACD代理上边界多伸约0.31 mm造成假阻挡，已修正逐平面裁剪／恢复闭合凸体，保留失败候选。旧内部暗支撑未实测，保留它后深处有效高度约8.29583 mm、竖向每侧余量约0.04792 mm；这仍是重要模型不确定性。

| 实验 | 已有结果 | 适用范围 |
| --- | --- | --- |
| 新SIM-r06局部插入／退出 | 到位51.28169 mm；原步长及半步长均通过 | 居中接触与等效触点，非真实抓取 |
| 新SIM-r06反例 | 锁死触点、横偏±1 mm、偏航±2°均受阻 | 证明不是直接穿透后仅靠位姿判成功 |
| 新SIM-r06机械臂规则循环 | 3/3插入＋退出通过 | 种子7／19／41；最大数值侵入约0.00211 mm |
| 加新相机／夹爪外观的独立场景 | 2/2规则循环通过 | 种子19／41，尚未训练新视角策略 |
| 旧SIM-r03加权BC | 两批独立初态合计7/8自主成功 | 10回合训练示范，不使用在线接管评估 |
| 旧SIM-r03第一轮20回合接管RL | 自主测试8/8；接管训练19/20 | 接管来源为规则，不是真人 |
| 旧SIM-r03另一RL组合 | 接管训练20/20，自主测试0/4 | 训练接管成功不等于策略学会 |
| 旧BC／RL直接迁移新SIM-r06 | 各0/2 | 没有按新几何重新训练 |

旧实验完成真实网络更新和闭环测试，说明RL实现并非完全无效；但8个测试初态很少，BC与第一轮RL仅差1例，不能断言RL必然更好。新场景同时改变几何、孔位、接触和外观，迁移失败不能仅归因于视觉策略。**新尺寸＋新视角＋r07材质的10BC／20接管RL尚未执行。**

证据：[新尺寸接触报告](/data/omi_runtime/runs/measured_v4_sim_20261121/report.json)、[规则循环视频](/data/omi_runtime/runs/measured_v4_sim_20261121/robot_validation/robot_contact_cycle.mp4)、[旧策略迁移报告](/data/omi_runtime/runs/measured_v4_sim_20261121/old_policy_transfer/report.json)、[旧场景学习对照](/data/omi_runtime/runs/contact_intervention_study_20261121/final_comparison/report.json)。机制详见[训练记录](../../../omi_proj/docs/agent/training/evolution/contact-intervention-study.md)。

## 真实视觉感知的独立进度

既有无marker结构线原型在61帧上完成归属过滤，保留四组结构、剔除支持不足的右侧头部线；贴纸替换不变性9项检查通过。但位姿候选不是已认证真值，精确六维、遮挡后的相对深度和到位判断尚未通过。r07改色与合成图没有重新验证这些能力，也没有把旧V3特征绑定自动迁移到V4。详见[真实感知交接](2026-11-21-perception-progress-handoff.md)。

## 当前问题和下一步顺序

1. 固定下一轮实验的资产／观测合同：显式选择r07外观、新尺寸插槽与相机设置，另存新场景，保留旧成功实验。先复核双相机可见性、接触反例和规则循环。
2. 核对相机外参、夹持变换、6.9 mm测量口径及孔内支撑尺寸；现有模型有照片估计和深部通路假设，不能把名义间隙视为实测。
3. 若继续混合视觉，先做一小段运动序列，验证真实夹爪像素随开度变化、与模块的遮挡关系和时间同步，再接入实时观测；目前单帧不够证明可训练。
4. 在选定新场景重新采集10回合规则示范，再执行20回合带规则接管RL。分开记录接管率、训练到位率和关闭接管成功率，保留BC基线及独立测试初态。
5. 扩大扰动和测试范围，逐项评估材质／相机／混合图的收益；真实抓取、工具碰撞／惯量、摩擦、柔性与触觉仍需单独建立和验证。

## 复现与接续入口

当前材质资产目录`/data/omi_runtime/assets/optical_module_v4/r07/`；当前对比与渲染目录`/data/omi_runtime/runs/module_v4_plain_material_20261122/`。构建使用资产`build_scripts/`，本次两种对比的脚本`make_grain_comparison.py`、`make_real_comparison.py`及裁剪来源记录在运行目录。不要覆盖旧目录或直接沿用旧训练成功率。

- [仿真器持续记录](../simulation.md) · [当前总览](../current.md) · [Mesh持续记录](../mesh-development.md)。
- [新尺寸场景操作](../../tutorials/measured_v4_simulation.md) · [腕部相机／夹爪窗口操作](../../tutorials/wrist_camera_gripper.md)。
- [r07登记](../../manifests/module_material_r07_20261122.json) · [资源恢复登记](../../manifests/resources.json)。

本轮总结未修改mesh、物理参数或权重，也没有新增训练成绩。所有统计均注明所属历史实验；生成物保存在外部运行目录，仓库工作树中已有开发改动保持原样。
