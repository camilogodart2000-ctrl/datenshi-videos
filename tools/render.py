"""Render Datenshi TikTok videos from HTML animations.
Usage: python3 render.py specs.json out_dir [--stills]
Each spec: {"id", "type", "dur", "bpm", "seed", "acc", "acc2", ...type fields}
"""
import json, os, subprocess, sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = (HERE / "template.html").as_uri()
FPS = 30


def render_one(args):
    spec, out_dir, stills = args
    from playwright.sync_api import sync_playwright
    out_dir = Path(out_dir)
    vid = spec["id"]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--disable-gpu"])
        page = b.new_page(viewport={"width": 1080, "height": 1920})
        page.goto(TEMPLATE)
        page.evaluate("cfg => setup(cfg)", spec)
        if stills:
            for t in stills:
                page.evaluate(f"render({t})")
                page.screenshot(path=str(out_dir / f"{vid}_t{t}.jpg"), type="jpeg", quality=80)
            b.close()
            return vid
        tmp = out_dir / f"{vid}.video.tmp.mp4"
        ff = subprocess.Popen([
            "ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
            "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", str(FPS), str(tmp)], stdin=subprocess.PIPE)
        n = int(spec["dur"] * FPS)
        for i in range(n):
            page.evaluate(f"render({i / FPS})")
            ff.stdin.write(page.screenshot(type="jpeg", quality=92))
        ff.stdin.close()
        if ff.wait() != 0:
            raise RuntimeError(f"ffmpeg video failed for {vid}")
        b.close()
    wav = out_dir / f"{vid}.wav"
    subprocess.run([sys.executable, str(HERE / "phonk.py"), str(spec["seed"]), str(spec["dur"]),
                    str(spec["bpm"]), str(wav)], check=True)
    final_tmp = out_dir / f"{vid}.tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-i", str(wav),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(final_tmp)], check=True)
    final_tmp.rename(out_dir / f"{vid}.mp4")
    tmp.unlink(); wav.unlink()
    return vid


if __name__ == "__main__":
    specs = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    stills = None
    if "--stills" in sys.argv:
        stills = [1.5, 3.0, 4.6, 6.4]
    only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")]
    if only:
        specs = [s for s in specs if s["id"] in only[0].split(",")]
    jobs = [(s, out, (stills + [s["dur"] - 1.5]) if stills else None) for s in specs]
    with Pool(min(4, len(jobs))) as pool:
        for vid in pool.imap_unordered(render_one, jobs):
            print("done", vid, flush=True)
