#!/bin/bash
# 把任意一张图片转成 Research 页用的配图：1600×900、16:9、白底、WebP，写到 images/pubs/<slug>.webp
#
# 用法：scripts/research-media.sh <输入图片> <slug> [--crop | --pad]
#   slug  : 和 _publications/<slug>.md 同名，例如 2026-mufasa
#   默认按比例自动选择：
#     比例和 16:9 相差 3% 以内 → 缩放后居中裁掉多余的一点（--crop）
#     否则                     → 完整缩进 16:9，四周补白（--pad），不裁内容
#   透明背景一律铺到白底上（Research 页的媒体框是白底，深色模式下也是）
#
# 支持 ffmpeg 能读的位图（png / jpg / webp / tiff / bmp / gif 首帧），
# 以及 pdf（第一页）、heic（用 macOS 的 sips 转换）和 svg（用 rsvg-convert 转换）。
# 依赖：ffmpeg、ffprobe、cwebp（brew install ffmpeg webp）；svg 另需 rsvg-convert（brew install librsvg）

set -euo pipefail

W=1600
H=900
QUALITY=82

die() { echo "错误：$*" >&2; exit 1; }

[ $# -ge 2 ] || die "用法：$0 <输入图片> <slug> [--crop | --pad]"
INPUT=$1
SLUG=$2
MODE=${3:-auto}

[ -f "$INPUT" ] || die "找不到输入文件：$INPUT"
[[ "$SLUG" =~ ^[a-z0-9][a-z0-9-]*$ ]] || die "slug 只能用小写字母、数字和连字符：$SLUG"
case "$MODE" in auto|--crop|--pad) ;; *) die "第三个参数只能是 --crop 或 --pad" ;; esac
for tool in ffmpeg ffprobe cwebp; do
  command -v "$tool" >/dev/null || die "缺少 $tool，请先 brew install ffmpeg webp"
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/images/pubs/$SLUG.webp"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ffmpeg 读不了的格式先转成 png
SRC="$INPUT"
EXT="$(echo "${INPUT##*.}" | tr '[:upper:]' '[:lower:]')"
case "$EXT" in
  pdf|heic|heif)
    command -v sips >/dev/null || die "$EXT 需要 macOS 的 sips 来转换"
    sips -s format png "$INPUT" --out "$TMP/src.png" >/dev/null
    SRC="$TMP/src.png" ;;
  svg)
    command -v rsvg-convert >/dev/null || die "svg 需要 rsvg-convert，请先 brew install librsvg，或把 svg 导出成 png 再用"
    rsvg-convert -w 3200 -a "$INPUT" -o "$TMP/src.png" || die "svg 转换失败"
    SRC="$TMP/src.png" ;;
esac

SIZE="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$SRC")"
SW=${SIZE%x*}
SH=${SIZE#*x}
[ -n "$SW" ] && [ -n "$SH" ] || die "读不出图片尺寸：$INPUT"

if [ "$MODE" = auto ]; then
  # 和 16:9 的相对偏差（千分比），3% 以内裁切，否则补白
  DEV=$(( (SW * H * 1000 / (SH * W)) - 1000 ))
  [ "$DEV" -lt 0 ] && DEV=$(( -DEV ))
  if [ "$DEV" -le 30 ]; then MODE=--crop; else MODE=--pad; fi
fi

if [ "$MODE" = --crop ]; then
  FG="scale=$W:$H:force_original_aspect_ratio=increase:flags=lanczos,crop=$W:$H"
else
  FG="scale=$W:$H:force_original_aspect_ratio=decrease:flags=lanczos"
fi

ffmpeg -v error -y -i "$SRC" -filter_complex \
  "color=white:s=${W}x${H}[bg];[0:v]format=rgba,$FG[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,format=rgb24" \
  -frames:v 1 "$TMP/out.png"

mkdir -p "$(dirname "$OUT")"
cwebp -quiet -q "$QUALITY" -m 6 -metadata none "$TMP/out.png" -o "$OUT"

echo "输入：$INPUT（${SW}×${SH}）"
echo "处理：$([ "$MODE" = --crop ] && echo '缩放并居中裁切到 16:9' || echo '完整缩进 16:9，四周补白')"
echo "输出：images/pubs/$SLUG.webp（${W}×${H}，$(( $(wc -c < "$OUT") / 1024 )) KB）"
if [ "$SW" -lt "$W" ] && [ "$SH" -lt "$H" ]; then
  echo "提醒：原图小于 ${W}×${H}，被放大了，网页上可能发虚，最好换一张更大的原图"
fi
echo "front matter 里写：media: { src: /images/pubs/$SLUG.webp }"
