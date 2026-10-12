---
type: workflow
name: photo-organize
description: "家庭/个人照片批量整理与相册归档工作流：目录侦察、人脸检测预分组、联系表逐批核验、按人物/场景分类移动、MD5 精确+dHash 感知两级去重、整理后完整性校验。当用户要整理或归档海量照片备份（手机导出、微信备份、硬盘转存）、清理重复或连拍、把散乱照片归入结构化家庭相册、按人脸分组时使用。随附 contact_sheet.py 与 dedup_photos.py 脚本。"
compatibility: "仅在 macOS(Darwin) 实测；执行前先 `uname -s` 判平台，非 macOS 停步告知不硬跑。依赖 Python3+Pillow、face-detect 技能、macOS 系统工具 find/du/md5/cp/mv。"
---

# Photo Organize（照片批量整理工作流）

## 平台适用（执行前先读）
- 当前**仅 macOS（Darwin）实测可用**。动手前 `uname -s` 返回 `Darwin` 才继续；**Windows/Linux 未适配，遇到就停下告知"需先做平台适配"，不要用想当然的等价命令硬跑**。
- 将来补齐其他平台后仍保留"先判平台 → 按平台分流"结构，命令与路径分开标注验证状态。

> 一句话：从海量照片备份里，按"人脸预筛 → 联系表人工核验 → 分类 → 两级去重 → 完整性校验"抽出并整理成结构化家庭相册。全部命令与决策规则见 [references/workflow.md](references/workflow.md)。

## 适用场景
- 从手机备份（iPhone 导出、安卓 DCIM、微信备份）抽取家庭照片
- 把散乱照片按人物/场景归入结构化相册目录
- 整理前先做人脸检测预筛选，减少逐张人工判断量
- 去重（精确副本 + 连拍/重编码的视觉相似）、完整性验证

## 依赖
- **face-detect 技能**：本地人脸检测（必须先加载）
- Python3 + Pillow（`python3 -c "import PIL"` 验证，缺则 `pip3 install Pillow`）
- macOS 系统工具：find/du/md5/cp/mv
- 本技能脚本：`scripts/contact_sheet.py`（联系表）、`scripts/dedup_photos.py`（两级去重）

## 六步流程（每步怎么做见 workflow.md）

| 步 | 做什么 | 关键产物 |
|----|--------|---------|
| 1 目录侦察 | 摸源目录结构/数量/年份分布/可疑子目录 | 候选目录清单 |
| 2 人脸预筛选 | face-detect 批量检测，按人脸数 0/1/≥2 分组 | noface/single/group 三份列表 |
| 3 联系表核验 | contact_sheet.py 每批 50-60 张生成网格图，Read 逐张判断 | 分类判断 |
| 4 分类移动 | 按人物/场景规则 mv 到目标相册目录 | 分类好的照片 |
| 5 两级去重 | dedup_photos.py：MD5 精确 + dHash 感知相似，先隔离 `_重复待确认` | 去重清单 |
| 6 完整性校验 | 源 vs 目标文件数/各分类数量/总大小 | 校验结论 |

## 脚本清单

| 脚本 | 作用 | 关键用法 |
|------|------|----------|
| `scripts/contact_sheet.py` | 列表→缩略图网格联系表 | `contact_sheet.py <列表> <输出.png> [--cols 4]`，列表每行「名<TAB>路径」 |
| `scripts/dedup_photos.py md5` | 精确副本去重 | `md5 <相册> [--apply]`，默认 dry-run，--apply 才移入 `_重复待确认` |
| `scripts/dedup_photos.py dhash` | 视觉相似对排查 | `dhash <相册> [--threshold 5]`，只报告相似对供人工裁决 |

## 硬红线（详见 workflow.md 注意事项）
- **先复制后移动**：重要照片先复制到"待确认"暂存目录，确认无误再删源。
- **去重不直接删**：两级去重都先隔离到 `_重复待确认`，人工确认后再清。
- **人脸检测是辅助**：侧脸/背影/远距离会漏检，无人脸组仍需联系表确认。
- **文档截图排除**：家庭相册只放照片，文档/截图/证件排除或单独归档。
- **大目录分批**：>1000 张每批 50-60 张，分多轮。
- **保留来源**：暂存目录按来源建子目录便于追溯。
- 分类决策规则、推荐相册目录结构、dHash 距离分级表、各步完整命令 → [references/workflow.md](references/workflow.md)
