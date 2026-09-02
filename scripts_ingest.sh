#!/bin/zsh
# 资产整理与盘点脚本 — Microduck 复刻资料库
set -u
cd /Users/copizzah/Desktop/work/robot/Microduck

echo "== git-lfs =="
git lfs version || { echo "LFS MISSING"; exit 1; }

for r in 02_cad/replica_assembly/microduck-replica \
         02_cad/replica_assembly/microduck-hardware-replica \
         02_cad/openduckmini/Open_Duck_Mini \
         01_official/microduck_rl \
         02_cad/diy_printable/microduck-diy; do
  cd /Users/copizzah/Desktop/work/robot/Microduck/$r
  n=$(git lfs ls-files 2>/dev/null | wc -l | tr -d ' ')
  echo "LFS $r: $n files"
  if [ "$n" != "0" ]; then git lfs pull 2>&1 | tail -1; fi
done

cd /Users/copizzah/Desktop/work/robot/Microduck
echo "== upstream STL =="
rsync -a 01_official/microduck_rl/src/mjlab_microduck/robot/microduck/assets/ 02_cad/upstream_stl/
ls 02_cad/upstream_stl | wc -l
du -sh 02_cad/upstream_stl

echo "== INVENTORY by extension =="
find 01_official 02_cad 08_refs -type f -not -path '*/.git/*' | awk -F. '{print tolower($NF)}' | sort | uniq -c | sort -rn | head -30

echo "== per-repo file counts =="
for d in 01_official/* 02_cad/*/* 08_refs/*; do
  [ -d "$d" ] && echo "$(find "$d" -type f -not -path '*/.git/*' | wc -l | tr -d ' ')  $d"
done

echo "== pointer-file check (LFS未拉取则输出内容为指针) =="
grep -rl "oid sha256" 02_cad/upstream_stl 2>/dev/null | head -3 || true
echo DONE
