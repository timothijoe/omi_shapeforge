# Isaac Sim 同源插接实验

> 本机迁移提示（2026-11-24）：运行资源实体已迁至 `/data/shapeforge/runtime`；本文中的 `/data/omi_runtime` 是保留的兼容入口，指向同一份内容。目录映射与恢复要求见[当前资源契约](../docs/agent/interfaces/local-resources.md)。

新增[接触力与图像改进结果](../docs/agent/simulation/evolution/isaac-contact-visual-review.md)。下面的gentle/refined均为独立候选，旧baseline仍可复现。

## 新候选：临近台阶减速与清晰图像

```bash
cd /home/linux/omi_folder/omi_shapeforge
timeout --signal=TERM --kill-after=10s 1200s \
  env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH \
  /data/isaac-sim-5.1.0/python.sh -u scripts/simulation/run_isaac_contact.py \
  --transfer /data/omi_runtime/runs/isaac_contact_development_20261122/robot_transfer \
  --output /data/omi_runtime/runs/isaac_gentle_refined_NEW \
  --seed 7 --contact-recipe gentle --force-limit 10 \
  --image-recipe refined --sensor-resolution 512 --render
```

gentle保持任务成功阈值，改变临近台阶的轴向限速和控制目标余量，并默认启用10 N控制采样停止门控。`--dt .0001`用于半步长检查。控制采样门控不限制所有物理子步峰值，也不是硬件安全力认证。

refined读取既有V4-r07 GLB/纯色纹理，区分材质并调整灯光，不改碰撞体。两相机实际渲染512×512，策略输入明确下采样到128×128；全景1280×960，视频1792×1024。使用原生768×768静态对照可运行`review_isaac_images.py`；该脚本冻结姿态，不能替代动态试验。原始法线直映、漏纹理颜色和启动失败候选均保留，详见能力页。

优先串行启动RTX作业。两次并行物理试验虽保存完整成功任务报告，工具会话收尾返回143；不能只读取`accepted`就宣称进程执行全通过。

本入口针对SIM-r06接触实验，不是旧的单模块落台脚本。设计见[实验方案](../docs/design/isaac-contact-experiment.md)，已执行结果及限制见[能力记录](../docs/agent/simulation/evolution/isaac-contact.md)。

## 环境和资产

- Isaac Sim：`/data/isaac-sim-5.1.0/python.sh`。
- 独立补充依赖：`/data/omi_runtime/envs/isaac_contact_support`；启动器先加入该目录，不改Isaac安装或系统驱动。
- MuJoCo求值导出：`/data/omi_runtime/envs/omi_sim_train/bin/python`。
- 本次冻结传递包：`/data/omi_runtime/runs/isaac_contact_development_20261122/{local_transfer,robot_transfer}`。
- 所有输出目录必须不存在。下列`NEW`须换为新名称。

如在另一环境重新准备补充依赖，使用独立新目录和[依赖版本](../configs/isaac_contact_support_requirements.txt)，随后通过`--support`指定它。不要向已有Isaac安装目录执行覆盖安装。该目录不含Isaac或GPU框架，后者仍使用供应商运行时。

```bash
env -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH \
  /data/isaac-sim-5.1.0/python.sh -m pip install --no-deps \
  --target /data/omi_runtime/envs/isaac_contact_support_NEW \
  -r configs/isaac_contact_support_requirements.txt
```

## 从原场景冻结输入

```bash
cd /home/linux/omi_folder/omi_shapeforge
/data/omi_runtime/envs/omi_sim_train/bin/python scripts/simulation/export_isaac_contact.py \
  --source /data/omi_runtime/runs/measured_v4_sim_20261121/robot_scene/scene.xml \
  --manifest /data/omi_runtime/runs/measured_v4_sim_20261121/robot_scene/robot_manifest.json \
  --output /data/omi_runtime/runs/isaac_transfer_NEW/robot_transfer

/data/omi_runtime/envs/omi_sim_train/bin/python scripts/simulation/export_isaac_contact.py \
  --source /data/omi_runtime/assets/sim_insertion/r06/scene.xml \
  --manifest /data/omi_runtime/assets/sim_insertion/r06/asset_manifest.json \
  --output /data/omi_runtime/runs/isaac_transfer_NEW/local_transfer
```

