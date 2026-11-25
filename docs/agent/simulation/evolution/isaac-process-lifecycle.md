# Isaac进程收尾：143排查与即时回执

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../../interfaces/local-resources.md)。

后续长运行检查：[分阶段重训](staged-retraining.md)已完成，初始化到最终评估及worker均有原生退出0回执，clean shutdown完整。这验证本轮完整流程的收尾，仍不证明历史143来源。

2026-11-23，用户要求先排查[在线恢复三例之后的退出143](online-insertion-recovery.md)，再尝试BC／RL重训。本轮短复现没有重现143，历史信号发送者仍未知；不能把监控补强写成已确定并根治历史原因。

## 实际排查

运行根为`/data/omi_runtime/runs/isaac_shutdown_audit_20261123`。用`strace`跟踪进程／线程发送的kill、tgkill和退出，以及SIGTERM信号，分别执行：

| 拓扑 | 操作 | 结果 |
| --- | --- | --- |
| 调度器、worker、客户端共用进程组 | 独立客户端reset、1步零动作、退出；调度器重新连接并shutdown | 客户端0、worker0、外层0；shutdown确认及clean文件完整 |
| worker和客户端各有独立进程组 | 同一操作顺序 | 客户端0、worker0、外层0；shutdown确认及clean文件完整 |

两组均未观察到SIGTERM；运行日志仅能证明这两条短路径正常，不能排除长运行或外部监督导致的中断，也不能给历史运行补写原生退出码。原生轨迹、事件时间、PID／PGID、系统调用跟踪和每组外层退出码均保存。短测试没有插入成功含义，不加入任何策略或规则成功率分母。

## 已补强的监督实现

旧临时调度器只在末尾统一写回执。一旦外层先被终止，即便某阶段已经结束，也可能没有独立原生退出证据。新增`src/omi_shapeforge/sim/process_supervisor.py`及`scripts/simulation/run_isaac_learning_study.py`：

- worker和每个阶段子进程独立进程组；不对未知／复用的历史PID操作。
- 启动前登记命令，运行后立即记录PID／PGID；每次原生进程结束立即原子保存退出码，再进入下一阶段或关闭worker。
- 保存阶段事件和父进程SIGTERM／SIGINT事件；第一次取消进行有界清理，第二次信号保持默认终止语义。
- 分别记录shutdown客户端退出码、worker原生退出码及整条流水线状态；不会用报告存在代替正常退出。
- 超时／失败停止后续阶段，保留已有结果和错误，不自动放宽示范配额或重跑覆盖旧目录。

相关39项测试通过；其中监督层3项实际覆盖子进程向自身进程组发SIGTERM不伤父进程、超时回收及正常退出即时落盘。轻量全套59项中17项执行通过、42项因可选资源跳过。

新的`isaac_staged_retrain_20261123`批次使用该监督层，并对调度器单独记录SIGTERM／SIGINT系统信号。长运行的实际收尾结果以该批次最终回执为准；该实现不保证能在SIGKILL、断电或磁盘故障下写完最后一条回执。

[排查汇总](/data/omi_runtime/runs/isaac_shutdown_audit_20261123/summary.json) · [原始两组回执](/data/omi_runtime/runs/isaac_shutdown_audit_20261123/receipts.json)

## 追加：25分钟执行会话对照

在`/data/omi_runtime/runs/exec_idle_audit_20261123`同时运行两条无GPU心跳：一条执行会话直到结束才轮询，另一条周期性轮询；均预设1500秒，并记录系统信号和独立文件心跳。两条都完成1500秒、退出0，未观察到SIGTERM。当前条件下，不支持“25分钟内单纯不轮询执行会话就会触发143”的假设；这不是所有负载／环境条件下的排除证明，也没有定位历史信号来源。

[长时对照汇总](/data/omi_runtime/runs/exec_idle_audit_20261123/summary.json) · [实际工具退出回执](/data/omi_runtime/runs/exec_idle_audit_20261123/receipts.json)。本轮完整重训也已正常收尾，因此已验证新的回执机制和当前长运行路径，但不将历史143改写为已解决的确定根因。
