"""Rendu d'une vidéo voix Datenshi (1080x1920, 30 i/s).
Usage :
  python3 tools/voice/build.py SPEC.json DOSSIER --stills      # planche de contrôle (contact.jpg)
  python3 tools/voice/build.py SPEC.json DOSSIER               # vidéo + sound design -> ID_sfx.mp4
  python3 tools/voice/build.py SPEC.json DOSSIER --voice v.mp3 # idem + mixage voix -> ID.mp4
"""
import json, os, subprocess, sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = (HERE / "motion.html").as_uri()
FPS = 30
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS)]
CHROME = "/usr/bin/google-chrome"


def open_page(p, spec):
    b = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None, args=["--disable-gpu"])
    page = b.new_page(viewport={"width": 1080, "height": 1920})
    page.goto(PAGE)
    page.wait_for_timeout(300)
    info = page.evaluate("cfg => setup(cfg)", spec)
    return b, page, info


def chunk(args):
    spec, a, b_, path = args
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b, page, _ = open_page(p, spec)
        tmp = path.with_suffix(".tmp.mp4")
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                               "-c:v", "mjpeg", "-i", "-", *ENC, str(tmp)], stdin=subprocess.PIPE)
        for i in range(a, b_):
            page.evaluate(f"render({i / FPS})")
            ff.stdin.write(page.screenshot(type="jpeg", quality=92))
        ff.stdin.close()
        if ff.wait() != 0:
            raise RuntimeError("ffmpeg chunk")
        b.close()
    tmp.rename(path)
    return path


MIX = ("[1:a]aformat=channel_layouts=stereo,aresample=48000,adelay={ms}:all=1,apad,asplit[v1][v2];"
       "[0:a]volume=0.6[s];[s][v1]sidechaincompress=threshold=0.04:ratio=5:attack=15:release=350[sd];"
       "[sd][v2]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")


def main():
    spec = json.load(open(sys.argv[1])); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    vid = spec["id"]
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b, page, info = open_page(p, spec)
        dur = info["dur"]
        json.dump(info["events"], open(out / "events.json", "w"), indent=0)
        if "--stills" in sys.argv:
            sc = page.evaluate("SC.map(s => [s.t0, s.t1, s.type])")
            times = []
            for t0, t1, _ in sc:
                times += [round(t0 + (t1 - t0) * .55, 2), round(max(t0, t1 - .12), 2)]
            shots = []
            for k, t in enumerate(times):
                page.evaluate(f"render({t})")
                f = out / f"still_{k:02d}.jpg"; page.screenshot(path=str(f), type="jpeg", quality=80); shots.append(f)
            b.close()
            cols = 6
            rows = (len(shots) + cols - 1) // cols
            ins = sum([["-i", str(s)] for s in shots], [])
            pads = cols * rows - len(shots)
            fl = "".join(f"[{i}:v]scale=270:480,drawtext=text='{times[i]}s':x=8:y=8:fontsize=22:fontcolor=yellow:box=1:boxcolor=black[s{i}];" for i in range(len(shots)))
            labels = "".join(f"[s{i}]" for i in range(len(shots)))
            if pads:
                fl += "".join(f"color=c=black:s=270x480:d=1[p{j}];" for j in range(pads)); labels += "".join(f"[p{j}]" for j in range(pads))
            fl += f"{labels}xstack=inputs={cols * rows}:layout=" + "|".join(f"{(i % cols) * 270}_{(i // cols) * 480}" for i in range(cols * rows))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fl, "-frames:v", "1", str(out / "contact.jpg")], check=True)
            for s in shots: s.unlink()
            print("contact", out / "contact.jpg", "dur", dur)
            return
        b.close()
    n = int(round(dur * FPS)); k = 4; step = (n + k - 1) // k
    jobs = [(spec, i * step, min(n, (i + 1) * step), out / f"part{i}.mp4") for i in range(k)]
    with Pool(k) as pool:
        parts = pool.map(chunk, jobs)
    (out / "parts.txt").write_text("".join(f"file '{q.name}'\n" for q in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(out / "parts.txt"), "-c", "copy", str(out / "silent.mp4")], check=True)
    subprocess.run([sys.executable, str(HERE / "sfx.py"), str(out / "events.json"), str(dur), str(spec.get("seed", 1)), str(out / "sfx.wav")], check=True)
    tmp = out / f"{vid}_sfx.tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / "silent.mp4"), "-i", str(out / "sfx.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.rename(out / f"{vid}_sfx.mp4")
    for q in parts: q.unlink()
    (out / "parts.txt").unlink(); (out / "silent.mp4").unlink()
    if "--voice" in sys.argv:
        v = sys.argv[sys.argv.index("--voice") + 1]
        ms = int(round(spec.get("lead", .3) * 1000))
        tmp = out / f"{vid}.tmp.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / f"{vid}_sfx.mp4"), "-i", v, "-filter_complex", MIX.format(ms=ms),
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(tmp)], check=True)
        tmp.rename(out / f"{vid}.mp4")
    print("done", vid, "dur", dur)


if __name__ == "__main__":
    main()
