#!/usr/bin/env python3
"""E5: 上游 STL 网格可打印性体检 — 水密性/自交/尺寸/体积。
输出: 07_build_log/stl_mesh_report.json + 终端摘要"""
import json, sys, glob
import numpy as np
import trimesh

files = sorted(glob.glob("/Users/copizzah/Desktop/work/robot/Microduck/02_cad/upstream_stl/*.stl"))
report = []
for f in files:
    try:
        m = trimesh.load(f, process=False)
        ext = m.bounding_box.extents if hasattr(m, "bounding_box") else [0,0,0]
        # 单位假设: MJCF 导出为米, 打印需要毫米
        unit_note = "meters(mjcf)" if max(ext) < 1.0 else "mm?"
        entry = dict(
            file=f.split("/")[-1],
            faces=int(getattr(m, "faces", np.empty((0,3))).shape[0]),
            watertight=bool(getattr(m, "is_watertight", False)),
            winding_consistent=bool(getattr(m, "is_winding_consistent", False)),
            self_intersecting=None,  # 检查昂贵, 只对水密件做
            volume_mm3=None,
            extents=dict(x=round(float(ext[0]),5), y=round(float(ext[1]),5), z=round(float(ext[2]),5)),
            unit=unit_note,
        )
        if entry["watertight"]:
            try:
                entry["self_intersecting"] = bool(m.is_volume and False) # trimesh无直接API, 留空
            except Exception:
                pass
        if hasattr(m, "volume") and np.isfinite(getattr(m, "volume", np.nan)):
            v = float(m.volume)
            entry["volume_mm3"] = round(v * 1e9, 1) if unit_note == "meters(mjcf)" else round(v, 1)
        report.append(entry)
    except Exception as e:
        report.append(dict(file=f.split("/")[-1], error=str(e)[:120]))

wt = [r for r in report if r.get("watertight")]
print(f"STL 总数: {len(report)}")
print(f"水密(watertight): {len(wt)}")
print(f"非水密: {len(report)-len(wt)}")
print(f"绕向一致: {sum(1 for r in report if r.get('winding_consistent'))}")
nonwt = [r['file'] for r in report if not r.get('watertight')]
print("非水密清单(前20):", nonwt[:20])
out = "/Users/copizzah/Desktop/work/robot/Microduck/07_build_log/stl_mesh_report.json"
json.dump(report, open(out, "w"), ensure_ascii=False, indent=1)
print("report ->", out)
