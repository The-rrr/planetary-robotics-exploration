# Development Process and Lessons Learned

This journal condenses September 2026 local records into a public account on 9 October 2026. It describes the sequence of learning and debugging rather than suggesting that all stages were independently designed from scratch.

## From the science question to an accessible experiment

Comparing the Moon, Mars and Europa prompted an interest in navigation in unfamiliar environments. I chose an indoor public RGB-D benchmark to establish basic data and geometry skills before attempting an ice-world analogue. The Europa connection is motivation, not the source of the experimental data.

## A1: Establishing the environment — 22 September

The project used Ubuntu 24.04 through WSL, ROS 2 Jazzy, RTAB-Map 0.23.7 and Open3D 0.19.0. Basic ROS communication, point-cloud processing and the installed SLAM tools were checked. Gazebo Harmonic's simple example world and clock bridge were also checked. This was environment verification, not a completed rover simulation.

## A2: Understanding the RGB-D data

The `freiburg1_xyz` and `freiburg1_desk` sequences were inspected for timestamps, missing files, image dimensions and valid depth. RGB and depth were paired using a one-to-one greedy association with a 20 ms tolerance. This produced 792 pairs for xyz and 573 for desk. I recorded why a raw depth value must be divided by 5000 to obtain metres and why an invalid zero is not a point at the camera origin.

## A3: Reconstructing one frame

Open3D was used to reconstruct coloured points from RGB-D images and camera intrinsics. I compared voxel sizes, checked the optical coordinate convention, applied a rigid transform and then its inverse. The saved local record reports 237,041 full-resolution points and 23,553 at a 1 cm voxel size; the inverse-transform error was near floating-point precision. These checks concern geometry, not SLAM trajectory accuracy.

## A4: Connecting odometry, loop closure and map export — 30 September

The replay node publishes images and calibration, the RGB-D odometry node estimates motion, and RTAB-Map detects revisits and optimises the pose graph. The final desk run generated the trajectory, coloured map and database. Ground truth was reserved for evaluation after the estimator processes exited.

Debugging exposed three useful lessons:

- An empty YAML parameter overrode the intended database path. Parameter precedence must be checked against actual runtime behaviour.
- An early run with the default-near 1 Hz backend detection rate did not demonstrate a global loop closure. A complete replay is not automatically evidence of loop closure.
- Publishing raw TUM depth as millimetre-semantic `16UC1` produced a scale error of about five. Converting the depth to metre-semantic `32FC1` corrected the final run. The erroneous map was not accepted as a final result.

The final audit counts unique constraints instead of double-counting the database's bidirectional link rows. The included figures were made from the recorded final trajectory and map; they are not a new experiment.

## What remains to be done

Controlled low-texture/depth-loss experiments, matched-timestamp comparisons, RPE evaluation, an explicitly labelled ice-world analogue and terrain annotation are future steps. Multi-sensor fusion, underwater sensing, cooperative mapping and swarm coordination remain research ideas. No hardware rover, AUV or multi-drone system has been validated.

See [the experiment report](../reports/03-slam-experiment.md) for evidence and [the reproduction guide](reproduce.md) for the selected scripts.
