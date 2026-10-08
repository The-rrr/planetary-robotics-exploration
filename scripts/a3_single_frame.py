"""A3: Convert one paired TUM RGB-D frame to a colored Open3D point cloud."""
from __future__ import annotations

import copy
import csv
import json
import time
from pathlib import Path

import numpy as np
import open3d as o3d


ROOT = Path(__file__).resolve().parents[1]
SEQUENCE = "freiburg1_xyz"
DATASET = ROOT / "data" / f"rgbd_dataset_{SEQUENCE}"
ASSOCIATIONS = ROOT / "results" / "a2" / f"{SEQUENCE}_associations.csv"
CONFIG_PATH = ROOT / "configs" / "tum_freiburg1.json"
OUTPUT = ROOT / "results" / "a3"
DEPTH_MAX_M = 5.0
SELECTED_VOXEL_M = 0.01


def load_middle_pair():
    with ASSOCIATIONS.open(newline="", encoding="utf-8") as handle:
        pairs = list(csv.DictReader(handle))
    pair = pairs[len(pairs) // 2]
    return DATASET / pair["rgb_path"], DATASET / pair["depth_path"], pair


def make_point_cloud(rgb_path: Path, depth_path: Path):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    k = config["intrinsics_used"]

    color = o3d.io.read_image(str(rgb_path))
    depth = o3d.io.read_image(str(depth_path))
    color_array = np.asarray(color)
    height, width = color_array.shape[:2]

    intrinsic = o3d.camera.PinholeCameraIntrinsic(
        width, height, k["fx"], k["fy"], k["cx"], k["cy"]
    )
    rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
        color,
        depth,
        depth_scale=config["depth_scale"],
        depth_trunc=DEPTH_MAX_M,
        convert_rgb_to_intensity=False,
    )
    pcd = o3d.geometry.PointCloud.create_from_rgbd_image(
        rgbd, intrinsic, project_valid_depth_only=True
    )

    points = np.asarray(pcd.points)
    valid = (
        np.isfinite(points).all(axis=1)
        & (points[:, 2] > 0.0)
        & (points[:, 2] <= DEPTH_MAX_M)
    )
    return pcd.select_by_index(np.flatnonzero(valid).tolist())


def print_geometry_check(pcd):
    points = np.asarray(pcd.points)
    extent = pcd.get_axis_aligned_bounding_box().get_extent()
    print(f"Valid points: {len(points):,}")
    print(f"Z median: {np.median(points[:, 2]):.4f} m")
    print(f"Z range: {points[:, 2].min():.4f} to {points[:, 2].max():.4f} m")
    print(f"Bounding-box XYZ extent: {extent} m")
    print("Optical coordinates: +X right, +Y down, +Z forward")


def compare_voxel_sizes(pcd):
    selected = None
    for voxel_size in (0.005, 0.01, 0.02, 0.05):
        start = time.perf_counter()
        down = pcd.voxel_down_sample(voxel_size)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        print(
            f"voxel={voxel_size:.3f} m | "
            f"{len(pcd.points):,} -> {len(down.points):,} points | "
            f"{elapsed_ms:.2f} ms"
        )
        if voxel_size == SELECTED_VOXEL_M:
            selected = down
    return selected


def transformation_experiment(pcd):
    original = np.asarray(pcd.points).copy()
    angles = np.deg2rad([10.0, 20.0, -15.0])
    transform = np.eye(4)
    transform[:3, :3] = o3d.geometry.get_rotation_matrix_from_xyz(angles)
    transform[:3, 3] = [0.10, -0.05, 0.20]

    transformed = copy.deepcopy(pcd)
    transformed.transform(transform)
    restored = copy.deepcopy(transformed)
    restored.transform(np.linalg.inv(transform))

    errors = np.linalg.norm(np.asarray(restored.points) - original, axis=1)
    print("Transform T:")
    print(transform)
    print(f"Restore max error: {errors.max():.3e} m")
    print(f"Restore mean error: {errors.mean():.3e} m")
    return transformed, restored


def save_cloud(path: Path, pcd):
    if not o3d.io.write_point_cloud(str(path), pcd, write_ascii=False):
        raise RuntimeError(f"Failed to save point cloud: {path}")
    print(f"Saved: {path}")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rgb_path, depth_path, pair = load_middle_pair()
    print(f"RGB: {rgb_path}")
    print(f"Depth: {depth_path}")
    print(f"Timestamp difference: {float(pair['abs_dt_s']) * 1000:.3f} ms")

    pcd = make_point_cloud(rgb_path, depth_path)
    print_geometry_check(pcd)
    save_cloud(OUTPUT / "single_frame_full.ply", pcd)

    down = compare_voxel_sizes(pcd)
    save_cloud(OUTPUT / "single_frame_voxel_10mm.ply", down)

    transformed, restored = transformation_experiment(down)
    save_cloud(OUTPUT / "transformed.ply", transformed)
    save_cloud(OUTPUT / "restored.ply", restored)

    coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.3)
    o3d.visualization.draw_geometries(
        [down, coordinate_frame],
        window_name="A3 - X right, Y down, Z forward",
        width=1280,
        height=800,
    )


if __name__ == "__main__":
    main()
