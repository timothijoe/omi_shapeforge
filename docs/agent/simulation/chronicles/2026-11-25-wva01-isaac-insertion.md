# r15新版夹爪的Isaac插入视频交付

承接[前日版本核查](2026-11-24-video-asset-version-audit.md)。旧r2～r5视频实际WG-r10身份和原片哈希已记录；用户要求换新版并核查其他组件。

新增`SC-WVA01-ISAAC-FIXTURE-r01`，使用WVA-01／WG-r15全部49件原网格与两侧UV／PNG。OM-r08、当前SIM-r06／M1888来源插座、staged碰撞判据、URDF与相机逐项核对保留。点云从选定packet重新生成，对象几何数组与原当前模板相同。

GC-r01自由接触夹持的PhysX移植未通过移动门槛，失败另存。最终选择固定夹持合同，只采用GC-r01闭合参考，不称为自由夹持验收；packet、worker和影片说明均标注范围。

新PhysX CPU／PGS／5子步回合586步、一次reset通过，入口外先对准，最终深度51.281185mm稳定落座，worker退出0。连续470状态进入3×影片，542帧／18.0667秒；r15轮廓及标志已在实际RTX图像查看。全片解码、9个编码帧、FK／深度和源哈希检查通过。轻量92项29通过、63跳过；新合同数学8项通过。渲染shell在FILM_COMPLETE后回执143，成片／manifest已独立验证完整，不将原回执改写为0。

[完整成片与范围](../evolution/wva01-isaac-insertion.md) · [清单](../../../../manifests/wva01_isaac_insertion_20261125.json)。未新增网络、BC／RL或真机成绩。
