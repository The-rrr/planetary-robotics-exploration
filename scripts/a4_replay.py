#!/usr/bin/env python3
"""Replay A2 RGB-D associations and record estimator-only ROS outputs."""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from rtabmap_msgs.msg import Info
from sensor_msgs.msg import CameraInfo, Image


def ros_stamp(timestamp: float):
    from builtin_interfaces.msg import Time

    sec = int(timestamp)
    nanosec = int(round((timestamp - sec) * 1_000_000_000))
    if nanosec == 1_000_000_000:
        sec += 1
        nanosec = 0
    return Time(sec=sec, nanosec=nanosec)


class TumReplay(Node):
    def __init__(self, args: argparse.Namespace, depth_scale: float) -> None:
        super().__init__("a4_tum_replay")
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=50,
        )
        self.rgb_pub = self.create_publisher(Image, "/camera/rgb/image_color", qos)
        self.depth_pub = self.create_publisher(Image, "/camera/depth/image", qos)
        self.info_pub = self.create_publisher(CameraInfo, "/camera/rgb/camera_info", qos)
        self.create_subscription(Odometry, "/odom", self.on_odom, qos)
        self.create_subscription(Info, "/info", self.on_info, qos)
        self.output = args.output
        self.output.mkdir(parents=True, exist_ok=True)
        self.trajectory = (self.output / "odometry_estimate.tum").open("w", encoding="utf-8")
        self.events = (self.output / "rtabmap_events.jsonl").open("w", encoding="utf-8")
        self.odom_count = 0
        self.info_count = 0
        self.loop_events = 0
        self.depth_scale = depth_scale

    def on_odom(self, message: Odometry) -> None:
        stamp = message.header.stamp.sec + message.header.stamp.nanosec / 1e9
        pose = message.pose.pose
        self.trajectory.write(
            f"{stamp:.9f} {pose.position.x:.9f} {pose.position.y:.9f} "
            f"{pose.position.z:.9f} {pose.orientation.x:.9f} "
            f"{pose.orientation.y:.9f} {pose.orientation.z:.9f} "
            f"{pose.orientation.w:.9f}\n"
        )
        self.odom_count += 1

    def on_info(self, message: Info) -> None:
        stats = {key: float(value) for key, value in zip(message.stats_keys, message.stats_values)}
        event = {
            "timestamp": message.header.stamp.sec + message.header.stamp.nanosec / 1e9,
            "ref_id": int(message.ref_id),
            "loop_closure_id": int(message.loop_closure_id),
            "proximity_detection_id": int(message.proximity_detection_id),
            "stats": stats,
        }
        self.events.write(json.dumps(event, ensure_ascii=True, allow_nan=False) + "\n")
        self.info_count += 1
        if message.loop_closure_id > 0:
            self.loop_events += 1

    def publish_pair(self, rgb: np.ndarray, depth: np.ndarray, timestamp: float, intrinsics: dict) -> None:
        stamp = ros_stamp(timestamp)
        frame = "camera_rgb_optical_frame"

        rgb_msg = Image()
        rgb_msg.header.stamp = stamp
        rgb_msg.header.frame_id = frame
        rgb_msg.height, rgb_msg.width = rgb.shape[:2]
        rgb_msg.encoding = "rgb8"
        rgb_msg.is_bigendian = False
        rgb_msg.step = rgb_msg.width * 3
        rgb_msg.data = np.ascontiguousarray(rgb).tobytes()

        depth_msg = Image()
        depth_msg.header.stamp = stamp
        depth_msg.header.frame_id = frame
        depth_m = depth.astype(np.float32) / self.depth_scale
        depth_msg.height, depth_msg.width = depth.shape
        depth_msg.encoding = "32FC1"
        depth_msg.is_bigendian = False
        depth_msg.step = depth_msg.width * 4
        depth_msg.data = np.ascontiguousarray(depth_m.astype("<f4", copy=False)).tobytes()

        camera_info = CameraInfo()
        camera_info.header.stamp = stamp
        camera_info.header.frame_id = frame
        camera_info.height = rgb_msg.height
        camera_info.width = rgb_msg.width
        camera_info.distortion_model = "plumb_bob"
        camera_info.d = [0.0] * 5
        fx, fy = float(intrinsics["fx"]), float(intrinsics["fy"])
        cx, cy = float(intrinsics["cx"]), float(intrinsics["cy"])
        camera_info.k = [fx, 0.0, cx, 0.0, fy, cy, 0.0, 0.0, 1.0]
        camera_info.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        camera_info.p = [fx, 0.0, cx, 0.0, 0.0, fy, cy, 0.0, 0.0, 0.0, 1.0, 0.0]

        self.rgb_pub.publish(rgb_msg)
        self.depth_pub.publish(depth_msg)
        self.info_pub.publish(camera_info)

    def close_outputs(self) -> None:
        self.trajectory.flush()
        self.events.flush()
        self.trajectory.close()
        self.events.close()


