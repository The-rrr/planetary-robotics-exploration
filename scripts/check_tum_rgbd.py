"""Inspect the two downloaded TUM sequences and regenerate A2 artifacts."""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SEQUENCES = ("freiburg1_xyz", "freiburg1_desk")


def read_table(path, columns):
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = line.split()
        if len(row) != columns:
            raise ValueError(f"{path}:{number}: expected {columns} columns")
        rows.append(row)
    if len(rows) < 2:
        raise ValueError(f"Too few records: {path}")
    times = np.array([float(row[0]) for row in rows])
    if not np.isfinite(times).all() or not (np.diff(times) > 0).all():
        raise ValueError(f"Non-finite or non-increasing original timestamps: {path}")
    return rows, times


def associate(rgb_times, depth_times, max_dt):
    # TUM-style greedy one-to-one association: shortest differences first.
    candidates = []
    for ri, timestamp in enumerate(rgb_times):
        start = bisect.bisect_left(depth_times, timestamp - max_dt)
        stop = bisect.bisect_right(depth_times, timestamp + max_dt)
        for di in range(start, stop):
            difference = abs(float(timestamp - depth_times[di]))
            if difference <= max_dt:
                candidates.append((difference, ri, di))
    used_rgb, used_depth, pairs = set(), set(), []
    for difference, ri, di in sorted(candidates):
        if ri not in used_rgb and di not in used_depth:
            used_rgb.add(ri)
            used_depth.add(di)
            pairs.append((ri, di, difference))
    return sorted(pairs)


def scan_images(dataset, rows, is_depth):
    missing, corrupt, resolutions, modes = [], [], set(), set()
    valid_pixels = total_pixels = readable = 0
    for _, relative_path in rows:
        path = dataset / relative_path
        if not path.is_file():
            missing.append(relative_path)
            continue
        try:
            with Image.open(path) as image:
                image.load()
                resolutions.add(image.size)
                modes.add(image.mode)
                if is_depth:
                    if image.format != "PNG" or image.mode not in ("I;16", "I;16L", "I;16B", "I"):
                        raise ValueError("Expected a 16-bit depth PNG")
                    raw = np.asarray(image)
                    if raw.ndim != 2 or raw.dtype.kind not in "ui" or raw.min() < 0 or raw.max() > 65535:
                        raise ValueError("Invalid depth array")
                    valid_pixels += int(np.count_nonzero(raw))
                    total_pixels += int(raw.size)
            readable += 1
        except Exception as error:
            corrupt.append({"path": relative_path, "error": str(error)})
    return {
        "indexed_frames": len(rows), "readable_frames": readable,
        "missing_files": missing, "corrupt_files": corrupt,
        "resolutions_width_height": [list(size) for size in sorted(resolutions)],
        "image_modes": sorted(modes),
        "valid_depth_ratio": valid_pixels / total_pixels if total_pixels else None,
        "invalid_depth_pixels": total_pixels - valid_pixels if is_depth else None,
        "total_depth_pixels": total_pixels if is_depth else None,
    }


def fps(times):
    return {"median_interval_fps": float(1 / np.median(np.diff(times))),
            "whole_span_fps": float((len(times) - 1) / (times[-1] - times[0]))}


