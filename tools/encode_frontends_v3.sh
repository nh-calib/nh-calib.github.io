#!/usr/bin/env bash
set -euo pipefail

frames=${1:-/tmp/feviz/frames_v3}
out=${2:-/tmp/feviz/out_v3}
mkdir -p "$out"

ffmpeg -hide_banner -loglevel error -y -framerate 24 \
  -i "$frames/%05d.png" -c:v libx264 -preset medium -crf 27 \
  -pix_fmt yuv420p -movflags +faststart "$out/hero_frontends_real.mp4"

ffmpeg -hide_banner -loglevel error -y -framerate 24 \
  -i "$frames/%05d.png" -c:v libvpx-vp9 -b:v 0 -crf 34 \
  -pix_fmt yuv420p "$out/hero_frontends_real.webm"

cp "$frames/00120.png" "$out/hero_frontends_real.png"
echo FRONTENDS_ENCODE_DONE
