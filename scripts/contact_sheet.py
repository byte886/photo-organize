#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
contact_sheet.py — 联系表（缩略图网格）生成器，服务照片批量整理的"逐批核验"。

输入列表文件：每行一张图，格式「显示名<TAB>完整路径」（# 开头为注释）。
输出一张 PNG 网格图，每格含缩略图 + 文件名，便于用 Read 工具逐张判断分类。

用法：
    python3 contact_sheet.py <list_file> <output.png> [--cols 4] [--tw 360] [--th 270]

仅依赖 Pillow；每批建议 50-60 张（--cols 4 时约 13-15 行），太多缩略图太小看不清。
"""
import argparse
import sys
from pathlib import Path


def load_items(list_file: str):
    items = []
    with open(list_file, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                items.append((parts[0], parts[1]))
    return items


def load_font(size: int):
    from PIL import ImageFont
    for cand in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(cand, size)
        except Exception:
            continue
    return ImageFont.load_default()


def build(items, cols, tw, th, lh, pad):
    from PIL import Image, ImageDraw
    rows = (len(items) + cols - 1) // cols
    canvas = Image.new(
        "RGB",
        (cols * (tw + pad) + pad, rows * (th + lh + pad) + pad),
        (240, 240, 240),
    )
    draw = ImageDraw.Draw(canvas)
    font = load_font(12)
    for idx, (name, path) in enumerate(items):
        col, row = idx % cols, idx // cols
        x = pad + col * (tw + pad)
        y = pad + row * (th + lh + pad)
        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.thumbnail((tw, th))
                canvas.paste(im, (x + (tw - im.width) // 2, y + (th - im.height) // 2))
        except Exception:
            draw.text((x + 5, y + 5), f"ERR: {name[:40]}", fill=(255, 0, 0), font=font)
        draw.text((x + 2, y + th + 2), name[:50], fill=(0, 0, 0), font=font)
    return canvas


def main():
    ap = argparse.ArgumentParser(description="生成照片联系表（缩略图网格）")
    ap.add_argument("list_file", help="列表文件：每行「显示名<TAB>路径」")
    ap.add_argument("output", help="输出 PNG 路径")
    ap.add_argument("--cols", type=int, default=4, help="每行列数（默认 4）")
    ap.add_argument("--tw", type=int, default=360, help="单格宽（默认 360）")
    ap.add_argument("--th", type=int, default=270, help="单格高（默认 270）")
    ap.add_argument("--lh", type=int, default=30, help="标签栏高（默认 30）")
    ap.add_argument("--pad", type=int, default=4, help="格间距（默认 4）")
    args = ap.parse_args()

    items = load_items(args.list_file)
    if not items:
        sys.exit("列表为空，退出")
    canvas = build(items, args.cols, args.tw, args.th, args.lh, args.pad)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, quality=85)
    print(f"已生成 {args.output}: {len(items)} 张，{args.cols} 列")


if __name__ == "__main__":
    main()