def read_pairs(path: Path, max_frames: int | None) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"rgb_timestamp", "rgb_path", "depth_timestamp", "depth_path", "abs_dt_s"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Invalid A2 association file: {path}")
    return rows[:max_frames] if max_frames else rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--associations", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rate", type=float, default=5.0)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--startup-seconds", type=float, default=4.0)
    parser.add_argument("--settle-seconds", type=float, default=8.0)
    args = parser.parse_args()
    if args.rate <= 0 or args.startup_seconds < 0 or args.settle_seconds < 0:
        parser.error("rate must be positive and wait durations must be non-negative")
    if args.max_frames is not None and args.max_frames <= 0:
        parser.error("max-frames must be positive")
    return args


def main() -> int:
    args = parse_args()
    pairs = read_pairs(args.associations, args.max_frames)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    intrinsics = config["intrinsics_used"]
    rclpy.init()
    depth_scale = float(config["depth_scale"])
    if depth_scale <= 0:
        raise ValueError("depth_scale must be positive")
    node = TumReplay(args, depth_scale)
    published = 0
    started = time.monotonic()
    try:
        while time.monotonic() - started < args.startup_seconds:
            rclpy.spin_once(node, timeout_sec=0.05)
        period = 1.0 / args.rate
        for row in pairs:
            tick = time.monotonic()
            rgb_bgr = cv2.imread(str(args.dataset / row["rgb_path"]), cv2.IMREAD_COLOR)
            depth = cv2.imread(str(args.dataset / row["depth_path"]), cv2.IMREAD_UNCHANGED)
            if rgb_bgr is None or depth is None:
                raise FileNotFoundError(f"Could not read pair {row['rgb_path']} / {row['depth_path']}")
            if depth.dtype != np.uint16 or depth.ndim != 2 or rgb_bgr.shape[:2] != depth.shape:
                raise ValueError(f"Unexpected RGB-D format at pair {published}")
            rgb = cv2.cvtColor(rgb_bgr, cv2.COLOR_BGR2RGB)
            node.publish_pair(rgb, depth, float(row["rgb_timestamp"]), intrinsics)
            published += 1
            while time.monotonic() - tick < period:
                rclpy.spin_once(node, timeout_sec=min(0.02, period))
            if published % 50 == 0 or published == len(pairs):
                print(f"Published {published}/{len(pairs)} pairs; odometry messages={node.odom_count}", flush=True)
        settled = time.monotonic()
        while time.monotonic() - settled < args.settle_seconds:
            rclpy.spin_once(node, timeout_sec=0.05)
    finally:
        summary = {
            "association_source": str(args.associations),
            "dataset": str(args.dataset),
            "published_pairs": published,
            "requested_pairs": len(pairs),
            "odometry_messages": node.odom_count,
            "rtabmap_info_messages": node.info_count,
            "global_loop_events": node.loop_events,
            "groundtruth_published": False,
            "depth_input_encoding": "TUM 16-bit PNG, 5000 units/m",
            "depth_published_encoding": "32FC1 meters",
            "depth_scale_applied": depth_scale,
            "topics_published": [
                "/camera/rgb/image_color",
                "/camera/depth/image",
                "/camera/rgb/camera_info",
            ],
        }
        (args.output / "replay_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        node.close_outputs()
        node.destroy_node()
        rclpy.shutdown()
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if published == len(pairs) and node.odom_count > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
