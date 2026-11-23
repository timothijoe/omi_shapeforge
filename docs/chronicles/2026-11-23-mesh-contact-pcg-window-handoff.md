# 2026-11-23：本窗口交接——外观资产、双胶垫接触与PCG-01纯几何包

本窗口当前工作已完成：用户查看并认可改善后的外观与夹持展示，随后要求无颜色的点云匹配几何、可视化、可复制交付及完整文档归档。**最近交付物是PCG-01便携包，直接复制`/home/linux/Downloads/PCG-01.zip`即可。**

本交接限定为本窗口的mesh／视觉／夹持／纯几何导出工作。其他窗口的点云监督训练、细网格采样和Isaac BC／RL仍在独立推进，其当前状态见[全局交接](../../HANDOFF.md)和[当前总览](../current.md)，不能把本窗口“未新增训练”理解为整个项目没有训练。

## 接手先读什么

1. [PCG-01纪传体：当前便携包及读取合同](../agent/perception/evolution/pointcloud-geometry-pcg01.md)；[编年体](../agent/perception/chronicles/2026-11-23-pointcloud-geometry.md)。
2. 如需实际夹持，读[GC-r01双胶垫接触纪传体](../agent/simulation/evolution/wrist-contact-closure.md)；[编年体](../agent/simulation/chronicles/2026-11-22-wrist-contact-closure.md)。
3. 如需原带材质视觉组合，读[WVA-01版本说明](../agent/simulation/evolution/wrist-visual-wva01.md)；[版本形成编年](../agent/simulation/chronicles/2026-11-22-wva01-assets.md)。
4. 如需各历史mesh版本及物理尺寸，读[模块／插口尺寸速查](../agent/simulation/evolution/module-socket-dimensions.md)。用户最近问的“大小”已明确指存储／内存，回答时不要再混成毫米尺寸。

## 版本身份，不能混用

| 身份 | 内容与当前定位 | 固定登记 |
| --- | --- | --- |
| WG-r14 | 根据原始照片收窄银壳前端、缩短根部平段；保留前端与黑胶垫齐平 | [r14](../../manifests/wrist_tip_photo_review_20261122.json) |
| WG-r15 | 两侧银壳增加红色DAIMON图标与黑字，阅读方向相反；全部49件几何与r14一致 | [r15](../../manifests/wrist_logo_20261122.json) |
| WVA-01「腕部实拍对齐版」 | 用户接受的视觉组合：WG-r15＋OM-r08＋SIM-r06插槽参考场景／候选鱼眼／实拍对比 | [WVA-01](../../manifests/wrist_visual_wva01_20261122.json) |
| GC-r01「黑胶垫双面接触修订候选」 | 基于同一视觉资产，增加可闭合双指、自由模块及真实接触保持／释放 | [GC-r01](../../manifests/wrist_contact_closure_20261122.json) |
| PCG-01「点云匹配纯几何版」 | 模块主体＋插口上部，无颜色／纹理，独立可复制的PLY／NPZ | [PCG-01](../../manifests/pointcloud_geometry_pcg01_20261123.json) |

WVA表示Wrist Visual Assets。01是第一次为完整视觉组合建立的命名版本，不是把夹爪的r15或光模块的r08归零。GC是独立接触场景，PCG是几何导出包；都不是光模块的新外形版本。

## 本窗口关键决定与过程

- 用户的红线仅表达形状，最终以原始实拍为依据。r14使用`20261122-000200.jpg`及`20261122-113448.jpg`复核比例；银壳前端短边6.3→3.8mm、根部平段11.3→7.5mm，均为模型估计。r13及旧版保留。
- 用户要求加DAIMON标志，形成r15。只增加表面UV／材质，不加凸起或金属颗粒。两侧朝向按照实拍设置；图形为照片描摹，不是厂家矢量原稿。
- 使用真实unit_001腕部原图与r15＋OM-r08鱼眼渲染做同像素区域对比。没有调色、单独拉伸或真实手部像素覆盖。用户接受后命名WVA-01；原有颜色、反光、拉环和插槽位置差异如实保留。
- 用户指出模块必须与两块黑胶垫接触：原WVA-01左右间隙约0.046／0.602mm，工具碰撞关闭，“没有穿模”不是“夹住”。新增GC-r01，保留旧视觉组合。
- 用户查看GC-r01交互窗口后反馈“感觉好很多”。该反馈不等于真机或插入验收。
- 用户询问mesh大小并澄清指内存空间。核对磁盘文件与几何数组后，按要求提取PCG-01，不带颜色，默认去掉大支架并明确说明范围。
- 用户确认看到PCG-01三维可视化，要求复制走。交付便携文件夹与ZIP，查看器改为包内相对路径；之后要求补齐纪传体、编年体及本窗口交接。

