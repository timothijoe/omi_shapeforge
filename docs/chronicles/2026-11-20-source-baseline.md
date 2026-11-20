# 2026-11-20：源码基线保存与复验

按 ENG-001 整理主项目和两个算法仓库的未提交内容，保留 omi_proj 原状态。先导出原 Git 历史、完整差异和新增文件，再分别保存本地提交；用户提供的 PROMPTS 原文一并保留。没有修改算法或运行层行为。

主项目运行版本为 `eb8da42`，FoundationStereo 为 `e46fa70`，BundleSDF 为 `b1a5587`，omi_proj 为 `963a7c2`。两个后端从原 master 建立 `feature/local-runtime-baseline`；主项目从 dev 建立整理分支接入既有仿真／文档，完成后 fast-forward 汇入本地 dev。main 继续保持空树，未推送。

四份源码 bundle 通过验证和独立克隆，恢复 HEAD 一致；原工作区和恢复副本各 4 项控制层测试通过。官方双目新运行输出 470,018 点；BundleSDF 组件新运行得到 2,893 组 LoFTR 匹配。两份运行记录均对应干净源码版本。

本阶段使用原有 GPU 环境与已编译扩展，未做从零编译或全流程重建；后续提交只补充文档和小型证据元数据。原交接中“后端适配未提交”的表述是早先时点的事实，当前已保存为本地版本，远端仍未同步。

恢复位置、完整版本及限制见[源码基线说明](../design/source-baseline.md)，机器可读证据见[基线清单](../../manifests/source_baseline_20261120.json)。