`transfer.json`记录关节、质量惯量、相机、源文件哈希和原实验清单；`meshes.npz`记录已求值顶点。它是当前场景专用传递合同，不是通用MJCF导入器。Isaac运行不调用MuJoCo推进物理。

## 运行局部测试和机器人

```bash
timeout --signal=TERM --kill-after=10s 900s \
  env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH \
  /data/isaac-sim-5.1.0/python.sh -u scripts/simulation/run_isaac_contact.py \
  --transfer /data/omi_runtime/runs/isaac_contact_development_20261122/robot_transfer \
  --output /data/omi_runtime/runs/isaac_robot_NEW --seed 7 --render
```

省略`--render`使用仅PhysX/张量扩展的CPU路径；加上时实际使用RTX渲染，保存双相机截图和三视图`cycle.mp4`。两路策略图像为128×128；全景和文字叠加只供展示。渲染使用零时间增量，并检查取图不改变关节状态。

将`--transfer`改为`local_transfer`运行局部插入退出。参数：`--dt .0001`半步长；`--locked`锁死触点；`--lateral-mm 1/-1`横偏；`--yaw-deg 2/-2`偏航。默认接触偏移每形状0.1 µm、rest offset为0；这是当前微间隙场景的数值设置，不是实物精度声明。

最终默认使用PGS。`--solver TGS`只用于保留的求解器对照；TGS曾在seed19小动作对准时停滞，不应将其失败覆盖或与PGS成绩混合统计。

机械臂的`accepted`对应源规则循环判据，不含后续学习评估的10 N停止规则。本次seed7控制采样峰值约21.3 N，需继续处理接触力后再接BC/RL；完整统计见能力页，不能把视频成功当作该力门控通过。

运行整组独立进程检查：

```bash
.venv/bin/python scripts/simulation/run_isaac_contact_suite.py \
  --transfer-root /data/omi_runtime/runs/isaac_contact_development_20261122 \
  --output /data/omi_runtime/runs/isaac_suite_NEW \
  --cases normal half_step locked x_plus x_minus yaw_plus yaw_minus

.venv/bin/python scripts/simulation/run_isaac_contact_suite.py \
  --transfer-root /data/omi_runtime/runs/isaac_contact_development_20261122 \
  --output /data/omi_runtime/runs/isaac_robot_suite_NEW \
  --cases robot_7 robot_19 robot_41 --timeout 900
```

监督器为每项保存命令、退出码、超时、报告和验收状态；即使底层退出0，也必须有`report.json`且`accepted=true`才计通过。中断/超时保留`trajectory.jsonl`，不应继续写进旧目录。

## 输出和排查

每次运行保存`execution.json`、实际执行模块的`code_snapshot/`、`scene.usda`、`scene_manifest.json`、接触轨迹和最终报告。机器人另有`kinematics_check.json`和初始姿态USD。`scene.usda`是零关节参考装配；查看初始任务姿态使用`initial_pose.usda`，运行仍按入口初始化。

本次另外提供[查看用USD场景](/data/omi_runtime/runs/isaac_contact_development_20261122/review_assets/ISAAC-SIM-r06-PGS-initial.usdc)：可在Isaac Sim中通过File→Open打开，包含初始任务姿态和18个初始化驱动目标。[重开检查](/data/omi_runtime/runs/isaac_contact_development_20261122/review_assets/validation.json)核对501个碰撞体与原文件未变；这是资产重开检查，不是另一次GUI交互或动力学验收。

`--audit-all-colliders`核对491个凸网格的实际PhysX烘焙结果，记录向外和向内的支持平面偏差。当前内部用顶点×1000、prim缩放×0.001改善小网格烘焙，世界几何不变；禁止去掉反向缩放。曲面件仍可能被引擎简化，详见能力页。

PhysX可能报告某些凸包不兼容GPU并回退CPU；当前任务明确运行CPU刚体，不据此宣称GPU物理、粒子或柔性体已经验证。首次RTX启动可能编译资源；优先串行启动RTX作业，避免多个Kit实例的缓存/初始化争用。

测试：`.venv/bin/python -m unittest discover -s tests -v`运行控制层；`PYTHONPATH=src /data/omi_runtime/envs/omi_sim_train/bin/python -m unittest discover -s tests -p test_isaac_contact_transfer.py -v`运行独立FK对照。可选依赖缺失而跳过的检查不计为已通过。
