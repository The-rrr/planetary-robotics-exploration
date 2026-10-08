# A3：使用 Open3D 将单帧 RGB-D 转换为三维点云

本教程对应脚本 `scripts/a3_single_frame.py`，输入来自 A2 已完成时间匹配的 TUM Freiburg 1 RGB-D 图像。

## 一、代码如何保存

本次演示使用 Windows 记事本完成：

1. 在记事本中按 `Ctrl+N` 新建标签页。
2. 将 Python 代码粘贴到空白编辑区。
3. 按 `Ctrl+Shift+S` 打开“另存为”。
4. 文件名输入完整路径：

   ```text
   <PROJECT_ROOT>\scripts\a3_single_frame.py
   ```

5. 编码选择 `UTF-8`，然后单击“保存”。
6. 检查标签名是否为 `a3_single_frame.py`，而不是 `a3_single_frame.py.txt`。

Python 脚本应使用 `.py` 扩展名。若资源管理器隐藏了扩展名，可以在“查看 → 显示”中开启“文件扩展名”。

## 二、运行程序

在项目根目录打开 PowerShell，运行：

```powershell
cd <PROJECT_ROOT>
.\.venv-win\Scripts\python.exe .\scripts\a3_single_frame.py
```

程序会完成以下工作：

1. 从 `results/a2/freiburg1_xyz_associations.csv` 选择中间的一对 RGB-D 图像。
2. 从 `configs/tum_freiburg1.json` 读取深度比例和相机内参。
3. 将 RGB 与深度图组成 Open3D `RGBDImage`。
4. 将有效深度像素反投影为带颜色的三维点。
5. 剔除零值、非有限值和超过 5 m 的深度。
6. 比较 5 mm、10 mm、20 mm 和 50 mm 体素降采样。
7. 保存完整点云和选定的 10 mm 降采样点云。
8. 执行一次旋转和平移，再用逆矩阵还原。
9. 打开 Open3D 三维查看窗口。

## 三、像素如何变成三维点

深度图中每个像素 `(u,v)` 保存一个深度值。对本项目使用的 TUM 16 位深度 PNG：

```text
Z = PNG像素值 / 5000
```

其中 `Z` 的单位是米，并且是沿相机光轴的深度。相机内参为：

```text
fx = 525.0
fy = 525.0
cx = 319.5
cy = 239.5
```

反投影公式为：

```text
X = (u - cx) * Z / fx
Y = (v - cy) * Z / fy
```

因此，一个有深度的二维像素会变成一个三维点 `(X,Y,Z)`。该像素在 RGB 图上的颜色会赋给对应三维点。

## 四、Open3D 代码主线

核心调用可以概括为：

```python
color = o3d.io.read_image(rgb_path)
depth = o3d.io.read_image(depth_path)

intrinsic = o3d.camera.PinholeCameraIntrinsic(
    640, 480, 525.0, 525.0, 319.5, 239.5
)

rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
    color,
    depth,
    depth_scale=5000.0,
    depth_trunc=5.0,
    convert_rgb_to_intensity=False,
)

pcd = o3d.geometry.PointCloud.create_from_rgbd_image(
    rgbd,
    intrinsic,
    project_valid_depth_only=True,
)
```

三个容易出错的参数：

- `depth_scale=5000.0`：TUM 数据不能沿用 Open3D 默认的 1000，否则尺度会错 5 倍。
- `depth_trunc=5.0`：本实验只保留 5 m 内的点。
- `convert_rgb_to_intensity=False`：否则彩色图会转换为灰度。

## 五、查看和判断方向

Open3D 窗口中：

- 按住鼠标左键拖动：旋转视角。
- 滚动滚轮：放大或缩小。
- 按住 `Ctrl` 再用鼠标左键拖动，或按住滚轮拖动：平移视角。
- 按住 `Shift` 再用鼠标左键拖动：绕视线方向翻滚。
- 按 `R`：恢复默认视角；按 `H`：在程序输出中显示完整快捷键帮助。
- 单击窗口右上角关闭按钮：结束程序。

脚本保留相机光学坐标系：

```text
+X：图像右方
+Y：图像下方
+Z：相机前方
```

坐标轴颜色通常为红色 X、绿色 Y、蓝色 Z。因为光学坐标的 Y 向下，默认观察视角可能显得上下颠倒；这不一定表示数据错误。用于后续 SLAM 的原始点云应继续保持 `+Z` 向前。

检查标准：

- 桌面、墙面等结构没有明显镜像。
- 不应在 X、Y 方向发生异常拉长。
- 室内深度应处于米级，而不是毫米级或数百米。
- RGB 颜色边界大致贴合几何边界。

## 六、降采样

脚本比较以下体素大小：

```text
0.005 m = 5 mm
0.010 m = 10 mm
0.020 m = 20 mm
0.050 m = 50 mm
```

调用方式：

```python
down = pcd.voxel_down_sample(0.01)
```

本实验选择 `0.01 m`。它通常能明显减少点数，同时保留桌沿和主要物体轮廓。

本次实际结果：

```text
完整点云：237,041 点
10 mm 降采样：23,553 点
深度范围：0.7358～3.6782 m
深度中位数：0.9348 m
```

## 七、坐标变换实验

三维刚体变换使用 4×4 齐次矩阵：

```text
T = [ R  t ]
    [ 0  1 ]
```

其中 `R` 是 3×3 旋转矩阵，`t` 是三维平移。Open3D 调用为：

```python
transformed.transform(T)
restored.transform(np.linalg.inv(T))
```

本次从变换后的点云用 `T` 的逆矩阵还原，测得：

```text
最大误差：1.09e-15 m
平均误差：2.23e-16 m
```

误差接近双精度浮点数精度，说明变换和逆变换关系正确。

## 八、输出文件

程序在 `results/a3` 中生成：

| 文件 | 含义 |
|---|---|
| `single_frame_full.ply` | 未降采样的单帧彩色点云 |
| `single_frame_voxel_10mm.ply` | 1 cm 体素降采样点云 |
| `transformed.ply` | 人工旋转和平移后的点云 |
| `restored.ply` | 使用逆变换还原后的点云 |

这些 `.ply` 文件可以再次用 Open3D、CloudCompare 或 MeshLab 打开。

## 九、常见问题

### 点云尺度大了或小了 5 倍

检查 `depth_scale` 是否错误地用了默认值 1000。本项目必须使用 5000。

### 点云没有颜色

检查 `convert_rgb_to_intensity=False`，并确认 RGB 与深度图尺寸相同、已经配准。

### 点云像是上下颠倒

先确认这是观察视角问题还是坐标数据问题。相机光学坐标本来就是 Y 向下。不要仅为了看起来直立就修改用于 SLAM 的原始点云坐标。

### 双击 Python 文件后窗口一闪而过

不要直接双击脚本。应在 PowerShell 中运行，这样能够看到报错信息和统计结果。
