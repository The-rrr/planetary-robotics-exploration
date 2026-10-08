from pathlib import Path
import argparse
import json
import hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import open3d as o3d

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='Render figures from saved September experiment outputs.')
parser.add_argument('--map', type=Path, required=True, help='Path to the saved full slam_cloud.ply')
args = parser.parse_args()
figure_dir = ROOT / 'figures'
figure_dir.mkdir(exist_ok=True)
trajectory_path = ROOT / 'evidence/slam_poses.txt'
trajectory = np.loadtxt(trajectory_path)
assert trajectory.shape[1] == 8 and np.isfinite(trajectory).all()
assert (np.diff(trajectory[:, 0]) > 0).all()
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':11})
fig, ax = plt.subplots(figsize=(9, 6))
p = trajectory[:, 1:4]
ax.plot(p[:, 0], p[:, 1], color='#176b82', linewidth=1.7)
ax.scatter(p[0, 0], p[0, 1], c='#1b8556', marker='o', s=65, label='Start', zorder=3)
ax.scatter(p[-1, 0], p[-1, 1], c='#bf5037', marker='X', s=75, label='End', zorder=3)
ax.set(xlabel='Map x (m)', ylabel='Map y (m)', title='TUM freiburg1_desk | recorded optimised trajectory')
ax.set_aspect('equal', adjustable='datalim')
ax.grid(alpha=.2)
ax.legend(frameon=False)
fig.text(.5,.025,'548 optimised poses | exported map frame | not a ground-truth error plot',ha='center',fontsize=9,color='#555555')
fig.tight_layout(rect=[0,.045,1,1])
fig.savefig(figure_dir/'trajectory.png',dpi=160)
fig.savefig(figure_dir/'trajectory.svg')
plt.close(fig)
cloud = o3d.io.read_point_cloud(str(args.map))
xyz, rgb = np.asarray(cloud.points), np.asarray(cloud.colors)
assert len(xyz) == 1031428 and np.isfinite(xyz).all()
indices = np.linspace(0, len(xyz)-1, min(30000,len(xyz)), dtype=int)
points, colors = xyz[indices], rgb[indices]
fig = plt.figure(figsize=(10,7))
ax = fig.add_subplot(111, projection='3d')
ax.scatter(points[:,0],points[:,1],points[:,2],c=colors,s=.6,depthshade=False,rasterized=True)
ax.set(xlabel='Map x (m)',ylabel='Map y (m)',zlabel='Map z (m)',title='Recorded RGB-D map | sampled indoor scene')
ax.set_box_aspect(np.ptp(points,axis=0))
ax.view_init(elev=-65,azim=-60)
fig.text(.5,.025,'30,000-point deterministic preview from 1,031,428 points | TUM RGB-D benchmark',ha='center',fontsize=9,color='#555555')
fig.tight_layout(rect=[0,.045,1,1])
fig.savefig(figure_dir/'map-preview.png',dpi=160)
fig.savefig(figure_dir/'map-preview.svg')
plt.close(fig)
meta = {'render_date':'2026-10-09','source_run':'A4-20260930-desk-full-03','trajectory_sha256':hashlib.sha256(trajectory_path.read_bytes()).hexdigest(),'full_map_sha256':hashlib.sha256(args.map.read_bytes()).hexdigest(),'full_map_points':len(xyz),'preview_points':len(indices),'sampling':'evenly spaced original point indices, including first and last','trajectory_frame':'exported map frame; no alignment applied for this plot','dataset':'TUM RGB-D freiburg1_desk','note':'Figures rendered from saved outputs; no new SLAM run.'}
(ROOT/'evidence/figure-provenance.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
print('Rendered trajectory and map preview; source hashes saved.')
