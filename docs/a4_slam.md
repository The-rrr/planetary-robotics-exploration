# A4: Running a Complete RTAB-Map SLAM Pipeline on TUM RGB-D Data

## Main result

Final recorded run: `A4-20260930-desk-full-03`.

| Item | Result |
|---|---:|
| Input sequence | `freiburg1_desk` |
| A2 matched inputs | 573 pairs |
| Successfully published / RGB-D odometry outputs | 573 / 573 |
| RTAB-Map database nodes | 548 |
| Unique global loop-closure constraints | 124 |
| Long-range global loop closures (node-ID separation of at least 30) | 19 |
| Exported map points | 1,031,428 |
| Odometry-only APE RMSE | 0.097661 m |
| Loop-optimised APE RMSE | 0.025180 m |

APE was calculated after SE(3) Umeyama alignment. Ground truth was read only by `evo_ape` after estimation had finished. It was not published to ROS or supplied to either the odometry node or RTAB-Map.

The main outputs are stored in `results/a4/A4-20260930-desk-full-03/`:

| File | Meaning |
|---|---|
| `odometry_estimate.tum` | Per-timestamp RGB-D front-end trajectory in TUM format |
| `slam_poses.txt` | RTAB-Map back-end optimised trajectory in TUM format |
| `slam_cloud.ply` | Coloured 3D map filtered with 1 cm voxels |
| `rtabmap.db` | Complete RTAB-Map database |
| `a4_rtabmap.yaml` | Configuration snapshot for this run |
| `manifest.json` | Unique run ID, versions, commands, inputs and responsibility notes |
| `node_subscriptions.txt` | Actual subscription lists for both estimation nodes |
| `loop_closures.json` | Loop-closure audit from runtime events and database graph constraints |
| `odometry.log`, `slam.log`, `replay.log`, `export.log` | Complete run and export logs |

## Fixed environment and official example

The recorded environment used ROS 2 Jazzy and RTAB-Map 0.23.7:

```text
ros-jazzy-rtabmap       0.23.7-1noble.20260903.070800
ros-jazzy-rtabmap-odom  0.23.7-1noble.20260903.102901
ros-jazzy-rtabmap-slam  0.23.7-1noble.20260903.103010
```

The node connections follow the installed version's official `rtabmap_examples/launch/rgbdslam_datasets.launch.py` example. `rgbd_odometry` receives colour, depth and camera information, then publishes `/odom`, `/odom_info` and `/odom_rgbd_image`. `rtabmap` uses the latter two streams for loop detection and pose-graph optimisation. The ground-truth frame parameters from the official example were deliberately set to empty strings.

The original TUM PNG depth images use `5000 units/m`. The replay node converts these values into ROS `32FC1` depth measured in metres, matching the semantics of the official TUM ROS bags. Publishing the raw PNG integers directly as `16UC1` would cause ROS consumers to interpret them as millimetres, making the reconstructed scale five times too large.

The camera intrinsics are the ROS default values verified in A2 and A3: `525`, `525`, `319.5`, `239.5`.

References:

- TUM RGB-D file format: https://cvg.cit.tum.de/data/datasets/rgbd-dataset/file_formats
- Official RTAB-Map ROS 2 launch file: https://github.com/introlab/rtabmap_ros/blob/ros2/rtabmap_launch/launch/rtabmap.launch.py

## Front-end and back-end responsibilities

- `rgbd_odometry` estimates visual motion between nearby frames and publishes the `odom -> camera_rgb_optical_frame` transform.
- `rtabmap` receives the front-end outputs and performs appearance-based place recognition, geometric verification, loop-closure constraint creation and global pose-graph optimisation.
- `Rtabmap/DetectionRate=0` allows complete offline processing rather than skipping keyframes at the default 1 Hz. The other central settings remain close to the official dataset example.

## Loop-closure evidence

The main run's `/info` messages reported 124 events with `loop_closure_id > 0`. The database `Link` table contains 248 records with `type=1`. RTAB-Map stores each constraint in both directions, giving 124 unique `kGlobalClosure` constraints.

Examples include `44 <-> 450`, `45 <-> 449` and `47 <-> 437`, which connect observations separated by long intervals. Representative records and counts are stored in `loop_closures.json`.

`A4-20260930-xyz-smoke-02` was a short test using the default 1 Hz back-end detection rate. It produced only neighbouring constraints, and its audit explicitly records `loop_closure_demonstrated=false`. It demonstrates that the odometry and export path could run, but it is not used as evidence of loop closure.

## Ground-truth isolation

The replay node reads only the A2 association CSV, RGB PNG files, depth PNG files and camera configuration. It publishes three topics:

```text
/camera/rgb/image_color
/camera/depth/image
/camera/rgb/camera_info
```

`node_subscriptions.txt` shows that the estimation nodes did not subscribe to `/world`, `kinect_gt` or any other ground-truth topic. The two `ground_truth_*` configuration values were also empty. Only after all ROS estimation processes had exited and the database had closed were the following commands run:

```bash
evo_ape tum data/rgbd_dataset_freiburg1_desk/groundtruth.txt \
  results/a4/A4-20260930-desk-full-03/odometry_estimate.tum -a

evo_ape tum data/rgbd_dataset_freiburg1_desk/groundtruth.txt \
  results/a4/A4-20260930-desk-full-03/slam_poses.txt -a
```

## Reproduction

From the Windows project root, run `Run-A4.cmd`. It first performs a 90-frame `freiburg1_xyz` check and then runs the complete `freiburg1_desk` sequence. Each execution generates a new UTC run ID, so it neither overwrites earlier results nor reuses an old database.

The two stages can also be run separately in WSL:

```bash
cd <PROJECT_ROOT>
source scripts/ros_env.sh
/usr/bin/python3 scripts/run_a4.py --sequence xyz --label smoke
/usr/bin/python3 scripts/run_a4.py --sequence desk --label full
```

The runner copies a configuration snapshot, records node subscriptions, closes the database cleanly, and then invokes `rtabmap-export` to export the trajectory and map. A full run does not allow `--max-frames`, preventing a truncated experiment from being labelled as the complete sequence.

## Correction history

`A4-20260930-desk-full-01` used the 1 Hz back-end detection rate from the official example and did not produce loop closures; it is retained as negative evidence.

`A4-20260930-desk-full-02` produced graph constraints, but still published depth incorrectly as `16UC1`, making the reconstructed scale approximately five times too large. It is not used as the final map.

`A4-20260930-desk-full-03` corrected the depth stream to metre-valued `32FC1` and is the final recorded result.
