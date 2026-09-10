---
name: photo-organize
description: "家庭/个人照片批量整理工作流。覆盖目录侦察、人脸检测预筛选、联系表生成与逐批核验、按内容分类移动、重复检测、完整性验证。适用于从海量备份（手机导出、微信备份、硬盘转存）中抽取家庭照片并归入结构化相册目录。"
compatibility: "仅在 macOS(Darwin) 实测可用；Windows/Linux 未适配。执行前先判平台(uname -s 返回 Darwin)，非 macOS 停止并告知需另行适配、不硬跑；将来补齐 Windows 后仍按平台分流并分别标注验证状态。本机依赖：Python3+Pillow、Swift(face-detect 子技能)，依赖 face-detect 技能。"
---

# Photo Organize（照片批量整理工作流）

## 平台适用（执行前先读）
- 本技能当前**仅在 macOS（Darwin）实测可用**，命令、路径、代理端口与系统原生能力均按 Mac。
- 动手前先判平台：`uname -s` 返回 `Darwin` 才走本技能流程；**Windows/Linux 未适配，遇到就停下告知用户“需先做该平台适配”，不要用想当然的等价命令硬跑**。
- 以后补齐 Windows 后也必须保留“先判平台 → 按平台分流”的结构：mac/Windows 的命令与路径分开写、各自标注是否已验证。

从海量照片备份中抽取、分类、整理家庭照片的标准化流程。

## 适用场景

- 从手机备份（iPhone 导出、华为 DCIM、微信备份）中抽取家庭照片
- 把散乱照片按人物/场景归入结构化相册目录
- 整理前先做人脸检测预筛选，减少逐张人工判断量
- 去重、完整性验证

## 依赖

- **face-detect skill**：本地人脸检测（必须先加载）
- Python3 + Pillow：联系表生成
- macOS 系统工具：find/du/md5/cp/mv

## 标准工作流（六步法）

### 第一步：目录侦察

摸清源目录结构、图片数量、年份分布、可疑子目录。

```bash
# 顶层结构
ls -la /path/to/source/

# 各子目录图片数
for d in /path/to/source/*/; do
  cnt=$(find "$d" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.heic" -o -iname "*.gif" \) 2>/dev/null | wc -l | tr -d ' ')
  [ "$cnt" -gt 0 ] && echo "$(basename "$d"): $cnt 张"
done

# 年份分布（从文件名时间戳解析，unix 10位/13位）
ls /path/to/photos/ | grep -oE '^[0-9]{10}' | while read ts; do
  [ ${#ts} -eq 10 ] && date -r "$ts" +%Y 2>/dev/null
done | sort | uniq -c | sort -rn
```

**关键判断**：
- 目录名含"家人/家庭/相册/胶卷/Camera" → 高概率家庭照片
- 目录名含"工作/文档/截图/微信" → 混合内容，需筛选
- 文件名格式 `时间戳_IMG_编号.JPG` → 手机导出，时间戳可解析年份
- 文件名 `mmexport<13位>.jpg` → 微信导出

### 第二步：人脸检测预筛选

用 face-detect skill 对候选目录批量检测，按人脸数分组。

```bash
/tmp/face_detect /path/to/candidate > /tmp/face_result.txt 2>/dev/null

# 分组
awk -F'\t' '$2==0 {print $1}' /tmp/face_result.txt > /tmp/noface.txt    # 无人脸
awk -F'\t' '$2==1 {print $1}' /tmp/face_result.txt > /tmp/single.txt    # 单人
awk -F'\t' '$2>=2 {print $1}' /tmp/face_result.txt > /tmp/group.txt     # 多人合照
```

**预分类决策**：
- 人脸数 >=2 → 大概率是合照，可直接归"合照"（抽样确认）
- 人脸数 =1 → 单人照，需联系表判断是谁（爸爸/妈妈/孩子/老人）
- 人脸数 =0 → 混合（风景/画作/文档/背影），需联系表逐张判断

### 第三步：联系表生成与逐批核验

生成缩略图网格联系表，逐批人工确认分类。

**联系表脚本**（保存为 /tmp/contact.py）：

