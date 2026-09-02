#!/bin/zsh
# 生成全库 SHA256 MANIFEST（排除 .git / venv）
cd /Users/copizzah/Desktop/work/robot/Microduck
find . -type f \
  -not -path '*/.git/*' \
  -not -path '*/05_sim/.venv/*' \
  -not -name '.DS_Store' \
  | sed 's|^\\./||' | sort \
  | while read f; do
      printf '%s  %s\n' "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$f"
    done > MANIFEST.sha256
wc -l MANIFEST.sha256
head -5 MANIFEST.sha256
echo MANIFEST_DONE