## PCG-01：最近交付及可直接复制的内容

- [文件夹](/home/linux/Downloads/PCG-01)
- [ZIP](/home/linux/Downloads/PCG-01.zip)
- [包内README](/home/linux/Downloads/PCG-01/README.md)
- [灰色预览](/home/linux/Downloads/PCG-01/preview.png)

ZIP共914,836字节，SHA256：

```text
6215ae794b4b29d31e0a3640c9af6048ffba496632f057debb40cbea834c0d7f
```

包内11个文件：两个PLY、两个NPZ、预览图、资产清单、验证报告、查看脚本、依赖版本、README和SHA256清单。总文件夹大小1,335,147字节，包含预览及两种格式的重复几何。

| 对象 | 范围 | 顶点／三角面 | PLY字节数 | float32顶点＋int32索引字节数 |
| --- | --- | --- | ---: | ---: |
| 模块 | V4-r08的15件主体；去绿色U形拉环、假设内部阴影块，保留尾部胶塞 | 2019／3954 | 75,876 | 71,676 |
| 插口 | SIM-r06的112件固定上部；保留框架、金属槽、PCB、小支柱，去下方大支架 | 12992／25628 | 489,316 | 463,440 |

两份PLY合计565,192字节；两份NPZ压缩后合计178,636字节；加载为顶点／索引数组合计535,116字节，约0.535MB。不能据此宣称整个配准进程或显存仅占0.535MB，还要计算法向、采样点、KD-tree及运行环境。

两种文件保留原物体坐标、原点和米制尺度，未减面／平滑／居中／变轴。PLY为二进制小端，仅XYZ和三角面索引；NPZ仅`vertices_m`与`faces`，不含RGB、UV、法向、材质或纹理。需要法向时从几何计算。两文件是分别定义的对象模型，直接叠放不是装配或配准结果。

源纯几何目录：`/data/omi_runtime/assets/pointcloud_matching/PCG-01/`。制作、检查、渲染和打包脚本：`/data/omi_runtime/runs/pointcloud_geometry_20261123/`。便携包无需这些绝对路径即可加载；来源哈希只用于追溯。

## GC-r01：接触修订与限制

资产目录：`/data/omi_runtime/assets/daimon/wrist_grasp_contact_r01/`；实验目录：`/data/omi_runtime/runs/wrist_contact_closure_20261122/`。

模块为6自由度刚体，不焊接在夹爪上；双指靠限力位置伺服闭合，实际黑胶垫凸网格与模块分解碰撞体接触。只有工具基座跟踪mocap目标使用weld，模块没有位置硬写或weld。每次从物理状态读取相对变换；原`tool_to_module`只是参考初始放置，不是通用夹持约束。

5种名义／偏移／倾角初态通过重力保持、22.36mm移动和释放，最大相对滑移约0.00464mm；半步长复验通过。实际可见表面只有两侧黑胶垫接触模块，数值压入约1～3微米；稳定法向力每侧约2.35N。另验证名义重放每0.2ms接触门控，释放后`held=false`。

20g质量、摩擦系数1和接触参数未实物标定，胶垫为刚性凸体；这里只验证小范围夹持。该单测关闭插槽碰撞，不能声称接触插槽后仍稳定或自主插入成功。软接触滑移和直接mocap移动失败保留在`attempt01_soft_slip`、`attempt02_mocap_velocity`。