```python
import sys
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) < 3:
    print("Usage: contact.py <list_file> <output.png>")
    sys.exit(1)

items = []
with open(sys.argv[1]) as f:
    for line in f:
        line = line.strip()
        if not line: continue
        parts = line.split('\t')
        if len(parts) >= 2:
            items.append((parts[0], parts[1]))

cols = 4
rows = (len(items) + cols - 1) // cols
tw, th, lh, pad = 360, 270, 30, 4
canvas = Image.new('RGB', (cols*(tw+pad)+pad, rows*(th+lh+pad)+pad), (240,240,240))
draw = ImageDraw.Draw(canvas)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
except:
    font = ImageFont.load_default()

for idx, (name, path) in enumerate(items):
    col, row = idx % cols, idx // cols
    x = pad + col*(tw+pad)
    y = pad + row*(th+lh+pad)
    try:
        im = Image.open(path)
        im.thumbnail((tw, th))
        canvas.paste(im, (x+(tw-im.width)//2, y+(th-im.height)//2))
    except:
        draw.text((x+5, y+5), f"ERR: {name}", fill=(255,0,0), font=font)
    draw.text((x+2, y+th+2), name[:50], fill=(0,0,0), font=font)

canvas.save(sys.argv[2], quality=85)
print(f"已生成 {sys.argv[2]}: {len(items)} 张")
```

**使用方法**：

```bash
# 准备列表文件（格式：显示名<TAB>完整路径）
awk -F'\t' '$2==0 {print $1"\t/path/to/photos/"$1}' /tmp/face_result.txt > /tmp/noface_list.txt

# 分批（每批60张）
split -l 60 /tmp/noface_list.txt /tmp/batch_

# 生成联系表
python3 /tmp/contact.py /tmp/batch_aa /tmp/contact_aa.png
```

**每批 50-60 张**为宜，太多缩略图太小看不清。用 Read 工具查看联系表，逐张判断分类。

### 第四步：按分类移动文件

根据联系表判断结果，把文件移动到目标分类目录。

```bash
# 目标目录结构（示例：家庭相册）
DST="/path/to/家庭相册"
mkdir -p "$DST/明宇成长" "$DST/合照" "$DST/妈妈" "$DST/爸爸" "$DST/姥姥" "$DST/姥爷" "$DST/亲戚" "$DST/儿童画作" "$DST/风景/自然风光" "$DST/风景/城市景观" "$DST/其他待确认"

# 批量移动（按文件名列表）
while IFS=$'\t' read -r name path; do
  mv "$path" "$DST/合照/" 2>/dev/null
done < /tmp/group_move.txt
```

**分类决策规则**：
- 多人（>=2人脸）且是家庭成员 → 合照
- 单人是孩子 → 明宇成长
- 单人是成年女性（妈妈） → 妈妈
- 单人是成年男性（爸爸） → 爸爸
- 单人是老人 → 姥姥/姥爷（需区分）
- 儿童手绘/画作/手工 → 儿童画作
- 纯风景无人物 → 风景/自然风光 或 风景/城市景观
- 文档/截图/证件/工作内容 → 排除（不放家庭相册）
- 背影/侧脸无法判断 → 其他待确认

### 第五步：两级去重

整理完成后执行两级去重：精确MD5 + 感知哈希（dHash）。重复文件先移到 `_重复待确认` 目录，用户确认后再删除。

#### 5.1 精确去重（MD5）

完全相同的文件（同一张照片的不同命名副本）。

```python
import hashlib, os
from collections import defaultdict

album = "/path/to/家庭相册"
dup_dir = os.path.join(album, "_重复待确认")
os.makedirs(dup_dir, exist_ok=True)

# 收集图片
images = []
for root, dirs, files in os.walk(album):
    if "_重复待确认" in root: continue
    for f in files:
        if f.lower().endswith(('.jpg','.jpeg','.png','.heic')):
            images.append(os.path.join(root, f))

# 按大小分组（快速过滤），再算MD5
by_size = defaultdict(list)
for f in images:
    by_size[os.path.getsize(f)].append(f)

duplicates = []
for size, files in by_size.items():
    if len(files) < 2: continue
    by_hash = defaultdict(list)
    for f in files:
        h = hashlib.md5(open(f,'rb').read()).hexdigest()
        by_hash[h].append(f)
    for h, flist in by_hash.items():
        if len(flist) > 1:
            duplicates.append(flist)

# 每组保留路径最短的，其余移走
moved = 0
for files in duplicates:
    files.sort(key=lambda x: (len(x), x))
    for f in files[1:]:
        dst = os.path.join(dup_dir, os.path.basename(f))
        i = 1
        while os.path.exists(dst):
            base, ext = os.path.splitext(os.path.basename(f))
            dst = os.path.join(dup_dir, f"{base}_{i}{ext}")
            i += 1
        os.rename(f, dst)
        moved += 1
print(f"精确去重移走 {moved} 个文件")
```

#### 5.2 视觉相似去重（dHash感知哈希）

检测连拍、轻微裁剪、重新编码等视觉几乎相同但MD5不同的图片。

