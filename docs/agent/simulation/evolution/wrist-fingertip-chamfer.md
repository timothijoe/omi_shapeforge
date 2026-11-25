# WG-r11：较宽的钝头与银色指尖倒角候选

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

2026-11-22，用户指出模型夹爪前段过尖，真机有倒角且两侧更宽。结合近照`20261122-000200.jpg`、俯视照`20261122-113448.jpg`及既有扫描点，本轮另建 **WG-DAIMON-CHAMFER-r11「宽钝头倒角候选」**。

## 修改与估计范围

旧r10的银色壳几乎收成三角尖端。新版本仅向外加宽左右银色外壳的前段，留下有限宽度的短前端面，并加0.6 mm单段倒角。保留根部位置和主要内侧平面，黑色凸接触面及名义18.4 mm夹持间隙不变；外壳深度方向X范围仍为−10～13.5 mm。

新轮廓、名义端面宽4.6 mm及0.6 mm倒角均为照片参考下的建模选择，**不是官方或卡尺尺寸**。实际导出截面在TCP Z=210.8 mm处，单侧银色壳的径向宽度约1.57→4.71 mm；Z=200 mm处约5.19→8.56 mm。它说明模型确实加宽，不能拿这些数值当作实物测量。

相机、模块参考变换、黑色接触垫、黄色衬垫和其他47份工具OBJ均保持r10原字节；没有为了此轮照片重新拟合相机或扩大两指间距。

## 验证与对照

- 49件网格闭合、法向一致、正体积、无退化面；完整／独立GLB及Blender重开通过。
- 两个银色壳修改，其余47件、相机独立GLB、相机／夹持参数不变。91个受保护r10文件哈希未变。
- 当前模块与−35°U形件参考装配无网格相交，黑垫到模块距离维持原值。未重新验证机器人插槽路径或物理抓取。
- 既有点云中粗选的26897个指尖表面点，到银色壳的单向距离中位约0.97→0.71 mm、P90约5.38→3.26 mm。这些点云有分割、配准和指尖锚定误差，不能作为独立实物精度认证。

[照片／r10／r11外形对比](/data/omi_runtime/runs/wrist_fingertip_chamfer_20261122/fingertip_comparison.png) · [保持相机不变的腕部局部对比](/data/omi_runtime/runs/wrist_fingertip_chamfer_20261122/wrist_tip_comparison.png)。新旧模型采用相同观察角度和灯光，实物照片未做精确视角配准。

[网格与间隙检查](/data/omi_runtime/assets/daimon/wrist_gripper_chamfer_r11/validation.json) · [导出截面](/data/omi_runtime/runs/wrist_fingertip_chamfer_20261122/tip_cross_sections.json) · [点云参考检查](/data/omi_runtime/runs/wrist_fingertip_chamfer_20261122/scan_tip_comparison.json)。

## 文件与其他Agent使用

- [Blender](/data/omi_runtime/assets/daimon/wrist_gripper_chamfer_r11/WG-DAIMON-CHAMFER-r11.blend) · [完整工具GLB](/data/omi_runtime/assets/daimon/wrist_gripper_chamfer_r11/WG-DAIMON-CHAMFER-r11.glb)
- [夹爪GLB](/data/omi_runtime/assets/daimon/wrist_gripper_chamfer_r11/gripper.glb) · [相机GLB（未改）](/data/omi_runtime/assets/daimon/wrist_gripper_chamfer_r11/wrist_camera.glb)
- [r11候选登记](../../../../manifests/wrist_fingertip_chamfer_20261122.json)

既有[固定交接清单](../../../../manifests/wrist_visual_asset_handoff_20261122.json)仍固定WG-r10＋OM-r08，未被静默改写。其他Agent若要评估新前端，应显式读取r11登记；部件索引与坐标合同保持一致。指尖角点发生变化，旧版约3px的角点拟合统计不能自动转记到r11，原人工对应也应重新检查。

运行目录为`/data/omi_runtime/runs/wrist_fingertip_chamfer_20261122/`，脚本与证据随资产保存。查看比较图可运行`view_comparison.py`；用omi_mesh_audit环境运行`view_tips.py`可打开自由视角的指尖近景，鼠标缩放／旋转。旧版本和训练场景保留。
