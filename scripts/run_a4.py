#!/usr/bin/env python3
"""Run a reproducible RTAB-Map RGB-D experiment and export its artifacts."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEQUENCES = {"xyz": "freiburg1_xyz", "desk": "freiburg1_desk"}


def command_output(command: list[str]) -> str:
    return subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False).stdout


def stop_process(process: subprocess.Popen, timeout: float = 15.0) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGINT)
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence", choices=sorted(SEQUENCES), default="desk")
    parser.add_argument("--label", choices=("smoke", "full"), default="full")
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--rate", type=float, default=5.0)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if args.label == "smoke" and args.max_frames is None:
        args.max_frames = 90
    if args.label == "full" and args.max_frames is not None:
        parser.error("full runs must not set --max-frames")
    return args


def main() -> int:
    args = parse_args()
    sequence = SEQUENCES[args.sequence]
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"A4-{timestamp}-{args.sequence}-{args.label}"
    if any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for character in run_id):
        raise ValueError("run-id may contain only letters, digits, hyphen and underscore")
    run_dir = ROOT / "results" / "a4" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    dataset = ROOT / "data" / f"rgbd_dataset_{sequence}"
    associations = ROOT / "results" / "a2" / f"{sequence}_associations.csv"
    camera_config = ROOT / "configs" / "tum_freiburg1.json"
    ros_config = ROOT / "configs" / "a4_rtabmap.yaml"
    for required in (dataset, associations, camera_config, ros_config):
        if not required.exists():
            raise FileNotFoundError(required)
    shutil.copy2(camera_config, run_dir / camera_config.name)
    shutil.copy2(ros_config, run_dir / ros_config.name)

    database = run_dir / "rtabmap.db"
    environment = dict(os.environ)
    environment.setdefault("ROS_DOMAIN_ID", "73")
    environment.setdefault("ROS_AUTOMATIC_DISCOVERY_RANGE", "LOCALHOST")
    odom_command = [
        "ros2", "run", "rtabmap_odom", "rgbd_odometry",
        "--ros-args", "--params-file", str(ros_config),
        "-r", "rgb/image:=/camera/rgb/image_color",
        "-r", "depth/image:=/camera/depth/image",
        "-r", "rgb/camera_info:=/camera/rgb/camera_info",
    ]
    slam_command = [
        "ros2", "run", "rtabmap_slam", "rtabmap", "-d",
        "--ros-args", "--params-file", str(ros_config),
        "-p", f"database_path:={database}",
        "-r", "rgbd_image:=/odom_rgbd_image",
    ]
    replay_command = [
        "/usr/bin/python3", str(ROOT / "scripts" / "a4_replay.py"),
        "--dataset", str(dataset),
        "--associations", str(associations),
        "--config", str(camera_config),
        "--output", str(run_dir),
        "--rate", str(args.rate),
    ]
    if args.max_frames:
        replay_command += ["--max-frames", str(args.max_frames)]

    manifest = {
        "run_id": run_id,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "sequence": sequence,
        "run_label": args.label,
        "max_frames": args.max_frames,
        "replay_rate_hz": args.rate,
        "association_file": str(associations),
        "groundtruth_input_to_estimator": False,
        "groundtruth_file_read_by_pipeline": False,
        "roles": {
            "rgbd_odometry": "adjacent-frame motion estimate and odom publication",
            "rtabmap": "loop closure detection and globally consistent pose-graph optimization",
        },
        "commands": {"odometry": odom_command, "slam": slam_command, "replay": replay_command},
        "versions": {
            "rtabmap": command_output(["rtabmap", "--version"]).strip(),
            "packages": command_output(["dpkg-query", "-W", "ros-jazzy-rtabmap", "ros-jazzy-rtabmap-odom", "ros-jazzy-rtabmap-slam"]).strip(),
        },
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Run ID: {run_id}", flush=True)
    print(f"Output: {run_dir}", flush=True)
    processes: list[tuple[subprocess.Popen, object]] = []
    try:
        for name, command in (("odometry", odom_command), ("slam", slam_command)):
            log = (run_dir / f"{name}.log").open("w", encoding="utf-8")
            process = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                env=environment,
                start_new_session=True,
            )
            processes.append((process, log))
        time.sleep(4.0)
        subscriptions = []
        for node in ("/rgbd_odometry", "/rtabmap"):
            subscriptions.append(f"===== {node} =====\n{command_output(['ros2', 'node', 'info', node])}")
        (run_dir / "node_subscriptions.txt").write_text("\n".join(subscriptions), encoding="utf-8")
        for process, _ in processes:
            if process.poll() is not None:
                raise RuntimeError("RTAB-Map process exited before replay; inspect run logs")
        with (run_dir / "replay.log").open("w", encoding="utf-8") as replay_log:
            replay = subprocess.run(replay_command, stdout=replay_log, stderr=subprocess.STDOUT, text=True, env=environment)
        if replay.returncode != 0:
            raise RuntimeError(f"Replay failed with exit code {replay.returncode}; inspect replay.log")
    finally:
        for process, _ in reversed(processes):
            stop_process(process)
        for _, log in processes:
            log.close()

    if not database.is_file() or database.stat().st_size == 0:
        raise RuntimeError("RTAB-Map database was not created")
    export_log = run_dir / "export.log"
    export_command = [
        "rtabmap-export", "--cloud", "--poses", "--poses_format", "10", "--opt", "2",
        "--output", "slam", "--output_dir", str(run_dir), str(database),
    ]
    with export_log.open("w", encoding="utf-8") as handle:
        exported = subprocess.run(export_command, stdout=handle, stderr=subprocess.STDOUT, text=True, env=environment)
    if exported.returncode != 0:
        raise RuntimeError(f"rtabmap-export failed with exit code {exported.returncode}")
    info_text = command_output(["rtabmap-info", str(database)])
    (run_dir / "database_info.txt").write_text(info_text, encoding="utf-8")
    analyze = subprocess.run([
        "/usr/bin/python3", str(ROOT / "scripts" / "analyze_a4_db.py"), str(database),
        "--events", str(run_dir / "rtabmap_events.jsonl"), "--output", str(run_dir / "loop_closures.json"),
    ], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=environment)
    (run_dir / "analysis.log").write_text(analyze.stdout, encoding="utf-8")
    if analyze.returncode != 0:
        raise RuntimeError("Database analysis failed; inspect analysis.log")
    print(f"Completed: {run_id}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"A4 failed: {error}", file=sys.stderr)
        raise
