"""Burn a small AI-production notice into the site's video assets.

The notice is placed in the bottom band of each frame, in a column that the
existing layout leaves empty: bottom-left for the hero clip (its own note sits
bottom-right), horizontally centred for the talk deck (its footer occupies both
corners).  Originals are kept in project_page/_backup/ai_notice_20260922/.
"""
import shutil
import subprocess
import sys
from pathlib import Path

FF = Path(r"C:/Users/jiwon/AppData/Roaming/Python/Python314/site-packages"
          r"/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe")
ROOT = Path(r"C:/Users/jiwon/OneDrive/AG1_Drive/01_research/ICRA_NH_Calib")
WORK = Path(r"C:/Users/jiwon/AppData/Local/Temp/ainotice")

NOTICE = "Figures and video produced with AI assistance"
SIZE = 19
COLOR = "0x9aa0a8"
Y = 1013

# (path, x expression, crf).  The web copies of the talk keep a higher crf so
# that adding the notice does not grow the file past its pre-notice size.
JOBS = [
    ("project_page/assets/hero_video/NHCalib_hero.mp4",        "64",           23),
    ("project_page/assets/hero_video/NHCalib_hero_poster.png", "64",           None),
    ("project_page/assets/talk/NHCalib_talk.mp4",              "(w-text_w)/2", 28),
    ("project_page/assets/talk/NHCalib_talk_poster.png",       "(w-text_w)/2", None),
    ("video/out/NHCalib_talk.mp4",                             "(w-text_w)/2", 23),
    ("video/out/NHCalib_talk_web.mp4",                         "(w-text_w)/2", 28),
]


def vf(x_expr):
    return (f"drawtext=fontfile=arial.ttf:text='{NOTICE}':"
            f"fontsize={SIZE}:fontcolor={COLOR}:x={x_expr}:y={Y}")


def run(cmd):
    r = subprocess.run(cmd, cwd=WORK, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg failed: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    shutil.copy("C:/Windows/Fonts/arial.ttf", WORK / "arial.ttf")

    for rel, x_expr, crf in JOBS:
        src = ROOT / rel
        if not src.exists():
            sys.exit(f"missing input: {src}")
        tmp = WORK / ("out_" + src.name)
        if src.suffix == ".png":
            cmd = [FF, "-v", "error", "-y", "-i", src, "-vf", vf(x_expr),
                   "-frames:v", "1", tmp]
        else:
            cmd = [FF, "-v", "error", "-y", "-i", src, "-vf", vf(x_expr),
                   "-c:v", "libx264", "-crf", str(crf), "-preset", "slow",
                   "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
                   "-metadata", f"comment={NOTICE}", tmp]
        run(cmd)
        before = src.stat().st_size
        shutil.move(str(tmp), str(src))
        print(f"{rel}: {before} -> {src.stat().st_size} B")


if __name__ == "__main__":
    main()
