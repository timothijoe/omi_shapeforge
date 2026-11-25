# 使用天机原厂IK

能力、模型范围与测试证据见[原厂IK适配](../docs/agent/simulation/evolution/tianji-native-ik.md)。当前支持CCS 1017左臂、固定基座及固定末端工具。无需连接真机。

在`omi_shapeforge`目录运行离线检查；输出目录必须是新的：

```bash
/data/omi_runtime/envs/omi_sim_train/bin/python scripts/simulation/audit_tianji_ik.py \
  --transfer /data/shapeforge/runtime/runs/staged_contact_20261123/robot_transfer \
  --tianji-sdk /home/linux/omi_folder/omi_proj/local/vendor/optical_module_pu/source/OpticalModule_PU/Arm_control \
  --output /data/shapeforge/runtime/runs/my_new_native_ik_audit
```

启动带真实RGB的Isaac worker，在原有参数后添加原厂IK选项：

```bash
/data/isaac-sim-5.1.0/python.sh scripts/simulation/isaac_rl_worker.py \
  --transfer /data/shapeforge/runtime/runs/staged_contact_20261123/robot_transfer \
  --output /data/shapeforge/runtime/runs/my_new_native_worker \
  --socket /tmp/my_new_native_worker.sock \
  --physics-substeps 20 --max-steps 900 \
  --teacher-min-step-mm .05 --target-overtravel-mm .1 --entry-guidance \
  --ik-backend tianji \
  --tianji-sdk /home/linux/omi_folder/omi_proj/local/vendor/optical_module_pu/source/OpticalModule_PU/Arm_control
```

等`WORKER_READY`后通过现有Isaac客户端连接。检查`worker_metadata.json`的`action_contract`及`execution_config.ik_backend`；它们必须标明原厂IK和实际库／配置哈希。沿用现有RPC shutdown及进程退出回执流程，不只关闭终端。

50段采集／BC／门控RL编排入口`run_isaac_diverse_study.py`接受相同的`--ik-backend tianji --tianji-sdk ...`，会给所有采集、验证、测试worker传递该选项。应使用新的输出目录和新合同；本次适配验证没有另起50段采集或重训。

后续[控制步优化](../docs/agent/simulation/evolution/isaac-step-profile.md)已默认关闭无界面worker中未使用的1280×720预览，保留两路真实传感器与双渲染子帧，并登记新的`execution_config.render_runtime`。复现优化前的合同／检查点时，在worker或批量入口增加`--keep-preview-viewport`，不要删改旧检查点中的合同来绕过检查。

要用原数值求解器，显式设置`--ik-backend dls`并去掉SDK参数。SDK目录缺失、模型不匹配或输出验收失败时原厂后端报错；修正原因后重试，不会静默降级。修改模型／SDK配置后重新运行离线与PhysX检查。

测试可在含numpy的环境设置`TIANJI_SDK_DIR`并执行`tests/test_tianji_ik.py`；不需要Isaac或机械臂。通用控制环境没有numpy时会显式跳过，不应把跳过当作SDK验证通过。

物理设备现在可通过`--physics-device gpu`选择，worker和`run_isaac_diverse_study.py`均支持；原厂IK与物理设备是两个独立选项。当前GPU物理仍经CPU回读，单环境对照更慢，默认保留CPU，见[验证与限制](../docs/agent/simulation/evolution/isaac-gpu-physics.md)。GPU运行使用新执行合同和新输出目录。

快速采集选项：在已有原厂IK的`run_isaac_diverse_study.py`命令后增加`--physics-substeps 5 --async-recording`，仍保留默认双渲染子帧；本机单环境完整周期约55 ms。可另外显式用`--render-subframes 1`试验新图像配方，约48 ms，但尚未验证学习策略。`--async-recording`属于采集／批量入口，不能传给worker；worker接受物理和渲染选项。使用新输出目录，检查回合报告中submitted、written、队列及结束等待统计；成功ready只在后台写入完成后发布。性能、完整性及5子步范围见[快速采集记录](../docs/agent/simulation/evolution/isaac-fast-collection.md)。
