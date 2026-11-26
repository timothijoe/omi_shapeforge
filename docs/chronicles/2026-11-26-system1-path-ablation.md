# 2026-11-26：System1路径增益配对实验完成

按用户要求增加数据与交互，比较GT路径条件化System0和只接受目标／共同历史的System0。新增33条成功规则示范，25条训练9162步、8条验证2923步。每组两个种子，每模型BC20000更新及12000有效在线交互，共48000步。

最终在相同24个未见目标位置无接管测试：种子340000路径24/24、无路径0/24；种子341000路径24/24、无路径20/24。汇总48/48对20/48，差58.33个百分点。只代表当前配方和两个种子，无路径第二种子已经能够自主完成大多数目标，不能把第一种子失败视频当作纯System0能力上限。

第一对训练完整结束后，总控收到来源未确认的SIGTERM；第二对均从3000步检查点继续9000步，保留相同新episode seed342000。最终第二对各11999梯度更新、第一对各12000；同一配对内匹配。原失败分支、未保存轨迹和回执均保留，通过routes文件指向最终有效模型及trace，未将失效分支计入48000步。

全部replay的实际／提议动作、历史、奖励、终止与腕力核验通过。学习端、物理端源码快照一致；初始actor及BC抽样在各配对内一致；测试模型哈希正确、全部teacher requests为0、无路径输入槽位全零。第一对无路径训练78%规则接管，仅2640步由策略执行，说明总预算配对并不等于自主探索量配对。

用户要求录制视频并质疑右侧是否接受过BC和RL。固定测试首例已制作双视图回放，来源链额外审核确认BC20000→加载BC模型→SAC12000→最终权重评估→视频来源一致。视频只展示一个种子，结合两种子完整结果解释。

- [能力记录与完整边界](../agent/simulation/evolution/system1-path-ablation.md)
- [视频交付记录](2026-11-26-system1-path-video.md)
- 运行根：`/data/shapeforge/runtime/runs/s1_path_ablation_20261126`
- 协议／恢复：`protocol.json`、`continuation_protocol.json`、`routes.json`
- 最终统计：`summary.json`、`comparison.png`
- 模型来源链：`video_training_lineage_audit.json`
- 清单：`manifests/system1_path_ablation_20261126.json`

复算：使用 `omi_sim_train/bin/python scripts/simulation/summarize_path_ablation.py --run <运行根>`。本次无新增视觉System1训练、旋转扰动、真机或自动切换外观资产。