```python
from PIL import Image

def dhash(img_path, size=8):
    """差异哈希：缩小到9x8灰度，比较相邻像素，返回64位整数"""
    img = Image.open(img_path).convert('L').resize((size+1, size), Image.LANCZOS)
    pixels = list(img.getdata())
    bits = []
    for row in range(size):
        for col in range(size):
            bits.append(1 if pixels[row*(size+1)+col] > pixels[row*(size+1)+col+1] else 0)
    h = 0
    for b in bits: h = (h << 1) | b
    return h

def hamming(h1, h2):
    return bin(h1 ^ h2).count('1')

# 计算所有图片dHash
hashes = {}
for f in images:
    try: hashes[f] = dhash(f)
    except: pass

# 两两比较，汉明距离<=5视为相似
files = list(hashes.keys())
pairs = []
for i in range(len(files)):
    for j in range(i+1, len(files)):
        d = hamming(hashes[files[i]], hashes[files[j]])
        if d <= 5:
            pairs.append((d, files[i], files[j]))
```

**距离分级处理策略**：

| 汉明距离 | 含义 | 处理方式 |
|----------|------|----------|
| 0 | 视觉完全相同（重新编码/不同格式） | 同目录同IMG编号→自动保留文件名短的；跨目录/不同编号→生成联系表确认 |
| 1-2 | 几乎一样（连拍极近） | 生成联系表，用户决定保留哪张 |
| 3-5 | 较相似（连拍有表情/角度差异） | 暂保留，列出目录分布，后续按需筛选 |
| >5 | 有明显差异 | 保留，不处理 |

#### 5.3 生成确认联系表

对需要人工确认的相似对，生成左右并排的联系表：

```python
from PIL import Image, ImageDraw, ImageFont

pairs_confirm = [(f1,f2) for d,f1,f2 in pairs if d == 0]  # 或 d<=2

cols, rows = 2, len(pairs_confirm)
tw, th, lh, pad = 400, 300, 35, 10
canvas = Image.new('RGB', (cols*(tw+pad)+pad, rows*(th+lh+pad)+pad), 'white')
draw = ImageDraw.Draw(canvas)
font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 14)

for i, (f1, f2) in enumerate(pairs_confirm):
    for j, f in enumerate([f1, f2]):
        im = Image.open(f); im.thumbnail((tw, th))
        x = pad + j*(tw+pad) + (tw-im.width)//2
        y = pad + i*(th+lh+pad) + (th-im.height)//2
        canvas.paste(im, (x, y))
        lx = pad + j*(tw+pad)
        ly = pad + i*(th+lh+pad) + th + 3
        draw.text((lx, ly), f"{i*2+j+1}. {os.path.basename(f)[:45]}", fill='black', font=font)
        draw.text((lx, ly+18), os.path.dirname(f).replace(album+'/','')[:40], fill='gray', font=font)

canvas.save('/tmp/dup_confirm.png', quality=85)
```

**确认后执行移动**：用户告知每对删左/删右/都保留，按指示移到 `_重复待确认`。

### 第六步：完整性验证

```bash
# 源 vs 目标文件数对比
echo "源: $(find /path/to/source -type f | wc -l | tr -d ' ')"
echo "目标: $(find "$DST" -type f | wc -l | tr -d ' ')"

# 各分类数量
for d in "$DST"/*/; do
  echo "$(basename "$d"): $(find "$d" -type f | wc -l | tr -d ' ') 张"
done

# 总大小
du -sh "$DST"
```

## 家庭相册推荐目录结构

```
家庭相册/
├── 明宇成长/          # 孩子单人照（按年份可再细分）
├── 合照/              # 家庭成员多人合影
├── 爸爸/              # 爸爸单人照
├── 妈妈/              # 妈妈单人照
├── 姥姥/              # 姥姥单人照
├── 姥爷/              # 姥爷单人照
├── 亲戚/              # 其他亲戚
├── 儿童画作/          # 孩子的手绘、手工、美术作品
├── 风景/
│   ├── 自然风光/      # 山水、海景、公园
│   └── 城市景观/      # 建筑、街景、室内
└── 其他待确认/        # 无法判断的，后续人工处理
```

## 注意事项

1. **先复制后移动**：整理重要照片时，先复制到暂存目录，确认无误后再从源目录删除
2. **暂存目录命名**：如 `juan_家庭照片待确认/`，明确标记"待确认"
3. **人脸检测是辅助**：侧脸/背影/远距离会漏检，无人脸组仍需联系表确认
4. **文档截图排除**：家庭相册只放照片，文档/截图/证件应排除或单独归档
5. **大目录分批**：>1000 张的目录，联系表每批 50-60 张，分多轮处理
6. **保留来源信息**：暂存目录下按来源建子目录（如 `iphone_相处胶卷/`、`HMA-AL00_家人/`），便于追溯
7. **uchg 标志**：macOS 下某些文件可能有不可变标志，mv 报 Operation not permitted 时用 `sudo chflags nouchg 文件` 解除
