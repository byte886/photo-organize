# photo-organize

家庭/个人照片批量整理工作流：目录侦察、人脸检测预筛、联系表生成与逐批核验、按内容分类移动、重复检测与完整性验证，适配手机/微信/硬盘备份归集。

## 使用

这是豆包（及兼容 Agent）的**本地技能（Skill）**。完整能力、触发场景与操作流程见入口文档 **[`SKILL.md`](SKILL.md)**，Agent 命中时首先读取它；下列子目录按需加载，不必一次全读。

## 目录

- `SKILL.md`：技能入口与路由
- `scripts/contact_sheet.py`：联系表（缩略图网格）生成
- `scripts/dedup_photos.py`：MD5 精确 + dHash 感知两级去重

## 许可

[MIT](LICENSE) © 2026 byte886
