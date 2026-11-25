# 腕部相机、夹爪与光模块：其他Agent接入说明

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

需要真正夹住时使用[GC-r01双胶垫接触修订](wrist-contact-closure.md)；WVA-01的固定参考`tool_to_module`不是通用夹持约束。新场景需初始化已夹紧关键帧或执行闭合并通过双侧接触门控。

**当前已接受版本为[WVA-01「腕部实拍对齐版」](wrist-visual-wva01.md)**，使用[WVA-01固定清单](../../../../manifests/wrist_visual_wva01_20261122.json)。下方WG-r10的清单、路径和统计为历史接入快照；组件坐标合同可参考，r15须额外保留UV／纹理。

可选新外观：[WG-r15 DAIMON表面标志](wrist-logo.md)，从[登记](../../../../manifests/wrist_logo_20261122.json)显式选择；几何沿用r14，导入须保留UV／纹理，固定组合不变。

可选最新银壳候选：[WG-r14原始实拍比例复核](wrist-tip-photo-review.md)，显式读取[独立登记](../../../../manifests/wrist_tip_photo_review_20261122.json)；固定WG-r10＋OM-r08组合不变。

可选新修订：[WG-r13按红线修改的斜边／根部平段](wrist-marked-tip.md)，从[独立登记](../../../../manifests/wrist_marked_tip_20261122.json)选择；固定WG-r10＋OM-r08清单保持不变。

可选新修订：[WG-r12梯形俯视面／前端齐平候选](wrist-trapezoid-tip.md)，由[独立登记](../../../../manifests/wrist_trapezoid_tip_20261122.json)选择；固定WG-r10＋OM-r08清单不变。r11作为上一候选保留。

后续接入：[已按本清单完成独立Isaac装配、开合与鱼眼检查](wrist-bundle-isaac.md)。下文第4节保留交接时旧挂载器的缺口；现有代码已补相机组件/颜色与17件映射，但仍需要新的安装解，不能复用旧r04结果。固定版本清单的历史状态不改写。

可选新修订：[WG-r11银色指尖宽钝头／倒角候选](wrist-fingertip-chamfer.md)，通过[独立登记](../../../../manifests/wrist_fingertip_chamfer_20261122.json)显式选择。下方固定交接组合仍是WG-r10＋OM-r08，r10的角点／图像统计不能直接转记给r11。

**以下为历史WG-r10工具＋OM-001/V4 r08光模块接入快照。** 从[固定版本清单](../../../../manifests/wrist_visual_asset_handoff_20261122.json)解析路径和哈希，再按[运行教程](../../../../tutorials/reuse_wrist_visual_assets.md)加载。项目任务优先级、真实感知和Isaac进展以[当前总览](../../../current.md)及相应领域记录为准；本页交接视觉资产及静态观测结果。

## 1. 版本选择

| 对象 | 本次入口 | 使用范围 |
| --- | --- | --- |
| 腕部相机／夹爪 | **WG-DAIMON-OBS-r10**，49件 | 当前内沿遮挡修正；47件OBJ、相机GLB及镜头／夹持变换与r09一致 |
| 光模块 | **OM-001/V4 r08**，17件 | 连续U形件＋16件保持r07原字节的主体；纯色材质，无新增颗粒 |
| 插槽视觉／物理来源 | **SIM-OM001-OS001-r06** | 静态组合场景依赖；孔口18.8×8.8 mm、窄边6.9 mm口径仍有假设 |
| 独立插槽展示 | OS-001/M1888-r01 | Blender／GLB，含等效触点视觉；不是单靠GLB就有接触动力学 |
| 对照版本 | WG-r09、冻结WG-r08、OM-r07 | 保留在原路径，做前后对照或回退 |
| 已暂定的模块基线 | OM-001/V4 r05「双窗尾槽版」 | 仍保留其原身份；新视觉候选没有自动覆盖它 |

WG-r08是旧工具版本，OM-r08是新光模块版本，SIM-r06是接触装配，不能只凭后缀数字选择。也不要按目录mtime、字符串“latest”或拒绝稿目录猜版本。

## 2. 文件与来源

工具根目录：`/data/omi_runtime/assets/daimon/wrist_gripper_observation_r10/`。
模块根目录：`/data/omi_runtime/assets/optical_module_v4/r08/`。

各目录有`asset_manifest.json`、`delivery_manifest.json`、Blender／GLB、逐件OBJ、验证、构建脚本和关键证据。**先校验清单，再复制到自己的新输出目录修改**；构建脚本通常含本机绝对路径及固定输出，不宜直接重跑来覆盖已发布资产。

