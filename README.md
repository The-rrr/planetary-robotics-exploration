# Planetary Robotics Exploration

**From exploration destinations to navigation requirements, RGB-D SLAM experiments and cooperative robotics ideas.**

I am a first-year Earth and Planetary Science student developing my understanding of robotic perception and autonomous exploration. This portfolio connects my comparative study of the Moon, Mars and Europa with a guided practical project in localisation and mapping.

My starting question is: **How do scientific goals and environmental constraints shape the navigation capabilities an exploration robot needs?** The destination study motivates the technical work; the initial indoor RGB-D benchmark establishes basic data handling and mapping skills before attempting more demanding environments.

## Start here

1. [Moon, Mars and Europa: destination comparison](reports/01-destination-comparison.md)
2. [From underwater localisation to cooperative exploration](reports/02-cooperative-exploration-concept.md)
3. [Development process and lessons learned](docs/development-journal.md)
4. [Recorded RGB-D SLAM results](reports/03-slam-experiment.md)
5. [Reproduction guide](docs/reproduce.md)

## Current progress

| Component | Status | Evidence |
|---|---|---|
| Destination comparison | Study notes consolidated into a report | Moon, Mars and Europa comparison |
| RGB-D data inspection and association | Completed | Data notes and inspection script |
| Single-frame reconstruction | Completed | Open3D reconstruction, downsampling and transform experiments |
| RGB-D odometry and RTAB-Map SLAM | Completed on an indoor benchmark | Trajectories, loop-closure audit and evaluation |
| Ice-world analogue, visual degradation and terrain labels | Planned | Next steps in the journal |
| AUV localisation combined with swarm coordination principles | Research concept | Questions and proposed experiments; not implemented |

## Recorded experiment

The final recorded run, `A4-20260930-desk-full-03`, used **TUM freiburg1_desk**. It processed **573 RGB-D pairs**, stored **548 optimised poses**, and exported **1,031,428 coloured map points**. The database audit found **124 unique global loop-closure constraints**, including 19 spanning at least 30 node IDs.

The saved evaluation reports an optimised absolute position error RMSE of **0.025180 m**, using SE(3) rigid alignment to motion-capture ground truth after estimation had stopped. This is one indoor dataset result; it does not demonstrate planetary, underwater, multi-robot or flight performance. The odometry and optimised trajectories contain different numbers of poses, so their reported errors should not be presented as a controlled percentage improvement.

![Recorded optimised camera trajectory](figures/trajectory.svg)

![Sampled view of the recorded coloured map](figures/map-preview.svg)

The map image displays a deterministic sample of the saved map, not every point. Figure provenance and reproduction commands are in [the experiment report](reports/03-slam-experiment.md).

## Learning approach and attribution

This is a learning portfolio using existing tools, official documentation and AI-assisted coding/debugging. RTAB-Map supplies the odometry and SLAM algorithms; Open3D supplies point-cloud processing. The work here focuses on connecting the workflow, understanding geometry and units, recording experiments and checking the resulting evidence. It does not claim a newly invented SLAM algorithm or independently implemented swarm system.

The reports were consolidated on **9 October 2026** from earlier study conversations and local experiment records. The included experiment outputs were generated in September; the portfolio figures were rendered from those saved outputs on 9 October. A complete new ROS run was not performed for this publication.

See [sources and data attribution](docs/sources-and-attribution.md). Raw datasets, the large database, full-resolution map, machine-specific setup scripts and private local paths are omitted from this public snapshot.

## 中文说明

这是一条连贯的学习路线：月球、火星和木卫二的探索目的地分析，引出机器人定位与建图需求；随后在公开室内数据上完成 RGB-D 点云和 SLAM 基础实践，再思考水下 AUV 定位与无人机集群协同原则的结合。已完成实验与未来构想分别标明。实际实验仍使用地球室内数据，不能视为木卫二、水下或多机器人系统的验证。
