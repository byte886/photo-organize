# 照片整理标准工作流（六步法）

> 从海量照片备份中抽取、分类、整理家庭照片的完整 SOP。SKILL.md 只做路由与红线，本篇放全部命令与决策规则。
> 路径示例一律 `/path/to/...`，实际执行时换成项目里的真实目录。

---

## 第一步：目录侦察

摸清源目录结构、图片数量、年份分布、可疑子目录。

```bash
ls -la /path/to/source/                       # 顶层结构
# 各子目录图片数
for d in /path/to/source/*/; do
  cnt=$(find "$d" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.gif" \) 2>/dev/null | wc -l | tr -d ' ')
  [ "$cnt" -gt 0 ] && echo "$(basename "$d"): $cnt 张"
done
# 年份分布（从文件名时间戳解析，unix 10位/13位）
ls /path/to/photos/ | grep -oE '^[0-9]{10}' | while read ts; do [ ${#ts} -eq 10 ] && date -r "$ts" +%Y 2>/dev/null; done | sort | uniq -c | sort -rn
```

**关键判断**：目录名含"家人/家庭/相册/胶卷/Camera" → 高概率家庭照片；含"工作/文档/截图/微信" → 混合需筛选；文件名 `时间戳_IMG_编号.JPG` → 手机导出；`mmexport<13位>.jpg` → 微信导出。

---

## 第二步：人脸检测预筛选

用 face-detect skill 对候选目录批量检测，按人脸数分组（face_detect 输出：路径<TAB>人脸数）。

```bash
/tmp/face_detect /path/to/candidate > /tmp/face_result.txt 2>/dev/null
awk -F'\t' '$2==0 {print $1}' /tmp/face_result.txt > /tmp/noface.txt    # 无人脸
awk -F'\t' '$2==1 {print $1}' /tmp/face_result.txt > /tmp/single.txt    # 单人
awk -F'\t' '$2>=2 {print $1}' /tmp/face_result.txt > /tmp/group.txt     # 多人合照
```

**预分类决策**：人脸数 ≥2 → 大概率合照（抽样确认）；=1 → 单人照，需联系表判断是谁；=0 → 混合（风景/画作/文档/背影），需联系表逐张判断。

---

## 第三步：联系表生成与逐批核验

用脚本 `scripts/contact_sheet.py`（列表文件每行「显示名<TAB>完整路径」，# 开头注释）。

```bash
SKILL="$HOME/Doubao/skills/photo-organize"
# 准备列表（-v d 必须与第二步 face_detect 输入目录一致，$1 只是文件名不含目录）
awk -F'\t' -v d="/path/to/candidate" '$2==0 {print $1"\t"d"/"$1}' /tmp/face_result.txt > /tmp/noface_list.txt
split -l 60 /tmp/noface_list.txt /tmp/batch_          # 每批 60 张
python3 "$SKILL/scripts/contact_sheet.py" /tmp/batch_aa /tmp/contact_aa.png   # 默认4列；--cols 调列数
```

**每批 50-60 张**为宜，太多缩略图太小看不清。用 Read 查看联系表，逐张判断分类。

---

## 第四步：按分类移动文件

```bash
DST="/path/to/家庭相册"
mkdir -p "$DST/孩子成长" "$DST/合照" "$DST/父亲" "$DST/母亲" "$DST/祖辈" "$DST/亲戚" "$DST/儿童画作" "$DST/风景/自然风光" "$DST/风景/城市景观" "$DST/其他待确认"
# 批量移动（按文件名列表）
while IFS=$'\t' read -r name path; do mv "$path" "$DST/合照/" 2>/dev/null; done < /tmp/group_move.txt
```

**分类决策规则**：
- 多人（≥2人脸）且家庭成员 → 合照
- 单人是孩子 → 孩子成长
- 单人成年女性/男性 → 母亲/父亲
- 单人是老人 → 祖辈（需区分）
- 儿童手绘/画作/手工 → 儿童画作
- 纯风景无人物 → 风景/自然风光 或 城市景观
- 文档/截图/证件/工作 → 排除（不放家庭相册）
- 背影/侧脸无法判断 → 其他待确认

