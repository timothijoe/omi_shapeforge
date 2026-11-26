# 2026-11-25 System1沿途姿态坐标系

用户基本认可远距离三维资产／二维投影的显示逻辑，并明确要求间隔若干点画坐标箭头表达orientation。复用已有三组冻结预测，从现有几何解码器的实际SE(3)插值构建模块尖端坐标系；每8个原始采样点绘制一组，共0%、25%、50%、75%、100%五处。红X、绿Y、蓝Z，模块插入方向−Y，三轴长6 mm。40 mm案例预测段太短，单独只画末端，避免重叠。

输出 `/data/shapeforge/runtime/runs/hier_s1_orientation_20261125_v1/`，包含三例预测／GT分开的6张3D／2D对照及3份含真实三维箭头的Blender场景。旧图、路径、模型与网格保持。

共26组坐标系与生产 `ReferenceProvider.features` 核对，最大原点差7.65e−6 mm、旋转矩阵元素差1.31e−8，OpenCV鱼眼投影最大差5.68e−13显示像素。源哈希保持；新增脚本仅负责姿态表达，没有训练或策略执行。效果待用户复审。

[能力事实与图片入口](../agent/simulation/evolution/system1-path-visualization.md) · [证据清单](../../manifests/system1_orientation_visualization_20261125.json)

## 后续：中心原点与前向X轴

用户认可三轴展示后要求红X向前、蓝Z向上，并将原点置于模块正中央。新增展示基底：X_new=−Y_old、Y_new=X_old、Z_new=Z_old；原点取下壳、左右壁、上壳的包围盒中心，不含拉环、尾塞和局部凸起附件，也不称质量中心。曲线同步换为中心轨迹；原TCP参考和模型不改。

新输出 `/data/shapeforge/runtime/runs/hier_s1_orientation_center_20261125_v1/`，原尖端版保留。26组生产参考核对原点最大差7.45e−6 mm，旋转矩阵元素差1.31e−8，OpenCV投影差3.22e−13显示像素；中心位置、右手轴向及源哈希保持检查通过。新场景中的曲线和箭头均已使用中心坐标，默认展示参数更新，旧版仍可显式复现。[新证据清单](../../manifests/system1_center_frame_visualization_20261125.json)

## 再修正：参考点固定在夹爪中心

用户指出模块可能滑动，因此改选夹爪中心。新版原点由左右接触垫的几何中点确定，约为原TCP `(0,0,198.5)` mm，轴向取X=原TCP的+Z、Y=−Y、Z=+X。没有使用模块位姿构建该坐标系；原夹持开度和旧TCP参考保持。

新输出 `/data/shapeforge/runtime/runs/hier_s1_gripper_frame_20261125_v1/`，含三例预测／GT对照及Blender场景。26组三轴与生产参考换算原点误差小于7.28e−6 mm，独立鱼眼投影差4.02e−13显示像素；修改检查副本中的模块平移和旋转后，夹爪坐标保持不变。该检查仅证明坐标构建不依赖模块位姿，不是物理滑移实验。真机工具中心标定、动态夹持关系估计、滑移补偿及正式动作合同仍未实施。[夹爪坐标证据](../../manifests/system1_gripper_frame_visualization_20261125.json)
