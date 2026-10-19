---
name: research-media
description: 给 Research 页（/research/）的某篇论文换配图或加配图，并按需上线。用户给出一张图片（png / jpg / webp / pdf / svg 等任意格式）和要放到哪篇论文时使用，例如“把这张图换成 MUFASA 的配图”“给新论文加图然后上线”。
---

# Research 页配图 SOP

Research 页的每篇论文由 `_publications/<slug>.md` 的 front matter 驱动，模板是
`_includes/research-entry.html`（文件开头的注释列出了全部字段）。所有媒体按 16:9 显示，
图片统一用 1600×900 的 WebP，放在 `images/pubs/<slug>.webp`。

## 需要从用户那里拿到的

1. 图片文件的路径。
2. 放到哪篇论文。用标题或关键词在 `_publications/` 里找到对应的 `.md`，文件名去掉 `.md` 就是 slug。
   找不到、或者匹配到不止一篇时，先问用户，不要猜。
3. 是否要上线。用户没说上线，就只改本地、不提交。

## 步骤

1. **确认目标文件**：读一遍 `_publications/<slug>.md`，看现有的 `media:` 字段。

2. **转换图片**（在仓库根目录运行）：

   ```bash
   scripts/research-media.sh <图片路径> <slug>
   ```

   脚本会输出 `images/pubs/<slug>.webp`，并打印采用了裁切还是补白。
   - 默认规则：比例接近 16:9（差 3% 以内）就居中裁切，否则完整缩进 16:9、四周补白，不裁内容。
     用户明确要求时才加 `--crop` 或 `--pad` 覆盖默认规则。
   - 脚本提醒“原图小于 1600×900”时，把这句话转告用户。
   - 不要自己另写 ffmpeg 命令，也不要改输出尺寸、格式或质量。

3. **改 front matter**：在 `_publications/<slug>.md` 两条 `---` 之间，确保有

   ```yaml
   media:
     src: /images/pubs/<slug>.webp
   ```

   - 已有 `media:` 就只改 `src`。原来是视频（`.mp4`，带 `poster:`）而现在换成图片的，删掉 `poster:`。
   - 不要加 `caption:`。用户已决定 Research 页不放图注，除非用户这次明确要求。
   - 不要改其他字段，也不要改模板、CSS 或 JS。
   - YAML 规则：缩进只用两个空格；值里有冒号要整段加引号。

4. **本地构建验证**：

   ```bash
   python3 _cv/tex2html.py _cv/main.tex -o _includes/cv-body.html
   PATH=/opt/homebrew/opt/ruby@3.3/bin:$PATH bundle exec jekyll build -q -d /tmp/research-check
   grep -c 'images/pubs/<slug>.webp' /tmp/research-check/research/index.html
   ```

   第一条生成 CV 页需要的文件（它被 gitignore，本地构建缺了会报错）。
   构建必须没有报错，最后一条输出至少为 1。不满足就停下，把报错告诉用户。
   临时目录用完删掉；如果所在环境规定了临时目录，就用那个。

5. **上线**（只在用户要求上线时做）：
   - 先看 `git status`。**只提交这次改的两个文件**：`images/pubs/<slug>.webp` 和
     `_publications/<slug>.md`。工作区里的其他改动可能属于别的工作，不要一起提交，也不要撤销。
   - 提交信息用英文，一句话说明给哪篇论文换了图，例如 `Research: new figure for MUFASA`。
   - `git push origin main`。推送被拒（远端有新提交）时先 `git pull --rebase origin main` 再推；
     有冲突就停下问用户。
   - 等部署完成：

     ```bash
     gh run list --limit 1
     gh run watch <run-id> --exit-status
     ```

   - 线上验证：

     ```bash
     curl -sI https://eliotchen8.github.io/images/pubs/<slug>.webp | head -1
     ```

     应为 `HTTP/2 200`。再用 `curl -s https://eliotchen8.github.io/research/ | grep -c '<slug>.webp'` 确认页面引用了新图。

## 最后向用户汇报

- 用了哪张图、对应哪篇论文、裁切还是补白、输出大小（KB）。
- 改了哪些文件；是否已提交、推送；部署是否成功，线上是否已确认。
- 构建或部署失败时，原样给出报错，不要说已完成。
