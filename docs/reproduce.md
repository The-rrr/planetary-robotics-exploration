# Reproducing the Selected Workflow

This public snapshot includes the data-inspection, geometry, replay and audit scripts; original machine-installation helpers are omitted. The September run used Ubuntu 24.04, ROS 2 Jazzy, RTAB-Map 0.23.7, Open3D 0.19.0 and evo 1.37.1. Software availability and exact package builds may differ on another machine.

## 1. Data and analysis environment

Download `freiburg1_xyz` and `freiburg1_desk` from the [official TUM dataset page](https://cvg.cit.tum.de/data/datasets/rgbd-dataset) and extract them into:

```text
data/rgbd_dataset_freiburg1_xyz/
data/rgbd_dataset_freiburg1_desk/
```

Each folder should contain `rgb.txt`, `depth.txt`, the image folders and `groundtruth.txt`. Obtain the data separately; do not assume it is bundled with this repository. Refer to [the file-format description](https://cvg.cit.tum.de/data/datasets/rgbd-dataset/file_formats).

For analysis, use a dedicated Python environment and the dependency file:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r configs/requirements-analysis.txt
python scripts/check_tum_rgbd.py
python scripts/a3_single_frame.py
```

On Windows activate with `.venv\Scripts\Activate.ps1`. The A3 script opens an Open3D window and therefore needs a graphical session. The inspection script regenerates `results/a2` and the A2 data note.

## 2. ROS estimation

Install ROS 2 Jazzy and RTAB-Map following [ROS documentation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) and the [RTAB-Map ROS repository](https://github.com/introlab/rtabmap_ros). The replay uses ROS's system Python; make sure its OpenCV and NumPy imports work. The original machine used system ROS packages, not the analysis virtual environment, for this stage.

Deactivate the analysis environment and run from the repository root in Ubuntu:

```bash
deactivate
source scripts/ros_env.sh
/usr/bin/python3 scripts/run_a4.py --sequence xyz --label smoke
/usr/bin/python3 scripts/run_a4.py --sequence desk --label full
```

The runner starts estimation nodes, replays the paired images, saves outputs and configuration snapshots, stops estimation, exports the map/poses and audits the database. Every run has its own directory. Do not use `--max-frames` for a run labelled full. Read logs before interpreting results.

## 3. Independent evaluation

After the estimator processes have stopped, substitute the generated run directory:

```bash
evo_ape tum data/rgbd_dataset_freiburg1_desk/groundtruth.txt results/a4/YOUR_RUN/odometry_estimate.tum -a
evo_ape tum data/rgbd_dataset_freiburg1_desk/groundtruth.txt results/a4/YOUR_RUN/slam_poses.txt -a
```

Ground truth belongs in evaluation only. Frame matching and trajectory lengths must be documented when comparing the two estimates. A matched-timestamp ablation and RPE analysis remain future work.

## Publication validation

For this publication, selected Python files were syntax-checked, saved trajectories were checked for finite values and monotonic timestamps, and figures were rendered from saved outputs. A new end-to-end ROS benchmark was not run. The large original map/database are not included; re-run the pipeline to create them.
