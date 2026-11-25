# WG-r13：按用户红线修正斜边与根部平段

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

后续澄清：用户红线仅为示意，不能作为精确比例目标；[r14已回到原始实拍复核](wrist-tip-photo-review.md)。本页保留r13当时的建模过程。

用户提供`20261122-222136.jpg`，在r11正俯视截图上标出了两侧银色外壳的目标外缘。正确理解是：**前段斜边向外展开，在靠近黑色指臂处接一段与内侧直边平行的根部平台**。不能继续只加宽前端，或仅以“前后端边平行”的四点梯形替代该标注。

另存WG-DAIMON-SHOULDER-r13「斜边平台指尖候选」。只改两份银色外壳，47份其他OBJ包括胶皮、黑色包边及相机均保持r12字节；相机GLB、夹持变换和名义18.4 mm间隙不变。

## 轮廓与前端约束

标注图来自已知正交渲染视图，按截图内模型画面的缩放作近似换算：根部外缘暂定|Y|=30 mm，平台从TCP Z=173.7至185 mm，长度约11.3 mm，再以直斜边接到前端|Y|≈18 mm。两侧镜像生成，0.6 mm倒角保留。这是用户对模型截图的形状约束，不是实物尺寸测量。

主轮廓有前端短面、外侧斜段、根部平段及闭合边，区别于r12的简单四点梯形。继承用户已确认的轴向齐平要求：左右银色壳与胶皮本体最大TCP Z均为210.5000019 mm，差0；黑色包边仍退后约0.2 mm，本轮未再改它。

[红线与拟定轮廓叠加](/data/omi_runtime/runs/wrist_marked_tip_20261122/marked_outline_overlay.png) · [原标注／新版正俯视对照](/data/omi_runtime/runs/wrist_marked_tip_20261122/marked_outline_comparison.png)。

## 验证和文件

49件工具网格闭合、法向一致、正体积，无退化面；GLB／Blender重开、包络及MuJoCo加载检查通过。当前参考模块无网格相交，74个直接受保护r12文件未变。未重跑腕部像素拟合、机器人插入或训练，旧版本的像素成绩不能自动转记。

- [r13 Blender](/data/omi_runtime/assets/daimon/wrist_gripper_shoulder_r13/WG-DAIMON-SHOULDER-r13.blend) · [完整GLB](/data/omi_runtime/assets/daimon/wrist_gripper_shoulder_r13/WG-DAIMON-SHOULDER-r13.glb)
- [夹爪GLB](/data/omi_runtime/assets/daimon/wrist_gripper_shoulder_r13/gripper.glb) · [相机GLB（不变）](/data/omi_runtime/assets/daimon/wrist_gripper_shoulder_r13/wrist_camera.glb)
- [验证](/data/omi_runtime/assets/daimon/wrist_gripper_shoulder_r13/validation.json) · [前端齐平检查](/data/omi_runtime/runs/wrist_marked_tip_20261122/front_alignment.json) · [独立登记](../../../../manifests/wrist_marked_tip_20261122.json)

固定WG-r10＋OM-r08交接清单不变；r11、r12保留。其他Agent使用本次新外形时，从上述r13登记显式加载，坐标和组件合同仍沿用[接入说明](wrist-assets-handoff.md)。脚本与证据保存在资产build_scripts／evidence，完整运行目录为`/data/omi_runtime/runs/wrist_marked_tip_20261122/`。
