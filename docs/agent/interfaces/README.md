# 接口索引

- [腕部／模块视觉资产接入合同](../simulation/evolution/wrist-assets-handoff.md)：版本、坐标方向、部件语义、材料、鱼眼与运行依赖。

- [CLI、Python 入口和退出语义](cli.md)
- [配置文件与路径解析](configuration.md)
- [数据格式、坐标和单位](data-formats.md)
- [运行与产物合同 v1](run-contract.md)：ENG-002 定版规范、状态规则、流程要求与旧格式适配；两个 smoke 与 MuJoCo 已接入，旧格式批量转换器尚未实现。
- [本地资源与恢复](local-resources.md)
- [外部算法、仿真和机器人系统](external-systems.md)

主 CLI 与直接脚本是不同接口；便携配准脚本来自外部包，不能写成已存在的主 CLI 子命令。
