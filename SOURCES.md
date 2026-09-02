# SOURCES · 各仓来源与钉定版本

> 归档日期 2026-09-02。各仓保留 `.git`，可 `git pull --ff-only` 追上游；
> 更新后请重跑 `zsh scripts_manifest.sh` 并刷新本表。

| 本库路径 | 上游 | 钉定 commit | 上游最后提交 |
|---|---|---|---|
| 01_official/microduck | https://github.com/pollen-robotics/microduck | 9f7eaad1008f | 2026-09-01 |
| 01_official/microduck_rl | https://github.com/pollen-robotics/microduck_rl | 5946fd9cdbc5 | 2026-09-01 |
| 01_official/microduck-gst-plugins | https://github.com/pollen-robotics/microduck-gst-plugins | a9a839f274fb | 2026-08-25 |
| 02_cad/replica_assembly/microduck-replica | https://github.com/fanhao375/microduck-replica | d60cd2e89b0e | 2026-09-02 |
| 02_cad/replica_assembly/microduck-hardware-replica | https://github.com/lingzolabs/microduck-hardware-replica | c453c78f5f8e | 2026-09-02 |
| 02_cad/replica_assembly/open-microduck | https://github.com/SaberOnGo/open-microduck | 9a959b6881bf | 2026-08-31 |
| 02_cad/diy_printable/microduck-diy | https://github.com/ScrapMeta/microduck-diy | 8fa142f55487 | 2026-08-31 |
| 02_cad/openduckmini/Open_Duck_Mini | https://github.com/apirrone/Open_Duck_Mini | b23317a485b3 | 2026-01-31 |
| 02_cad/openduckmini/Open_Duck_Mini_Runtime | https://github.com/apirrone/Open_Duck_Mini_Runtime | 32037347dc43 | 2025-06-24 |
| 08_refs/awesome-microduck | https://github.com/joeynyc/awesome-microduck | 6298c095fe68 | 2026-09-02 |

## 非 git 来源

| 资产 | 来源 | 校验 |
|---|---|---|
| 9× ONNX + manifest.json | hf-mirror.com/pollen-robotics/microduck-policies @ commit 41d5508e | SHA256 全录于 MANIFEST.sha256 |
| press-kit.zip | pollen-robotics.com/assets/microduck/press/microduck-press-kit.zip | 08_refs/press-kit/ |
| microduck-lab-apple | codeload.github.com/jonathanhawkins/microduck-lab @ main 快照 | 05_sim/（无 .git，快照式） |

## 恢复脚本

```bash
bash scripts_ingest.sh   # 重建 upstream_stl 提取 + 盘点（克隆已存在则跳过失败项）
# 完整重建：按上表 git clone 到对应路径后运行上述脚本
```
