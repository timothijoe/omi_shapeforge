# 独立 System1 与 System0 插接实验

本入口用于分别调试真值／噪声／视觉 System1 与直接动作 SAC System0。System0决定推进、暂停和倒退；System1提供接近入口、轴向插入的参考几何，不调用恢复老师。当前原型只接受固定模块夹持场景，不能用于真机执行。

## 环境与输入

学习环境为 `/data/shapeforge/runtime/envs/omi_sim_train/bin/python`，Isaac使用 `/data/isaac-sim-5.1.0/python.sh`。设置：

```bash
export PYTHONPATH=/home/linux/omi_folder/omi_proj/src:/home/linux/omi_folder/omi_shapeforge/src
```

从 `omi_shapeforge` 根执行 launcher。每次使用新的外部输出目录，不覆盖旧数据。下方场景、650步上限、5子步、原厂IK、插槽随机化配置必须在采集／训练／评估间一致。5子步属于已有快速仿真配方，不代表真实接触精度。

## 采集独立示范和 System1 标签

```bash
.venv/bin/python scripts/simulation/run_hierarchical_insertion.py \
  --output /data/shapeforge/runtime/runs/hier_NEW_collect \
  --transfer /data/shapeforge/runtime/runs/staged_contact_20261123/robot_transfer \
  --max-steps 650 --physics-substeps 5 --ik-backend tianji \
  --tianji-sdk /home/linux/omi_folder/omi_proj/local/vendor/optical_module_pu/source/OpticalModule_PU/Arm_control \
  --socket-range-mm .2 --socket-yaw-deg .1 \
  -- collect --episodes 3 --seed 121000
```

输出在 `experiment/`：每回合NPZ保存实际使用的reference/history、专家动作、双RGB和独立位姿标签；`dataset.json`保存哈希、成功标记和划分。最后一回合为验证，其余训练；三回合仅用于链路冒烟。失败回合保留，BC仅使用成功训练回合；视觉监督可使用有合法标签的失败回合。完整轨迹不跨划分。

规则老师只用于此显式 `collect` 命令。老师使用仿真真值，不是人工数据；它成功不能算System0成功。第一批以正常小扰动为主，恢复策略需要后续专门扩充受阻场景与示范。

## 单独训练 System0

复用上述launcher物理参数，把 `--output` 换成新目录，把 `--` 后的命令换为：

```bash
train-s0 --demos /data/shapeforge/runtime/runs/hier_NEW_collect/experiment \
  --bc-steps 1000 --steps 10000 --learning-starts 100 --seed 122000
```

此处BC1000步和SAC10000环境步是可调整实验预算，不是收敛承诺。System0是独立SB3 SAC，默认两层256维MLP；不加载旧OMI Actor。新路径／运动／腕力特征全部可训练。输出是原worker归一化世界系六维增量；原IK、物理与任务奖励仍执行。训练rollout无teacher接管。

`system0.zip`、`replay.pkl`、`system0.json`成套保存。使用 `train-s0 --model <旧目录>/system0.zip --bc-steps 0 --steps <新增步数>`在新目录续训；要求参考配置和物理合同一致，恢复replay与优化器。仅加载自己生成且信任的SB3/replay文件，不能加载来源未知的pickle。新观测不能直接混用旧经验池。

## 固定 System0 对比真值和噪声

使用同一个 `system0.zip` 和同一组留出种子，分别启动新输出目录：

```bash
evaluate --model /data/shapeforge/runtime/runs/hier_NEW_train/experiment/system0.zip \
  --episodes 10 --seed 123000 --system1 gt
```

```bash
evaluate --model /data/shapeforge/runtime/runs/hier_NEW_train/experiment/system0.zip \
  --episodes 10 --seed 123000 --system1 noisy \
  --bias-mm .2 --bias-deg .1 --noise-mm .05 --noise-deg .02 \
  --update-steps 5 --delay-steps 2
```

