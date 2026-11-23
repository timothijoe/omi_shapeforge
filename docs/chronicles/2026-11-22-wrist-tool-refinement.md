# 2026-11-22：腕部相机与夹爪精修资产

综合两段新D435录制的四组双目帧、原视频和指尖照片，另建WG-DAIMON-REFINED-r05「双目参考精修版」。完成FoundationStereo深度推理、局部尺寸估计、49件Blender建模、相机／夹爪独立导出和MuJoCo开合预览。指臂120 mm、指尖40 mm、相机42×40×28 mm为建模估计，未进行实物计量认证。

改进独立凸起黑色接触面、渐窄银色壳、橙色衬垫真实开孔与筋、弯指轮廓、相机短座和外壳。拒绝不一致的相机正面55.9 mm高度外推；修正共面布尔孔边界后49件拓扑通过。参考模块无相交，但黑垫距模块约0.543 mm，并未形成力学夹持。

完整及独立GLB重开、Blender49件与OBJ一致、MuJoCo49mesh／2关节和镜头绑定通过；77个直接受保护旧文件未变。旧r04工具与r07模块保留，新资产未接入机械臂插入或策略训练。

[开发事实、证据及文件](../agent/simulation/evolution/wrist-tool-refinement.md) · [操作](../../tutorials/refined_wrist_tool.md) · [登记](../../manifests/wrist_tool_refinement_20261122.json)。

## 后续颜色纠正

用户指出衬垫应为黄色；另存WG-r06，只改两侧衬垫及横筋4件材质。49份OBJ与r05逐字节相同，相机GLB不变，Blender／GLB与MuJoCo同步改为暖黄色。实物／旧版／新版对比及验证见上方开发记录的最新修订段。
