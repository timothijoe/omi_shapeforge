# 感知当前摘要

截至 2026-11-20，主 CLI 可在分离环境中执行两种样例；本机另已复跑便携包的已确认光模块 ROI 配准。

- [双目与组件](evolution/stereo-and-backends.md)：官方双目样例、BundleSDF 原生／GPU 组件实际验证通过；两后端适配已保存为本地提交并新跑 smoke，通过范围未扩展到完整重建。
- [数据与回放](evolution/data-and-replay.md)：9 包完整恢复；V2 冻结几何复验通过，04 仅保留快照而未启用。
- [条件刚体配准](evolution/confirmed-registration.md)：包内 10 万点样例与固定 mesh 可用，检查残差复现；尚无绝对位姿真值或全场景自动检测验收。

便携配准尚未成为 `omi-shapeforge smoke` 子命令，须调用包内脚本。01 工程快照已恢复并通过 V2 冻结几何回放；02 原始／处理数据已完整解压并校验，FoundationStereo 的 DATA 也已完整恢复，04 作为未重定位的历史环境快照独立保留，详见[资源接口](../interfaces/local-resources.md)。

阶段依据见[编年索引](chronicles/README.md)。
