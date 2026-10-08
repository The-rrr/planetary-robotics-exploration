# A2: TUM RGB-D Data Inspection Notes

Run `Run-A2.cmd` from the project root to regenerate the statistics, three-panel figures and single-frame 3D point-cloud previews. The complete statistics and manually inspected samples are recorded in `results/a2/summary.json`; the matched-frame lists are stored in CSV files in the same directory.

| Sequence | RGB/depth frames | Usable pairs | Unmatched RGB/unused depth | RGB/depth frame rate | Valid depth ratio | Maximum observed time difference |
|---|---:|---:|---:|---:|---:|---:|
| `freiburg1_xyz` | 798/798 | 792 | 6/6 | 31.15/30.74 Hz | 75.69% | 17.230 ms |
| `freiburg1_desk` | 613/595 | 573 | 40/22 | 31.18/30.93 Hz | 74.53% | 19.742 ms |

The association method is a one-to-one greedy match prioritising the smallest timestamp difference. The maximum allowed difference is 20.0 ms and the timestamp offset is zero. Unmatched frames are retained on disk.

Frame rate is calculated as the reciprocal of the median interval between adjacent timestamps; whole-sequence frame rates are also saved in JSON. The valid-depth ratio is calculated across all readable depth images, with zero treated as an invalid measurement.

- `freiburg1_xyz`: RGB/depth resolutions are `[[640, 480]]/[[640, 480]]` (width × height). There are no missing or corrupted files. The cumulative number of invalid depth pixels is 59,591,839. The ground-truth file contains 3,000 entries, and all three original timestamp streams are strictly increasing.
- `freiburg1_desk`: RGB/depth resolutions are `[[640, 480]]/[[640, 480]]` (width × height). There are no missing or corrupted files. The cumulative number of invalid depth pixels is 46,551,587. The ground-truth file contains 2,335 entries, and all three original timestamp streams are strictly increasing.

## Depth values and camera intrinsics

For the 16-bit depth PNG files:

```text
Z (metres) = raw pixel value / 5000
```

`Z` is depth along the camera's optical axis and is generally different from the straight-line distance to the camera centre. A value of zero means that no valid depth was measured. The official depth correction has already been applied, so the values are not multiplied by 1.035 again.

The depth colour range in the three-panel figures is 0–5 m. Values beyond 5 m are clipped only for display; the underlying statistics are not truncated.

The program reads `configs/tum_freiburg1.json`. This file records the published Freiburg 1 RGB calibration (`fx=517.3`, `fy=516.5`, `cx=318.6`, `cy=255.3`) and distortion coefficients. It also records the ROS default intrinsics recommended for the pre-registered images (`525`, `525`, `319.5`, `239.5`). A2 only inspects the data and does not undistort images or back-project pixels.

## Coordinates and ground truth

The optical camera coordinate system uses +x to the right, +y downwards and +z forwards. The motion-capture system defines the world coordinate system, so the world origin must not be assumed to coincide with the first camera position.

Ground-truth rows use the format:

```text
timestamp tx ty tz qx qy qz qw
```

The timestamp is in Unix seconds, translation is in metres, and the real component `qw` appears last in the quaternion. The ground truth describes the pose of the RGB camera centre in the world frame:

```text
p_world = R(q) p_camera + t
```

## Pixel spot checks

- `freiburg1_xyz`: at pixel `(u,v)=(320,240)`, the PNG value is 4765, giving `Z=4765/5000=0.9530 m`.
- `freiburg1_desk`: at pixel `(u,v)=(320,240)`, the PNG value is 3719, giving `Z=3719/5000=0.7438 m`.

## 3D previews

The `*_pointcloud.html` files in the same directory are rotatable single-frame point clouds produced from the RGB-D frames shown in the three-panel figures. The preview samples every fourth pixel, retains valid depths satisfying `0 < Z ≤ 5 m`, and uses the ROS default intrinsics above. It is a preview in the camera coordinate frame, not a multi-frame SLAM map.

## Manual inspection

Open both three-panel figures and check whether the desk edge, monitor and object outlines agree across the RGB and depth views. White regions in the right-hand panel indicate missing depth. This check requires visual inspection; the program does not automatically claim that it has passed.

Official reference: https://cvg.cit.tum.de/data/datasets/rgbd-dataset/file_formats
