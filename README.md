# 看懂画风：一场有趣的插画旅行

策划与整理：YZ

正文由 AI 编写，插画由 AI 生成

中文图解入门书，写给喜欢看图、想说清楚自己喜欢什么的人。修订完本 v1.1，2026-10-06。

全书包含 35 个画风专题、43 张独立生成插图、14 组横向比较、同故事三种漫画案例。53 个正文单元与资料附录全部完成。每个画风专题补有“来源与发展”；新增两章参考工作室，用名画与流行内容练习观察、迁移和比较。

## 阅读入口

- [完整目录](SUMMARY.md)：按顺序逐章阅读。
- [导读](chapters/00-preface.md)：理解图像、标签与证据。
- [名画参考工作室](chapters/51-masterpiece-lab.md)：从《星夜》《神奈川冲浪里》、修拉与马蒂斯的作品提取方法。
- [流行视觉工作室](chapters/52-popular-lab.md)：比较动画、游戏像素、纵向漫画与双色印刷语言。
- [同题材实验室](chapters/45-comparisons.md)：练习比较并识别干扰。
- `build/book.md`：交付包中的完整合并 Markdown；保留目录与图片相对路径。

## 图像与资料约定

43 张插图均为 AI 生成教学示意。名画与流行内容通过馆方、发行方或官方资料链接旁读，生成图是方法迁移的原创场景，不能当作原作。成图与设想的差异在讲解中说明；模拟纹理不能证明真实制作工艺。

40 个来源编号在相关事实旁直接链接原始资料；[资料附录](editorial/SOURCES.md)汇总出处和适用范围。图像分析、比较与练习答案属于编辑解读。艺术传统、材料、工具和传播形式有交叉，本书不声称穷尽全部流派。

## 组织结构

| 路径 | 内容 |
| --- | --- |
| `chapters/` | 53 个分章 Markdown，权威书稿 |
| `SUMMARY.md` | 正式阅读顺序 |
| `assets/images/` | 43 张阅读用 JPEG |
| `assets/originals/` | 43 张完整生成 PNG |
| `assets/manifest.json` | 编号、提示记录、成图评价与原图 SHA-256 |
| `editorial/` | 来源、写作规范、核验和版本记录 |
| `scripts/` | 构建、检查和源码包命令 |
| `build/` | 用户可重建的阅读产物，不进入 Git |

## 构建与检查

在仓库根目录执行，使用 Python 标准库：

```bash
python3 scripts/build.py
python3 scripts/check.py
```

默认只生成 `build/book.md` 与统计文件。需要 HTML 时，由读者自行运行：

```bash
python3 scripts/build.py --html
python3 scripts/check.py --html
```

网页由 tag 发布流程构建并部署到 GitHub Pages。所有 `.html` 与 `build/` 均被 Git 忽略；阅读 JPEG 的制作另需 Pillow，已交付的图片无需重新制作。

## Git 与归档

交付包保留既有提交和 v0.1、v1.0、v1.1 标签，不绑定远端账户。查看修订内容可运行 `git diff v1.0..v1.1 --stat`。归档命令只打包 Git 管理的源文件、完整 Git 历史，以及现有合并 Markdown 与统计文件；不收入 HTML：

```bash
python3 scripts/package.py --output ../style-atlas-sourcebook.zip
```

旧版本记录描述当时的交付，不代表本版仍生成 HTML。正式书稿中没有占位章节。

## Tag 驱动发布

推送 `v*` 标签触发 `.github/workflows/release.yml`：检查书稿、生成网页与 PDF，再部署 GitHub Pages，并将全书 PDF 和分章 PDF ZIP 上传到同名 GitHub Release。普通分支提交不触发发布；重复运行同一标签会更新附件。发布任务排队执行，避免部署并发覆盖。

首次使用须在仓库 Settings → Pages → Build and deployment 中选择 **GitHub Actions**。若 `github-pages` 环境限制部署分支，应允许 `v*` 标签。工作流使用仓库自带 `GITHUB_TOKEN`，无需额外密钥。

```bash
git tag v1.2.0
git push origin v1.2.0
```

标签示例不代表已创建版本；发布前同步 `book.json` 的版本与日期及书稿版本说明。Pages 首页提供全书 PDF 与分章包下载。

本地生成 PDF（Python 3.12；Linux 另需 Pango 和 Noto CJK 字体）：

```bash
sudo apt-get install fonts-noto-cjk libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
python3 -m pip install -r scripts/pdf-requirements.txt
python3 scripts/build_pdf.py
python3 scripts/check_pdf.py
```

输出为 `build/pdf/style-atlas.pdf`、各章及资料附录 PDF、`build/pdf/style-atlas-chapters.zip`。章节从新页开始，来源编号在正文位置对应页脚资料，PDF 保留点击链接。PDF 输出不进入 Git。

`libharfbuzz-subset0` 为大型中文字体提供原生裁剪；缺少它时，WeasyPrint 会回退到较慢的 Python 字体处理。CI 会检查原生裁剪是否可用。构建复用相同来源页脚，并逐个输出 PDF 的页数与耗时。

修复发布脚本后，应从包含修复的提交创建新标签。重新运行旧标签的 Actions 仍使用旧提交中的脚本与工作流。