---

## 第五步：两级去重（MD5 + dHash）

用脚本 `scripts/dedup_photos.py`。重复文件先移到 `_重复待确认`，用户确认后再删。

### 5.1 精确去重（MD5）

同一张照片的不同命名副本。脚本先按大小分组再算 MD5，每组保留路径最短者，默认只报告：

```bash
python3 "$SKILL/scripts/dedup_photos.py" md5 "/path/to/家庭相册"            # dry-run
python3 "$SKILL/scripts/dedup_photos.py" md5 "/path/to/家庭相册" --apply    # 确认后移入 _重复待确认/
```

### 5.2 视觉相似去重（dHash）

检测连拍、轻微裁剪、重编码等 MD5 不同但视觉几乎相同的图。脚本把每张缩成 9×8 灰度算 64 位差异哈希，两两算汉明距离，输出 ≤ 阈值（默认 5）的相似对：

```bash
python3 "$SKILL/scripts/dedup_photos.py" dhash "/path/to/家庭相册" --threshold 5
```

**距离分级处理策略**：

| 汉明距离 | 含义 | 处理方式 |
|----------|------|----------|
| 0 | 视觉完全相同（重编码/不同格式） | 同目录同 IMG 编号→自动保留文件名短的；跨目录/不同编号→生成联系表确认 |
| 1-2 | 几乎一样（连拍极近） | 生成联系表，用户决定保留哪张 |
| 3-5 | 较相似（连拍有表情/角度差异） | 暂保留，列出目录分布，后续按需筛选 |
| >5 | 有明显差异 | 保留，不处理 |

### 5.3 生成确认联系表

复用 `contact_sheet.py --cols 2`：把每对两张图按「名<TAB>路径」连续写进列表（每对两行），2 列生成左右并排对比表：

```bash
python3 "$SKILL/scripts/contact_sheet.py" pairs_list.txt /tmp/dup_confirm.png --cols 2 --tw 400 --th 300
```

用户告知每对删左/删右/都保留后，按指示移到 `_重复待确认`。

---

## 第六步：完整性验证

```bash
echo "源: $(find /path/to/source -type f | wc -l | tr -d ' ')"
echo "目标: $(find "$DST" -type f | wc -l | tr -d ' ')"
for d in "$DST"/*/; do echo "$(basename "$d"): $(find "$d" -type f | wc -l | tr -d ' ') 张"; done
du -sh "$DST"
```

---

## 家庭相册推荐目录结构

```
家庭相册/
├── 孩子成长/          # 孩子单人照（按年份可再细分）
├── 合照/              # 家庭成员多人合影
├── 父亲/              # 父亲单人照
├── 母亲/              # 母亲单人照
├── 祖辈/              # 祖辈单人照
├── 亲戚/              # 其他亲戚
├── 儿童画作/          # 孩子的手绘、手工、美术作品
├── 风景/
│   ├── 自然风光/      # 山水、海景、公园
│   └── 城市景观/      # 建筑、街景、室内
├── _重复待确认/       # 去重隔离区，确认后再删
└── 其他待确认/        # 无法判断的，后续人工处理
```

---

## 注意事项（硬红线）

1. **先复制后移动**：整理重要照片先复制到暂存目录，确认无误再从源目录删除。
2. **暂存目录命名**：明确标记"待确认"（如 `<项目>_照片待确认/`）。
3. **人脸检测是辅助**：侧脸/背影/远距离会漏检，无人脸组仍需联系表确认。
4. **文档截图排除**：家庭相册只放照片，文档/截图/证件应排除或单独归档。
5. **大目录分批**：>1000 张的目录，联系表每批 50-60 张，分多轮处理。
6. **保留来源信息**：暂存目录下按来源建子目录（如 `iphone_相机胶卷/`、`<手机型号>_家人/`），便于追溯。
7. **uchg 标志**：mv 报 Operation not permitted 时用 `sudo chflags nouchg 文件` 解除。
8. **去重不直接删**：两级去重都先隔离到 `_重复待确认`，人工确认后再清，避免误删。
