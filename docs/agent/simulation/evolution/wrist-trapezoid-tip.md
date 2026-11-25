# WG-r12：梯形俯视面与银色壳／胶皮前端齐平

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

用户指出r11仍有三角形观感，并明确“同一高度”是指**沿夹爪伸出方向，银色壳最前端与黑色胶皮最前端齐平**。据此另建WG-DAIMON-TRAPEZOID-r12「梯形齐平指尖候选」，保留r11和所有旧版本。

## 本次几何

两侧银色壳的主轮廓以四点构成梯形，前后端边平行，外侧边改为直线；不再采用逐段收尖曲线。倒角保留0.6 mm，名义前边7 mm、后边16 mm；这些宽度和倒角仍是建模选择，不是实物测量。

实际黑色胶皮本体完全不动，逐侧读取它的最大TCP Z作为银色壳最前端目标。原黑色包边还比胶皮多伸出约0.35 mm，若只改银壳会继续露在前面，因此两份包边缩短并退到胶皮前端后0.2 mm。没有缩短胶皮本体或修改夹持间隙。

| 实际导出网格 | 左侧 | 右侧 |
| --- | --- | --- |
| 银色壳最大TCP Z | 210.5000019 mm | 210.5000019 mm |
| 胶皮本体最大TCP Z | 210.5000019 mm | 210.5000019 mm |
| 两者前端差 | **0 mm** | **0 mm** |
| 包边前端 | 210.2999985 mm | 210.2999985 mm |

这里的0是网格坐标约束验证，不代表实物加工精度或所有透视视角中的屏幕边缘重合。正俯视及包络示意用来检查实际伸出方向。

## 验证与文件

49件工具网格闭合、法向一致、正体积且无退化面；Blender／GLB重新打开、包络及MuJoCo加载检查通过。修改2件银色壳和2件黑色包边，其余45份OBJ保持r11原字节，其中包括两块胶皮。相机独立GLB、相机参数、模块参考变换、18.4 mm名义夹持间隙不变。当前模块／工具参考装配无网格相交；真实抓取和机器人路径未重新验证。

- [正俯视、对齐示意与r11对照](/data/omi_runtime/runs/wrist_trapezoid_tip_20261122/trapezoid_alignment_comparison.png)
- [r12 Blender](/data/omi_runtime/assets/daimon/wrist_gripper_trapezoid_r12/WG-DAIMON-TRAPEZOID-r12.blend) · [完整GLB](/data/omi_runtime/assets/daimon/wrist_gripper_trapezoid_r12/WG-DAIMON-TRAPEZOID-r12.glb)
- [夹爪GLB](/data/omi_runtime/assets/daimon/wrist_gripper_trapezoid_r12/gripper.glb) · [相机GLB（不变）](/data/omi_runtime/assets/daimon/wrist_gripper_trapezoid_r12/wrist_camera.glb)
- [前端对齐数据](/data/omi_runtime/runs/wrist_trapezoid_tip_20261122/front_alignment.json) · [完整验证](/data/omi_runtime/assets/daimon/wrist_gripper_trapezoid_r12/validation.json) · [登记](../../../../manifests/wrist_trapezoid_tip_20261122.json)

运行目录`/data/omi_runtime/runs/wrist_trapezoid_tip_20261122/`；脚本和证据随资产保存。旧r11与固定WG-r10＋OM-r08交接清单保持原样；其他Agent评估新形状时显式读取r12登记。旧指尖角点拟合和图像成绩不自动沿用，本轮没有新增相机标定、训练或实物尺寸认证。
