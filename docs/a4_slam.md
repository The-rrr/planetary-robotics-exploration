# A4：在 TUM RGB-D 数据上运行完整 RTAB-Map SLAM

## 主结果

最终主运行编号：`A4-20260930-desk-full-03`。

| 项目 | 结果 |
|---|---:|
| 输入序列 | `freiburg1_desk` |
| A2 配对输入 | 573 对 |
| 成功发布 / RGB-D 里程计输出 | 573 / 573 |
| RTAB-Map 数据库节点 | 548 |
| 唯一全局回环约束 | 124 |
| 长距离全局回环约束（节点编号差至少 30） | 19 |
| 导出地图点数 | 1,031,428 |
| 纯里程计 APE RMSE | 0.097661 m |
| 回环优化后 APE RMSE | 0.025180 m |

APE 使用 SE(3) Umeyama 对齐。真值只由估计结束后的 `evo_ape` 读取，不发布到 ROS，也不提供给里程计或 RTAB-Map。

主产物位于 `results/a4/A4-20260930-desk-full-03/`：

| 文件 | 含义 |
|---|---|
| `odometry_estimate.tum` | RGB-D 前端逐时刻估计轨迹，TUM 时间戳格式 |
| `slam_poses.txt` | RTAB-Map 后端优化轨迹，TUM 时间戳格式 |
| `slam_cloud.ply` | 1 cm 体素滤波的彩色三维地图 |
| `rtabmap.db` | 完整 RTAB-Map 数据库 |
| `a4_rtabmap.yaml` | 本次运行的配置快照 |
| `manifest.json` | 唯一运行编号、版本、命令、输入和职责说明 |
| `node_subscriptions.txt` | 两个估计节点的实际订阅清单 |
| `loop_closures.json` | 运行时事件和数据库图约束的回环审计 |
| `odometry.log`、`slam.log`、`replay.log`、`export.log` | 完整运行与导出日志 |

## 固定环境与官方示例

运行环境固定为 ROS 2 Jazzy、RTAB-Map 0.23.7：

```text
ros-jazzy-rtabmap       0.23.7-1noble.20260903.070800
ros-jazzy-rtabmap-odom  0.23.7-1noble.20260903.102901
ros-jazzy-rtabmap-slam  0.23.7-1noble.20260903.103010
```

节点连接以该安装版本的官方 `rtabmap_examples/launch/rgbdslam_datasets.launch.py` 为基线：`rgbd_odometry` 接收 RGB、深度、相机内参，输出 `/odom`、`/odom_info` 和 `/odom_rgbd_image`；`rtabmap` 使用后两项做回环检测和位姿图优化。项目有意删除官方示例中的 ground-truth frame 参数，固定为空字符串。

TUM 原始 PNG 深度是 `5000 units/m`。回放节点先转换为以米表示的 ROS `32FC1`，与 TUM 官方 ROS bag 的深度语义一致；直接把 PNG 原值发布为 `16UC1` 会被 ROS 消费端按毫米解释，导致尺度放大 5 倍。相机内参沿用 A2/A3 已确认的 ROS 默认值 `525, 525, 319.5, 239.5`。依据：

- TUM RGB-D 文件格式：https://cvg.cit.tum.de/data/datasets/rgbd-dataset/file_formats
- RTAB-Map ROS 2 官方启动文件：https://github.com/introlab/rtabmap_ros/blob/ros2/rtabmap_launch/launch/rtabmap.launch.py

## 前端和后端职责

- `rgbd_odometry` 负责相邻时刻的视觉运动估计并发布 `odom -> camera_rgb_optical_frame`。
- `rtabmap` 接收前端结果，负责外观重访检索、几何验证、回环约束和全局位姿图优化。
- `Rtabmap/DetectionRate=0` 用于离线完整处理，不按默认 1 Hz 跳过关键帧；其余核心配置保持官方数据集示例附近。

## 回环证据

主运行的 `/info` 消息报告 124 次 `loop_closure_id > 0`。数据库 `Link` 表有 248 条 `type=1` 记录；RTAB-Map 对同一约束保存双向记录，因此折算为 124 个唯一 `kGlobalClosure`。其中包括 `44 <-> 450`、`45 <-> 449` 和 `47 <-> 437` 等跨越很长时间段的约束。完整样例与计数见 `loop_closures.json`。

`A4-20260930-xyz-smoke-02` 是默认 1 Hz 后端检测率的短测试，只有相邻约束，审计结果明确为 `loop_closure_demonstrated=false`；它只证明里程计和导出链路可运行，不作为回环证据。

## 真值隔离

回放节点只读取 A2 的关联 CSV、RGB PNG、深度 PNG 和相机配置。它只发布三个 topic：

```text
/camera/rgb/image_color
/camera/depth/image
/camera/rgb/camera_info
```

`node_subscriptions.txt` 显示估计节点没有订阅 `/world`、`kinect_gt` 或任何真值 topic；配置中的两个 `ground_truth_*` 参数也为空。只有在所有 ROS 估计进程退出、数据库关闭后，才运行：

```bash
evo_ape tum data/rgbd_dataset_freiburg1_desk/groundtruth.txt \
  results/a4/A4-20260930-desk-full-03/odometry_estimate.tum -a

evo_ape tum data/rgbd_dataset_freiburg1_desk/groundtruth.txt \
  results/a4/A4-20260930-desk-full-03/slam_poses.txt -a
```

## 复现

在 Windows 项目根目录双击 `Run-A4.cmd`。它会先运行 90 帧 `freiburg1_xyz` 检查，再运行完整 `freiburg1_desk`；每次自动生成新的 UTC 时间运行编号，既不覆盖旧结果，也不复用旧数据库。

在 WSL 中也可单独运行：

```bash
cd <PROJECT_ROOT>
source scripts/ros_env.sh
/usr/bin/python3 scripts/run_a4.py --sequence xyz --label smoke
/usr/bin/python3 scripts/run_a4.py --sequence desk --label full
```

运行器会复制配置快照、保存节点订阅、正常关闭数据库，然后执行 `rtabmap-export` 导出轨迹和地图。完整运行不允许设置 `--max-frames`，以免把截断实验误标为完整序列。

## 修正记录

`A4-20260930-desk-full-01` 使用官方示例附近的 1 Hz 后端检测率，未形成回环，保留为阴性证据。`A4-20260930-desk-full-02` 虽形成图约束，但深度仍错误地按 `16UC1` 发布，尺度大约放大 5 倍，不能作为最终地图。`A4-20260930-desk-full-03` 修正为 `32FC1` 米值，是最终主结果。
