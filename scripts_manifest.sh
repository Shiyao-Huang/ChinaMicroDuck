#!/bin/zsh
# 生成全库 SHA256 MANIFEST（排除构建产物/虚拟环境/训练中间物/git 内部）
cd /Users/copizzah/Desktop/work/robot/Microduck
find . -type f \
  -not -path '*/.git/*' \
  -not -path '*/target/*' \
  -not -path '*/.venv/*' \
  -not -path '*/venv/*' \
  -not -path '*/runs/*' \
  -not -path '*/checkpoints/*' \
  -not -path '*/captures/*' \
  -not -path '*/clips/*' \
  -not -path '*/tb/*' \
  -not -path '*/node_modules/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/upstream/*' \
  -not -name '.DS_Store' \
  -not -name '*.pyc' \
  -size -100M \
  | sed 's|^\./||' | sort \
  | while read f; do
      printf '%s  %s\n' "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$f"
    done > MANIFEST.sha256
wc -l MANIFEST.sha256
echo MANIFEST_DONE
