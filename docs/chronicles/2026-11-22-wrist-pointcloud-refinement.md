# 2026-11-22：保留r08并用扫描点云优化r09

按用户要求冻结r08完整82文件副本。由两段工具扫描的15组同步双目帧生成深度，11视角通过刚体配准／位姿图，结合审阅掩码得到约16.9万体素化工具点。原数据和旧资产保留。

另建WG-r09：修改8件指臂／衬垫局部网格，41件及相机参数不变。复核视角黑臂点到表面P90约6.30→1.90 mm；固定相机下腕部黑臂5行外缘平均约30.8→7.2 px。黄色视觉外缘改善有限，相机点云残差、绿色拉环和未观测面仍待处理。

[完整来源、建模、验证与限制](../agent/simulation/evolution/wrist-pointcloud-refinement.md) · [r08保留登记](../../manifests/wrist_tool_r08_preservation_20261122.json) · [r09登记](../../manifests/wrist_pointcloud_refinement_20261122.json)。
