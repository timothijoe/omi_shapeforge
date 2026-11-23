# 2026-11-22：混合腕部图像反馈与黑色接触面修正

用户对已打开的“真实夹爪像素＋仿真模块／插槽”首版预览反馈“整体效果很不错”，要求把当前进展记录到docs。随后补充`20261122-000122.jpg`、`20261122-000200.jpg`，明确夹持光模块的实际部位是白色指尖壳内侧的黑色圆凸接触面，而非后方橙黄色内衬。

## 已完成

1. 保留首版预览及其来源报告，记录用户的整体视觉正向反馈和接触面纠正，不回写为动态／训练验收。
2. 确认首版前景漏掉了两处黑色接触面；从同一真实腕部源帧补回两侧接触面，并修正旧模块排除掩码误吞掉的少量黑色边缘像素。
3. 继续使用用户提供的`wrist_intrinsics_1920x1080.json`和原首帧位姿先验；仿真内容仍为V4-r05「双窗尾槽版」和SIM-r06中的18.8 × 8.8 mm插槽。没有变形或覆盖源mesh。
4. 新预览保留黑色接触面核心647／543个真实像素；两侧到可见模块边界的最近距离均为1个原分辨率像素，仅验证图像邻接。
5. 保存修正后全图、局部构图、黑色接触处放大、左右掩码、区域坐标、参考照片与哈希，并在桌面打开修正图。

## 当前产物

- [修正预览](/data/omi_runtime/runs/hybrid_black_contact_20261122/hybrid_black_contact.png) · [黑色接触面放大](/data/omi_runtime/runs/hybrid_black_contact_20261122/black_contact_detail.png)。
- [完整图](/data/omi_runtime/runs/hybrid_black_contact_20261122/hybrid_full.png) · [首版对照](/data/omi_runtime/runs/hybrid_hand_preview_20261121/hybrid_detail.png)。
- [本轮报告](/data/omi_runtime/runs/hybrid_black_contact_20261122/report.json) · [登记](../../manifests/hybrid_black_contact_20261122.json)。

## 未完成范围

当前仍是单帧、固定开度的合成实验。未把黑色接触面启用为真实力学抓取，未修改实时观测接口，也未验证动态遮挡、动作同步、视频连续性或策略收益。两张新照片确认了接触部位归属，没有给出接触面尺寸、材料参数或独立相机外参。

持续事实维护在[混合腕部图像记录](../agent/simulation/evolution/hybrid-wrist-preview.md)，并同步[仿真器记录](../simulation.md)和[Mesh开发记录](../mesh-development.md)。
