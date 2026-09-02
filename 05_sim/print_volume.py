#!/usr/bin/env python3
"""3D 打印体积估算：上游 47 STL → 每件体积(cm³)、PLA克重 → 打印报价依据。
方案 A 单台打印材料成本（自印按料钱，代工按市场价 2-4 元/cm³）。"""
import glob, json
import trimesh
import numpy as np

files = sorted(glob.glob('/Users/copizzah/Desktop/work/robot/Microduck/02_cad/upstream_stl/*.stl'))
rows = []
total_cm3 = 0.0
for f in files:
    m = trimesh.load(f, process=True)
    vol_m3 = abs(float(m.volume))
    vol_cm3 = vol_m3 * 1e6  # MJCF 单位 m
    # 每件的整机用量（从装配体引用统计, 单位:件）—— 一次性简化：多数×1，腿/髋类×2
    name = f.split('/')[-1].replace('.stl','')
    q = 2 if any(k in name for k in ['ankle','hip','leg','upper','neck','bearing_roll','foot']) else 1
    rows.append({'file': name, 'cm3': round(vol_cm3,2), 'qty': q, 'total_cm3': round(vol_cm3*q,2)})
    total_cm3 += vol_cm3 * q

pla_g = total_cm3 * 1.24  # PLA 密度 1.24 g/cm³
tpu_extra = 20  # jaw_soft 等柔性件粗略 20g
out = dict(
    files=len(files), total_cm3=round(total_cm3,1),
    pla_grams=round(pla_g,0), tpu_grams=tpu_extra,
    estimate=dict(
        material_only_cny=round(total_cm3*0.08,0),          # 自印料钱 ~0.08元/g PLA
        outsource_low_cny=round(total_cm3*2.5,0),           # 代工 2.5元/cm³ 起（PLA FDM）
        outsource_high_cny=round(total_cm3*4.0,0),          # 代工 4元/cm³（含后处理）
    )
)
json.dump({'rows': rows, 'summary': out}, open('/Users/copizzah/Desktop/work/robot/Microduck/07_build_log/print_volume_estimate.json','w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