加载`contact_scene.xml`必须恢复`gravity_hold`关键帧，才是已夹紧状态；默认XML是闭合前放置。`scripts/grasp_status.py`提供实际双侧接触和法向力门控。

## WVA-01与历史资产保护

WVA-01快照：`/data/omi_runtime/releases/wrist/WVA-01/`。快照记录677个静态场景外部依赖，不是自包含资产包；与PCG-01便携ZIP的交付方式不同。

WG-r15工具在`/data/omi_runtime/assets/daimon/wrist_gripper_logo_r15/`，OM-r08在`/data/omi_runtime/assets/optical_module_v4/r08/`。当前插口来源SIM-r06，独立展示资产在`/data/omi_runtime/assets/optical_socket/measured/r01/`。原r05「双窗尾槽版」、V3、其他历史mesh和旧WG-r10固定清单均保留。

候选腕部内参来自`/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json`，与新采集硬件／模式绑定尚未认证。unit_001是已有参考拟合帧，不是独立留出集。物理尺寸、标定和旧像素／训练成绩不能随版本名称自动转移。

## 窗口恢复与环境

交接核查时，未发现标题匹配PCG-01／GC-r01／MuJoCo的可见窗口；此前已实际打开且用户已看到。窗口是否仍开着不影响文件交付，下列命令可恢复，不要关闭其他工作窗口。

PCG-01便携查看：

```bash
/data/omi_runtime/envs/foundation_stereo/bin/python /home/linux/Downloads/PCG-01/view_geometry.py
```

Python3.11.15、NumPy1.26.4、Open3D0.19.0已验证。鼠标旋转／滚轮缩放；M网格、P临时采样点云、1仅模块、2仅插口、3两者。P模式不是传感器实测数据，不写回文件；并排显示的平移只作用于内存副本。

GC-r01接触查看：

```bash
MUJOCO_GL=glfw /data/omi_runtime/envs/omi_mesh_audit/bin/python /data/omi_runtime/assets/daimon/wrist_grasp_contact_r01/scripts/view_contact.py
```

默认双侧夹紧暂停；空格／R重放闭合→重力保持→平移→张开释放；1自由视角、2腕部针孔检查视角。最终鱼眼图由cubemap与K／D生成，不能把针孔检查图当作最终观测。

Blender运行路径：`/data/omi_runtime/tools/blender-4.5.16-linux-x64/blender`；mesh审计环境使用MuJoCo3.15。绘图和生成脚本可能写死输出目录，复做实验应先复制到新的运行目录并修改输出，勿重跑覆盖已发布结果。

## 文档、验证与下一步

PCG-01的[最终归档验证](/data/omi_runtime/runs/pointcloud_geometry_20261123/docs_archive_verification.json)确认便携目录／ZIP哈希不变、ZIP完整性和文档链接通过；[几何验证](/data/omi_runtime/assets/pointcloud_matching/PCG-01/validation.json)确认选中顶点与三角面保持一致，float32舍入差低于0.000004mm。GC-r01的[最终入口验证](/data/omi_runtime/runs/wrist_contact_closure_20261122/final_verification.json)确认闭合关键帧、连续接触门控和释放结果。

本窗口已授权的当前工作没有待完成步骤，也没有等待用户审批的动作。后续按新的用户指令接续：

- 要复制几何：直接交付现有ZIP，不需要重建或重训。
- 要接入点云匹配：先核对对象坐标与部件范围；PCG-01不含大支架，不能不检查就替换旧完整模板。
- 要更改几何／范围：另建版本并重新记录来源、大小及验证，保留PCG-01。
- 要接触插入：在独立场景启用并验证插槽接触，GC-r01现有5例不是插入验收。

工作区为`/home/linux/omi_folder/omi_shapeforge`，交接时分支`feature/isaac-contact-insertion`，存在大量其他窗口的未提交修改。本窗口没有提交／推送；不要reset、clean或覆盖并行感知／训练工作，也不要依据旧文档覆盖全局当前优先级。先读`AGENTS.md`、`docs/current.md`及相关领域最新记录。