- 完整工具GLB含49件工具，不含光模块；独立`gripper.glb`与`wrist_camera.glb`保留公共TCP坐标，不自动居中。
- 工具Blender额外含17件光模块参考展示，展示拉环−35°，不是额外工具件。
- 模块GLB／OBJ含17件模块，默认拉环为中性姿态；组合渲染时另施加−35°展示变换。
- 纹理、MTL、`meshes/textures/`需与OBJ一起保留。Blender／GLB材质已打包；沿用r07纯色，不添加噪声／颗粒。
- [历史r10组合登记](../../../../manifests/wrist_primary_refinement_20261122.json)、[资产版本](../../../asset-versions.md)、[资源恢复清单](../../../../manifests/resources.json)分别记录结果、身份与来源。

完整静态组合场景：`/data/omi_runtime/runs/wrist_primary_refinement_20261122/final/audit_scene.xml`。它除这两份资产外还引用SIM-r06、OM-r07中的旧网格／纹理；共675个文件依赖已检查，详见[依赖索引](/data/omi_runtime/runs/wrist_asset_handoff_check_20261122_181528/scene_dependencies.json)。只复制两份新资产目录不足以在另一台机器直接加载这份XML。

## 3. 坐标、单位和变换方向

统一使用米，右手系。工具原点是TCP法兰参考，+Z指向指尖，+X指向相机／顶面，两指沿Y开合。模块逐件OBJ使用公共模块局部坐标，不能逐件重新归中。 GLB导出关闭自动Y-up转换（`export_yup=False`），按清单中的资产坐标解释；目标引擎需要轴转换时在父变换中显式处理一次，避免重复旋转。

清单字段`tool_to_module`的实际含义是 **`T_TCP_from_module`**：

```python
p_tcp = R_tcp_from_module @ p_module + t_tcp_from_module
T_world_from_module = T_world_from_tcp @ T_tcp_from_module
```

字段名称可能误导方向，以这两个式子及清单内的矩阵为准。当前平移约(−6.94,−0.65,237.65) mm，仅是参考帧的固定展示关系，不能赋给全部287个样本作为真值。

`camera.xyaxes_tcp`前3项是相机右方向、后3项是上方向；`optical_forward_tcp`是前方向。OpenCV光学坐标x右、y下、z前，因此：

```python
R_tcp_from_camera_cv = np.column_stack([right_tcp, -up_tcp, forward_tcp])
T_camera_cv_from_module = np.linalg.inv(T_tcp_from_camera_cv) @ T_tcp_from_module
```

MuJoCo相机局部+Z朝后，不能直接把它的朝后轴当OpenCV的z前。若使用MuJoCo四元数，顺序为wxyz；其他引擎需要按其接口显式转换。

如果挂到机器人某个link：`T_link_from_mesh = inverse(T_world_from_link) @ T_world_from_tcp`，因为mesh顶点已在TCP系。关节运动由父link提供，避免把同一个开合位移再加两遍。

## 4. 旧挂载代码的兼容缺口

当前`src/omi_shapeforge/sim/wrist_tool_scene.py`仍是旧工具的挂载实现，只识别`base/jaw_left/jaw_right`。r10还有`camera/camera_mount`，**直接调用会在部件映射处失败**，该函数不是已经适配r10的通用接口。

按当前左臂URDF名称扩展时应明确映射：

```python
parents = {
    "base": "TCP_Link_L",
    "camera": "TCP_Link_L",
    "camera_mount": "TCP_Link_L",
    "jaw_left": "Arm_L10_Link",
    "jaw_right": "Arm_L11_Link",
}
rgba = part.get("mujoco_rgba", part["color"])
```

后一句很重要：黄色件有显式MuJoCo颜色适配，旧函数只读`color`会重新出现偏红等显示差异。相机不能挂到活动夹指link。

还需按新`tool_to_module`重算IK／预插入目标和净空。不要复用旧r04的195 mm安装解或其1.96 mm净空结论。`integration_joint_reference_qpos_m=0.0313`是继承的旧URDF展示参考，不是真机开度标定；独立预览用每指0～12 mm的额外滑动量，两者不能混用。本次交接没有修改旧挂载代码或完成新的机器人安装验收。

## 5. 17件模块的映射与拉环

读取模块`mujoco_visual_patch.json`。保留件使用`source_part_index`映射回原视觉索引；移除原绿色视觉geom `sim_module_008_visual`、`sim_module_010_visual`，添加新U形视觉件。不能把17件列表按原18件的顺序直接逐项替换。

拉环绕模块系X轴、假设铰点`(0,0.0359,0.0016)` m旋转。实现为`p' = pivot + R_x(theta) @ (p - pivot)`；若使用子body，其pos为`pivot - R_x(theta) @ pivot`。组合展示取−35°。已检查0／−25／−35°，−40°会碰黑色胶塞；不能据此宣称连续运动范围或铰链力学已标定。

