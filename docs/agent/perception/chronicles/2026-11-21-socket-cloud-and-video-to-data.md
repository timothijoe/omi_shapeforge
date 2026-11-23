# 2026-11-21：插座点云粗配准与 Video to Data 评估

用户要求把插座也匹配到同一 HTML 点云，并说明光模块绿色部分只是挂件、不需要配准。本次按绿色拉环／拉臂理解：它们在此前 V3 的 9 部件主体拟合中已经排除，本次也不参与任何求解，并从默认显示中隐藏，可单独勾选查看。模块保持用户纠正正反面后的位姿，不重新移动以迁就插座。

## 插座条件粗配准

输入仍为 SHA256 `efdf00062690651d2123d57f4eac48abc0bfca2c2a49ef5de29fc53d2201ee85` 的 100000 点 SGBM 场景。插座采用 OS-001 r04，源 Blender 哈希 `44e24fbe1ef3b352c61adcea6e84a9044de13275d1f62856e8a502ed275e0f48`，网格从既有评估导出加载，mm 转 m，不缩放或变形。

在复现的斜视图中手动圈选插座区域，像素多边形为 `[[320,232],[450,235],[469,335],[332,354]]`，视图中心 `[.015,-.025,.65] m`、yaw `-.3`、pitch `-.5`、距离 `.45 m`、1000×1000、投影因子 1.5。这不是采集相机像素。深度范围 `.71–.815 m`，得到 3039 原始选区点。依据主要观测平面及框架／PCB 分层保留平面带 `[-24,+4] mm` 的 2249 点；该过滤属于条件先验，不是自动发现。

1799 点用于稳健点到面 ICP 和候选评分，450 点仅用于最终残差检查。24 个轴向姿态×3 个平移初值，共 72 个初始化；初始化轴参考光模块方向，但完整尝试轴排列与符号，且没有插合约束。上部 134 个部件参与几何，1 个下部打印支架不参与。评分含点到网格距离和考虑遮挡的表面支持率。ROI、平面和初始化仍依赖整体观测，检查集不是独立位姿真值。

默认候选结果：

| 点集 | 数量 | 距离中位数 mm | P90 mm |
| --- | ---: | ---: | ---: |
| 拟合点 | 1799 | 0.725 | 3.913 |
| 检查点 | 450 | 0.754 | 4.313 |
| 全部原始选区 | 3039 | 1.256 | 11.328 |

这是**粗配准候选**。双孔形状重复、背景／侧面离群点及部分不可见结构影响结果。拟合分数接近的其他候选保留在页面下拉框，不能把低表面距离当作朝向唯一或物理精度已验证。

重要相对关系：默认插座解下，模块前端轴线参考点在插座坐标约 `[-32.03,6.56,3.29] mm`，与模型金属通道 `x=-0.5 mm` 的横向参考差约 `-31.53 mm`，更接近框架另一侧开口。该值依赖当前粗解和名义轴线探针，不是实物测量或碰撞结论。未把模块强行移到金属通道，也未改插座内部位置；**实际开口对应关系仍须复核**。

产物目录 `/data/omi_runtime/runs/socket_module_cloud_20261121/`：

- `overlay.html`：蓝色插座、橙色模块；绿色挂件和未验证下部支架为独立开关，默认关闭。全部 10 万点保留。
- `report.json`：两个绝对变换、相对变换、输入来源、ROI 和过滤策略、残差及限制。
- `socket_candidates_refined.json`：72 初值和去重候选。
- `matched_socket_upper.ply`、`matched_socket_full.ply`：当前变换后的网格。
- `preview.png`、`closeup.png`：实际可见浏览器截图。

源码为 `scripts/perception/fit_socket_pointcloud.py`、`render_socket_cloud.py`、`socket_cloud_viewer.html`。在独立软件渲染 Chrome 中验证加载、模型/插座/挂件/支架/拟合点开关、候选切换及局部查看，WebGL 错误码 0。没有连接硬件、修改模型尺寸或运行 RL。

## NVIDIA Video to Data 只读评估

用户在配准过程中给出 `https://github.com/nvidia-isaac/video_to_data`，询问能否改善鱼眼腕部位姿。已查阅官方 README 和代码，固定检查提交 `1e862a8984bf28474c324c1b49db99b2da7ece80`，少量源码快照保存在 `/data/omi_runtime/reviews/video_to_data_20261121/`。没有安装其依赖、下载权重或运行推理。

- [重建模块说明](https://github.com/nvidia-isaac/video_to_data/blob/1e862a8984bf28474c324c1b49db99b2da7ece80/reconstruction/README.md)：提供 SAM2 分割、FoundationStereo、FoundationPose、单目深度等可组合模块。对我们的目标，最有用的是主体分割、已知 mesh 位姿跟踪和重投影检查，不必启动整个人体动作／机器人重定向训练流程。
- [单视频位姿入口](https://github.com/nvidia-isaac/video_to_data/blob/1e862a8984bf28474c324c1b49db99b2da7ece80/reconstruction/modules/v2d_foundation_pose/lib/run_video_to_poses.py)：加载视频、逐帧深度、掩码、mesh 和针孔 K；初始化帧缺少 RGB/depth/mask 会报错。并非直接接收原始鱼眼 RGB 就能完成的接口。
- [相机数据类型](https://github.com/nvidia-isaac/video_to_data/blob/1e862a8984bf28474c324c1b49db99b2da7ece80/reconstruction/modules/v2d_common/datatypes.py)：独立 CameraDistortion 类型可记录 `opencv_fisheye`，但上述位姿入口只传递针孔 CameraIntrinsics。存在畸变类型不等于该入口自动处理鱼眼。
- 检查的多目 `image_proc/proc_cv2.py` 使用普通 `cv2.stereoRectify/initUndistortRectifyMap`；不能把我们四个鱼眼系数直接作为普通 Brown-Conrady 四系数使用。应显式用鱼眼标定生成针孔视图和新 K，再在该视图估计，最后转换回原鱼眼投影检查。

判断：相较当前四个几何代理角点的启发式原型，学习式主体分割和时序跟踪**有改善潜力，尚未实测**。主要依赖可靠深度、正确的鱼眼预处理、足够像素及遮挡判断。现有腕部 RGB 单视频不能直接用 FoundationStereo 产生双目深度；头部深度也不能未经外参、时间同步和可见性处理就当作腕部深度。单目估计深度可以试验，但不能默认满足插接所需毫米精度。

建议最小对比：原分辨率腕部帧→按已知 K/D 做局部针孔重映射→SAM2 主体掩码（排除绿色挂件）→使用可靠深度的 FoundationPose，或头部点云初始化后的 RGB 跟踪→把 V3 投回原鱼眼图。固定现有 mesh 尺寸，不采用无依据自动缩放；用跨 episode 不同俯仰／遮挡图像和人工核对对应关系评估，不能只看拟合残差或平滑程度。128×128 的已有 episode ROI 不能凭算法恢复原始丢失细节。
