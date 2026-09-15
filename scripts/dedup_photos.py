#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dedup_photos.py — 照片两级去重工具，服务照片整理第五步。

子命令：
  md5   精确去重：同大小分组后算 MD5，完全相同的副本，每组保留"路径最短"者，
        其余默认仅报告；加 --apply 才移入 <album>/_重复待确认/。
  dhash 视觉相似去重：9x8 灰度差异哈希(dHash, 64bit)，两两算汉明距离，
        输出 <= 阈值的相似对（默认 5），供生成联系表人工裁决，不自动删除。

用法：
    python3 dedup_photos.py md5  <相册目录> [--apply]
    python3 dedup_photos.py dhash <相册目录> [--threshold 5]

仅依赖 Pillow（dhash 需要；md5 只用标准库）。重复/相似文件先移到"待确认"目录，
不直接删除，确认后再清。
"""
import argparse
import hashlib
import os
import shutil
import sys
from collections import defaultdict

IMG_EXT = (".jpg", ".jpeg", ".png", ".heic")


def collect_images(album: str):
    images = []
    for root, _dirs, files in os.walk(album):
        if "_重复待确认" in root:  # 已隔离的不再参与
            continue
        for f in files:
            if f.lower().endswith(IMG_EXT):
                images.append(os.path.join(root, f))
    return images


def unique_dest(dup_dir: str, f: str):
    dst = os.path.join(dup_dir, os.path.basename(f))
    i = 1
    while os.path.exists(dst):
        base, ext = os.path.splitext(os.path.basename(f))
        dst = os.path.join(dup_dir, f"{base}_{i}{ext}")
        i += 1
    return dst


def cmd_md5(album: str, apply: bool):
    images = collect_images(album)
    by_size = defaultdict(list)
    for f in images:  # 先按大小分组，快速过滤掉大小唯一的文件
        by_size[os.path.getsize(f)].append(f)

    groups = []
    for _size, files in by_size.items():
        if len(files) < 2:
            continue
        by_hash = defaultdict(list)
        for f in files:
            with open(f, "rb") as fh:
                by_hash[hashlib.md5(fh.read()).hexdigest()].append(f)
        for flist in by_hash.values():
            if len(flist) > 1:
                groups.append(flist)

    moved = 0
    dup_dir = os.path.join(album, "_重复待确认")
    for files in groups:
        files.sort(key=lambda x: (len(x), x))  # 保留路径最短的
        keep, dups = files[0], files[1:]
        print(f"保留 {keep}")
        for f in dups:
            print(f"  重复 {f}")
            if apply:
                os.makedirs(dup_dir, exist_ok=True)
                shutil.move(f, unique_dest(dup_dir, f))
                moved += 1
    if apply:
        print(f"精确去重：发现 {len(groups)} 组重复，已移入待确认 {moved} 个")
    else:
        print(f"精确去重：发现 {len(groups)} 组重复（dry-run，加 --apply 才移入待确认）")


def dhash(img_path: str, size: int = 8):
    from PIL import Image
    with Image.open(img_path) as im:
        gray = im.convert("L").resize((size + 1, size), Image.LANCZOS)
        px = list(gray.getdata())
    bits = []
    for row in range(size):
        for col in range(size):
            bits.append(1 if px[row * (size + 1) + col] > px[row * (size + 1) + col + 1] else 0)
    h = 0
    for b in bits:
        h = (h << 1) | b
    return h


def hamming(h1: int, h2: int) -> int:
    return bin(h1 ^ h2).count("1")


def cmd_dhash(album: str, threshold: int):
    images = collect_images(album)
    hashes = {}
    for f in images:
        try:
            hashes[f] = dhash(f)
        except Exception as e:
            print(f"跳过无法读取的 {f}: {e}", file=sys.stderr)
    files = list(hashes)
    pairs = []
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            d = hamming(hashes[files[i]], hashes[files[j]])
            if d <= threshold:
                pairs.append((d, files[i], files[j]))
    pairs.sort(key=lambda t: t[0])
    if not pairs:
        print("无相似图片对")
        return
    print(f"汉明距离 <= {threshold} 的相似对（距离分级见 SKILL 第五步，需联系表人工裁决）：")
    for d, a, b in pairs:
        print(f"  d={d}\n    A {a}\n    B {b}")


def main():
    ap = argparse.ArgumentParser(description="照片两级去重（MD5 精确 + dHash 相似）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("md5", help="精确去重")
    p1.add_argument("album")
    p1.add_argument("--apply", action="store_true", help="真正移入待确认目录（默认只报告）")
    p2 = sub.add_parser("dhash", help="视觉相似去重")
    p2.add_argument("album")
    p2.add_argument("--threshold", type=int, default=5, help="汉明距离阈值（默认 5）")
    args = ap.parse_args()

    if not os.path.isdir(args.album):
        sys.exit(f"不是目录：{args.album}")
    if args.cmd == "md5":
        cmd_md5(args.album, args.apply)
    else:
        cmd_dhash(args.album, args.threshold)


if __name__ == "__main__":
    main()