拉环是用户指定的次要因素。位姿估计沿用现有感知工具对绿色附件／假设内部阴影块的排除策略，不把它们当刚体配准依据；[当前头腕位姿审阅工具](../../perception/evolution/head-wrist-pose-review.md)仍使用其已登记的主体模型，不应未经映射就替换标注顶点或重写用户已保存的位姿。

## 6. 鱼眼观测与查看窗口

使用`observation_projection`里的K、D及1920×1080域。当前相机壳尺寸、安装外参和K／D与新批次的绑定仍是候选，不是硬件标定真值。

- `fovy_degrees=90`用于针孔／六面采样，**不是最终鱼眼模型**。原生查看器2键也只是针孔检查视角。
- `render_final.py`的六面渲染＋鱼眼重投影输出才与原始腕部图同域；导入GLB本身不会自动建立这个相机或变换。
- 不应把展示图的裁剪／放大当作训练输入或像素坐标真值。后续缩放／裁剪要在真实与仿真两侧一致，并更新投影坐标。
- 本次纯仿真对比没有粘贴真实夹爪；旧hybrid真实像素叠加实验是另一条独立路线，不要混用其观感作为mesh准确证据。
- 全局头部—腕部外参会随机械臂状态变化。本资产只给出相机相对工具的候选；感知工具里的`T_wrist_from_head`仍按样本维护。

## 7. 不同任务如何接续

| 接收任务 | 可以直接复用 | 接收方需要完成 |
| --- | --- | --- |
| 模型查看、外观编辑 | Blender／GLB／OBJ、共同坐标和当前对比 | 另存新修订，保留原材料／尺寸来源，更新mesh记录 |
| 静态图像／视觉回投影 | 组合XML、相机参数、鱼眼渲染脚本、逐件语义 | 在独立目录重现，检查遮挡与坐标，不把候选当标定真值 |
| 头腕点云／位姿审阅 | 主体尺寸、语义部件、当前帧约定和数据来源 | 保留既有人工标注；逐样本估计／验证，不复制固定夹持变换为标签 |
| 机器人MuJoCo接入 | r10视觉mesh、命名和挂载参考 | 适配组件／颜色映射、重算IK／TCP、重测工具—插槽路径与相机绑定 |
| Isaac/USD接入 | 公共米制mesh与变换、视觉材料依据 | 独立导入／材质／鱼眼适配和验证；不假定既有Isaac试验使用了r10 |
| BC／RL | 旧训练流程接口和新视觉资产来源 | 先建立新观测／动作／奖励合同并验证接触；重采示范和评估，旧成功率不移植 |

r10工具碰撞关闭，质量／惯量是展示占位，模块固定附着；组合场景只调用`mj_forward`，没有动态抓取。这份混合了旧物理来源与新外观的静态XML不能直接作为新动力学验收结果。新U形件也未生成专用碰撞分解。状态／触觉、真实接触、整机碰撞及策略收益不在本交付验收范围。

## 8. 已验证结果与验收方式

- 工具49件、模块17件；模块16件主体保持r07原字节。文件重开、单位／包络、工具网格及当前参考姿态无相交检查通过。
- 参数锁定后的004／007／011单元，黄色外缘均值10.93→6.17 px；黑臂7.33→7.53 px基本不变。只覆盖选定外缘，非全图精度。
- 内沿局部点云P90约0.71→1.00 mm的小幅退步有记录，整体黑臂P90约1.90 mm。未认证实物尺寸。
- 微调镜头稿因相机点云贴合变差被拒绝；不要从`draft_camera_micro`加载正式资产。
- 本次交接额外验证：两份资产哈希和675个场景依赖可读；在新目录完整运行鱼眼渲染，输出1080×1920×3，原6个输出文件未变化。新旧图平均通道差约3.22e−7（非逐像素完全相同），不应把微小GPU渲染差异当失败。

[交接验证记录](/data/omi_runtime/runs/wrist_asset_handoff_check_20261122_181528/verification.json) · [主体开发与取舍](wrist-primary-refinement.md) · [拉环开发](module-u-handle.md) · [点云来源](wrist-pointcloud-refinement.md)。接入时先复验载入和坐标，再做与任务相称的检查；扩展仓库挂载／观测代码需执行AGENTS.md规定的控制层及相关环境集成测试。

## 9. 给接收Agent的简短任务说明

> 先读AGENTS.md及docs/agent/simulation/evolution/wrist-assets-handoff.md，从manifests/wrist_visual_asset_handoff_20261122.json固定版本、路径和哈希。视觉组合是WG-r10＋OM-r08；不要覆盖源资产、旧实验或人工标注。在新的/data/omi_runtime/runs目录复现静态结果。按任务适配坐标、相机、部件与材料；机器人接入前修正旧挂载脚本的组件映射并重新验证。区分静态视觉、接触仿真、位姿候选和训练结果，回写新的manifest、领域记录及阶段文档。