噪声作用于System1估计的插座世界位姿，再统一生成路径和目标；下层没有额外的干净孔位／目标输入。回合偏置每回合采一次，抖动每次上层更新采一次。`update-steps=5`即每0.5秒更新，`delay-steps=2`即延迟0.2秒交付；这是单进程内按仿真步建模的异步接口，不是已部署ROS并发节点。

延迟期间尚无参考时，reference有效位为0；策略可看到此状态，当前原型不自动覆盖其动作。训练应包含对应失效／延迟状态后再评估可靠性。奖励始终来自原任务真值，不随路径噪声变化。`evaluation.json`记录policy-only成功率、失败、倒退实际运动步数和teacher调用次数；训练／BC／视觉监督种子重叠会拒绝评估。

## 单独训练 System1 并组合

离线训练不需要启动Isaac：

```bash
/data/shapeforge/runtime/envs/omi_sim_train/bin/python \
  -m omi_hil_rl.training.hierarchical_insertion.cli train-s1 \
  --dataset /data/shapeforge/runtime/runs/hier_NEW_collect/experiment \
  --output /data/shapeforge/runtime/runs/hier_NEW_s1 \
  --epochs 20 --batch-size 32 --device cpu
```

第一版网络为小型双RGB CNN，预测当前TCP坐标系中的插座位姿（位置＋6D旋转表示），用几何解码器生成入口和插入路径。它是独立可训练基线，未替换现有ResNet-18感知网络。输入只有当时的两路图像；预测转换到世界系时使用该帧TCP，延迟交付时不再用新TCP重解释。训练按回合划分，归一化统计只用训练集，验证损失选择权重；报告提供平移、旋转误差和无效旋转数。

组合评估仍使用launcher的同一物理配置：

```bash
evaluate --model /data/shapeforge/runtime/runs/hier_NEW_train/experiment/system0.zip \
  --system1 learned --system1-model /data/shapeforge/runtime/runs/hier_NEW_s1/system1.pt \
  --episodes 10 --seed 123000
```

此模式不得查询GT插座来修正预测。System1资产哈希与System0物理／观测合同均检查。先固定System0比较三种System1，之后若联合适配，应另开训练版本并保留独立测试集。

## 腕部六维力输入

按用户后续要求，第一版不使用双指触觉。launcher显式开启worker的 `--wrist-wrench`；旧worker默认关闭，不改变旧策略观测。新System0默认 `--contact wrist-wrench`，也可显式 `--contact none` 做消融，但不同输入语义的模型需分别训练。

测量为固定夹持模块受到的外界接触冲量矢量及其力矩，按100 ms区间求均值，表示为 Fx/Fy/Fz（N）、Tx/Ty/Tz（Nm）。它是理想重力／惯性补偿后的外部接触合力近似，不是原来的接触冲量模长之和，也不是真实硬件传感器仿真。夹指内部接触排除；不含工具其他部位碰撞、重力／惯性、电子噪声与零漂。

虚拟传感器轴向跟随TCP；默认原点在TCP。若模拟具体腕部安装位置，launcher用 `--wrist-offset-m x y z` 指定传感器原点相对TCP的米制偏移。该变更进入执行合同，原点不同会改变力矩，不能直接混用。reset无新测量时valid为false，实际执行一个控制周期后valid为true；零接触可以是有效零值。

## 调试与恢复

`worker.log`、`experiment.log`保存原生输出；`*_process.json`记录实际退出码，`result.json`记录编排结果。`trace.jsonl`逐步记录动作、上层版本／年龄、奖励、深度、腕力和终止；NPZ或SB3经验池保存网络实际输入。`hierarchical_sources/`和worker自己的源码快照保留运行时版本。

源码、分支与检查结果见[能力记录](../docs/agent/simulation/evolution/hierarchical-insertion.md)。没有成功训练的模型不能因为工具链运行完毕而被标为已学会插孔。
