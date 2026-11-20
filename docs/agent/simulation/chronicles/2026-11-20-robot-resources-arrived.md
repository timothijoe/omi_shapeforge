# 2026-11-20：OMI 外部资源补齐与离线模型预检

此前仿真阶段记录的缺少资产状态由本次上传解除。OMI 资源包恢复到独立基线，gzip CRC、7,361 项包内 SHA256 和 7,321 项源文件记录通过核对；旧绝对来源字符串未被当作包外读取指令。

`omi_proj/local` 链接到已验证外部资源，当前 Git 源码保留。补齐双臂 MJCF、相邻 MarvinCCS、Stand 派生模型和完整厂商目录，并发现两份 27 links／26 joints 的完整 URDF，各含四个滑动指关节，网格引用齐全。

原 MuJoCo 3.3.7 环境拒绝模型的新 compiler 语法，因此独立建立 Python 3.12／MuJoCo 3.15 环境。保留原 XML，模型编译、forward、项目 A 臂 preflight 及 EGL 静态图像通过。未进行动力学步进、抓取、策略推理、训练或硬件连接。

默认 MJCF 是含灵巧手／刀具的旧场景，不等于当前夹爪配置；完整 URDF 的参数和现场工具仍需核对。机器人尚未组合到光模块场景。证据见[迁移验证](../../../../manifests/transfer_validation.json)，最新资源边界见[能力说明](../evolution/robot-assets.md)。