def excerpts(rows):
    return [rows[index] for index in (0, len(rows) // 2, len(rows) - 1)]


def triptych(dataset, rgb_row, depth_row, output, config):
    with Image.open(dataset / rgb_row[1]) as image:
        rgb = np.array(image.convert("RGB"))
    with Image.open(dataset / depth_row[1]) as image:
        raw = np.array(image)
    if rgb.shape[:2] != raw.shape:
        raise ValueError("RGB/depth dimensions differ")
    invalid = raw == config["invalid_depth_value"]
    depth_m = raw.astype(np.float32) / config["depth_scale"]
    cmap = plt.get_cmap("turbo").copy()
    cmap.set_bad("black")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), layout="constrained")
    axes[0].imshow(rgb)
    axes[0].set_title(f"RGB | {rgb_row[0]} s")
    shown = axes[1].imshow(np.ma.masked_where(invalid, depth_m), cmap=cmap, vmin=0, vmax=5)
    axes[1].set_title(f"Depth | {depth_row[0]} s")
    fig.colorbar(shown, ax=axes[1], label="Z (m); display clipped at 5 m", shrink=0.8)
    axes[2].imshow(invalid, cmap="gray", vmin=0, vmax=1)
    axes[2].set_title(f"Invalid = white | {invalid.mean():.1%} of this frame")
    for axis in axes:
        axis.set_axis_off()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    ys, xs = np.nonzero(~invalid)
    if not len(xs):
        return None
    center = np.argmin((xs - raw.shape[1] // 2) ** 2 + (ys - raw.shape[0] // 2) ** 2)
    u, v = int(xs[center]), int(ys[center])
    return {"u": u, "v": v, "png_value": int(raw[v, u]),
            "z_m": float(raw[v, u] / config["depth_scale"])}


def inspect(name, data_root, output, max_dt, config):
    print(f"Checking {name}: reading all RGB/depth PNGs...", flush=True)
    dataset = data_root / f"rgbd_dataset_{name}"
    rgb, rgb_times = read_table(dataset / "rgb.txt", 2)
    depth, depth_times = read_table(dataset / "depth.txt", 2)
    gt, gt_times = read_table(dataset / "groundtruth.txt", 8)
    poses = np.asarray(gt, dtype=float)
    if not np.isfinite(poses).all():
        raise ValueError(f"Non-finite ground truth: {name}")
    pairs = associate(rgb_times, depth_times, max_dt)
    rgb_check = scan_images(dataset, rgb, False)
    depth_check = scan_images(dataset, depth, True)
    bad_rgb = set(rgb_check["missing_files"]) | {x["path"] for x in rgb_check["corrupt_files"]}
    bad_depth = set(depth_check["missing_files"]) | {x["path"] for x in depth_check["corrupt_files"]}
    usable = [p for p in pairs if rgb[p[0]][1] not in bad_rgb and depth[p[1]][1] not in bad_depth]
    if not usable:
        raise ValueError(f"No usable RGB-D pairs: {name}")
    used_rgb = {p[0] for p in pairs}
    used_depth = {p[1] for p in pairs}
    with (output / f"{name}_associations.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rgb_timestamp", "rgb_path", "depth_timestamp", "depth_path", "abs_dt_s"])
        for ri, di, difference in usable:
            writer.writerow([*rgb[ri], *depth[di], f"{difference:.9f}"])
    ri, di, difference = usable[len(usable) // 2]
    pixel = triptych(dataset, rgb[ri], depth[di], output / f"{name}_triptych.png", config)
    result = {
        "sequence": name, "timestamp_order": "strictly increasing in original RGB, depth and groundtruth files",
        "rgb": rgb_check, "depth": depth_check,
        "rgb_fps": fps(rgb_times), "depth_fps": fps(depth_times),
        "groundtruth_records": len(gt),
        "groundtruth_quaternion_max_norm_error": float(np.max(abs(np.linalg.norm(poses[:, 4:8], axis=1) - 1))),
        "association": {
            "method": "greedy shortest-time-difference first, one-to-one; offset=0",
            "max_allowed_dt_s": max_dt, "timestamp_matched_pairs": len(pairs), "usable_pairs": len(usable),
            "unmatched_rgb_count": len(rgb) - len(pairs), "unused_depth_count": len(depth) - len(pairs),
            "pairs_lost_to_file_errors": len(pairs) - len(usable),
            "actual_max_dt_s": max(p[2] for p in pairs),
            "mean_dt_s": float(np.mean([p[2] for p in pairs])),
            "unmatched_rgb_rows": [row for i, row in enumerate(rgb) if i not in used_rgb],
            "unused_depth_rows": [row for i, row in enumerate(depth) if i not in used_depth],
        },
        "example": {"rgb_row": rgb[ri], "depth_row": depth[di], "dt_s": difference, "pixel": pixel},
        "manual_inspection_samples": {"rgb": excerpts(rgb), "depth": excerpts(depth), "groundtruth": excerpts(gt)},
        "visual_correspondence": "Inspect generated triptych; not automatically certified",
    }
    print(f"  RGB={len(rgb)}, depth={len(depth)}, usable pairs={len(usable)}; "
          f"valid depth={depth_check['valid_depth_ratio']:.2%}", flush=True)
    return result


def write_note(results, config, path):
    lines = ["# A2：TUM RGB-D 数据检查说明", "",
             "运行项目根目录的 `Run-A2.cmd` 可重新生成统计、三联图和单帧三维点云预览。完整统计及人工抽查样例见 `results/a2/summary.json`，匹配清单见同目录 CSV。", "",
             "|序列|RGB/深度帧|可用配对|未匹配RGB/未使用深度|RGB/深度帧率|有效深度比例|实际最大时间差|",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        a = r["association"]
        lines.append(f"|{r['sequence']}|{r['rgb']['indexed_frames']}/{r['depth']['indexed_frames']}|"
                     f"{a['usable_pairs']}|{a['unmatched_rgb_count']}/{a['unused_depth_count']}|"
                     f"{r['rgb_fps']['median_interval_fps']:.2f}/{r['depth_fps']['median_interval_fps']:.2f}|"
                     f"{r['depth']['valid_depth_ratio']:.2%}|{1000*a['actual_max_dt_s']:.3f} ms|")
    lines += ["", f"关联方法：时间差优先的一对一贪心匹配，最大允许差 {1000*results[0]['association']['max_allowed_dt_s']:.1f} ms，时间偏移为 0。未匹配帧未从磁盘删除。",
              "帧率为相邻时间戳间隔中位数的倒数；全时段帧率另存 JSON。有效深度比例统计全部可读取深度图，0 值为无效。"]
    for r in results:
        lines.append(f"{r['sequence']}：RGB/深度分辨率 {r['rgb']['resolutions_width_height']}/{r['depth']['resolutions_width_height']}（宽×高）；"
                     f"缺失文件 {len(r['rgb']['missing_files'])+len(r['depth']['missing_files'])}，损坏文件 {len(r['rgb']['corrupt_files'])+len(r['depth']['corrupt_files'])}，"
                     f"无效深度像素累计 {r['depth']['invalid_depth_pixels']}；真值 {r['groundtruth_records']} 条，三类原始时间戳均严格递增。")
    lines += ["", "**深度与内参。** 16 位 PNG 的 `Z（米）= 原始像素值 / 5000`；Z 是沿光轴的深度，通常不等于到相机光心的直线距离。0 表示没有测量。官方已应用深度校正，不重复乘 1.035。三联图深度颜色范围为 0–5 m，超过 5 m 的值只在显示中截色，统计不截断。",
              "程序读取 `configs/tum_freiburg1.json`。其中记录 Freiburg 1 官方 RGB 标定值 `fx=517.3, fy=516.5, cx=318.6, cy=255.3` 及畸变系数；同时记录官方对预配准图像建议的 ROS 默认参数 `525, 525, 319.5, 239.5`。本次只检查数据，不做去畸变或反投影。", "",
              "**坐标与真值。** 光学相机坐标 x 向右、y 向下、z 向前。世界坐标由动捕系统定义，不能假定世界原点就是第一帧相机位置。真值字段 `timestamp tx ty tz qx qy qz qw`；时间戳为 Unix 秒，平移单位为米，四元数实部 qw 在最后。真值描述彩色相机光心在世界系中的位姿，`p_world = R(q) p_camera + t`。", "",
              "**像素抽查。**", ""]
    for r in results:
        p = r["example"]["pixel"]
        if p:
            lines.append(f"- {r['sequence']}：像素 `(u,v)=({p['u']},{p['v']})`，PNG 值 {p['png_value']}，Z={p['png_value']}/5000={p['z_m']:.4f} m。")
    lines += ["", "**三维预览。** 同目录的 `*_pointcloud.html` 是用三联图对应的 RGB-D 帧生成的可旋转单帧点云。每 4 个像素采样一次，仅显示 0<Z≤5 m 的有效深度，使用上述 ROS 默认内参；这是相机坐标系下的预览，不是多帧 SLAM 地图。", "",
              "**人工验收。** 打开两张三联图，比较桌沿、显示器和物体轮廓是否对应；右侧白色表示缺失深度。此项需要目视检查，程序不自动声称通过。", "",
              f"官方依据：{config['source']}"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "a2")
    parser.add_argument("--note", type=Path, default=ROOT / "docs" / "a2_data_notes.md")
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "tum_freiburg1.json")
    parser.add_argument("--max-dt", type=float, default=0.02)
    args = parser.parse_args()
    if not np.isfinite(args.max_dt) or args.max_dt <= 0:
        parser.error("--max-dt must be finite and positive")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config["depth_scale"] <= 0 or config["invalid_depth_value"] != 0:
        raise ValueError("This inspector expects TUM PNG depth with invalid value 0")
    args.output.mkdir(parents=True, exist_ok=True)
    results = [inspect(name, args.data_root, args.output, args.max_dt, config) for name in SEQUENCES]
    summary = {"configuration": config, "sequences": results}
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_note(results, config, args.note)
    print(f"Done. Figures and JSON: {args.output}\nData notes: {args.note}")
    if any(r[k]["missing_files"] or r[k]["corrupt_files"] for r in results for k in ("rgb", "depth")):
        raise SystemExit("Inspection completed with missing/corrupt images; see summary.json")


if __name__ == "__main__":
    main()
