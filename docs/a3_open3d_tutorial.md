# A3: Converting a Single RGB-D Frame into a 3D Point Cloud with Open3D

This tutorial accompanies `scripts/a3_single_frame.py`. Its inputs are the timestamp-matched TUM Freiburg 1 RGB-D images prepared in A2.

## 1. Saving the script

The original demonstration used Windows Notepad:

1. Press `Ctrl+N` in Notepad to open a new tab.
2. Paste the Python code into the empty editor.
3. Press `Ctrl+Shift+S` to open **Save As**.
4. Enter the full filename:

   ```text
   <PROJECT_ROOT>\scripts\a3_single_frame.py
   ```

5. Select `UTF-8` encoding and click **Save**.
6. Check that the tab is named `a3_single_frame.py`, rather than `a3_single_frame.py.txt`.

Python scripts should use the `.py` extension. If File Explorer hides extensions, enable **File name extensions** under **View → Show**.

## 2. Running the program

Open PowerShell in the project root and run:

```powershell
cd <PROJECT_ROOT>
.\.venv-win\Scripts\python.exe .\scripts\a3_single_frame.py
```

The program performs the following steps:

1. Selects the middle RGB-D pair from `results/a2/freiburg1_xyz_associations.csv`.
2. Reads the depth scale and camera intrinsics from `configs/tum_freiburg1.json`.
3. Combines the colour and depth images into an Open3D `RGBDImage`.
4. Back-projects valid depth pixels into coloured 3D points.
5. Removes zero, non-finite and beyond-5-metre depth values.
6. Compares voxel sizes of 5 mm, 10 mm, 20 mm and 50 mm.
7. Saves the complete point cloud and the selected 10 mm downsampled cloud.
8. Applies a rotation and translation, then restores the cloud with the inverse matrix.
9. Opens the Open3D 3D viewer.

## 3. Converting pixels into 3D points

Each depth-image pixel `(u,v)` stores a depth value. For the TUM 16-bit depth PNG files used here:

```text
Z = PNG pixel value / 5000
```

`Z` is measured in metres along the camera's optical axis. The camera intrinsics are:

```text
fx = 525.0
fy = 525.0
cx = 319.5
cy = 239.5
```

The back-projection equations are:

```text
X = (u - cx) * Z / fx
Y = (v - cy) * Z / fy
```

A two-dimensional pixel with valid depth therefore becomes a three-dimensional point `(X,Y,Z)`. Its colour is taken from the corresponding pixel in the RGB image.

## 4. Main Open3D operations

The core calls can be summarised as follows:

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

Three parameters require particular care:

- `depth_scale=5000.0`: TUM data must not use Open3D's default scale of 1000, which would make the reconstructed scene five times too large.
- `depth_trunc=5.0`: this experiment retains points within 5 m.
- `convert_rgb_to_intensity=False`: this preserves colour rather than converting the RGB image to greyscale.

## 5. Viewing the cloud and checking its orientation

In the Open3D window:

- Hold the left mouse button and drag to rotate the view.
- Use the scroll wheel to zoom.
- Hold `Ctrl` and drag with the left mouse button, or drag with the middle mouse button, to pan.
- Hold `Shift` and drag with the left mouse button to roll around the viewing direction.
- Press `R` to restore the default view and `H` to show the complete shortcut help in the program output.
- Click the close button in the upper-right corner to end the program.

The script retains the optical camera coordinate system:

```text
+X: right in the image
+Y: down in the image
+Z: forwards from the camera
```

Coordinate axes are usually shown as red for X, green for Y and blue for Z. Because optical coordinates use +Y downwards, the cloud may appear upside down from the default viewing direction. This does not necessarily indicate an error. The original cloud used by later SLAM stages should retain +Z forwards.

Inspection criteria:

- Structures such as the desk and walls should not be visibly mirrored.
- The cloud should not be abnormally stretched along X or Y.
- Indoor depths should be on the scale of metres, rather than millimetres or hundreds of metres.
- RGB colour boundaries should approximately follow geometric boundaries.

## 6. Downsampling

The script compares the following voxel sizes:

```text
0.005 m = 5 mm
0.010 m = 10 mm
0.020 m = 20 mm
0.050 m = 50 mm
```

The Open3D call is:

```python
down = pcd.voxel_down_sample(0.01)
```

This experiment selects `0.01 m`. It substantially reduces the number of points while preserving the desk edge and the outlines of major objects.

Recorded result:

```text
Complete point cloud: 237,041 points
10 mm downsampled cloud: 23,553 points
Depth range: 0.7358–3.6782 m
Median depth: 0.9348 m
```

## 7. Coordinate-transform experiment

A three-dimensional rigid transformation uses a 4×4 homogeneous matrix:

```text
T = [ R  t ]
    [ 0  1 ]
```

Here, `R` is a 3×3 rotation matrix and `t` is a three-dimensional translation vector. The corresponding Open3D calls are:

```python
transformed.transform(T)
restored.transform(np.linalg.inv(T))
```

The transformed cloud was restored with the inverse of `T`, producing:

```text
Maximum error: 1.09e-15 m
Mean error: 2.23e-16 m
```

These values are close to double-precision floating-point accuracy, supporting that the transform and inverse-transform relationship was implemented correctly.

## 8. Output files

The program generates the following files in `results/a3`:

| File | Meaning |
|---|---|
| `single_frame_full.ply` | Complete single-frame coloured point cloud |
| `single_frame_voxel_10mm.ply` | Point cloud downsampled with 1 cm voxels |
| `transformed.ply` | Point cloud after the artificial rotation and translation |
| `restored.ply` | Point cloud restored with the inverse transformation |

These `.ply` files can be reopened with Open3D, CloudCompare or MeshLab.

## 9. Common problems

### The point cloud is five times too large or too small

Check whether `depth_scale` was mistakenly left at Open3D's default value of 1000. This project requires 5000.

### The point cloud has no colour

Check that `convert_rgb_to_intensity=False`, and confirm that the colour and depth images have the same dimensions and are already registered.

### The point cloud appears upside down

First determine whether this is a viewing-direction issue or a coordinate-data problem. The optical camera coordinate system uses +Y downwards. Do not alter the original coordinates used by SLAM only to make the preview appear upright.

### The window disappears after double-clicking the Python file

Run the script from PowerShell rather than double-clicking it. This keeps error messages and statistics visible.
