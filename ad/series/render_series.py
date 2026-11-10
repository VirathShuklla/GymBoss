import asyncio
import subprocess
import sys
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent
AD = ROOT.parent
FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 44100
FPS = 24
OV = ROOT / "overlays"
OUT = ROOT / "out"
OV.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

FONTS = '<link href="https://fonts.googleapis.com/css2?family=Anton&family=Archivo:wght@800;900&family=Bungee&family=Playfair+Display:ital,wght@0,800;1,600;1,800&family=Space+Grotesk:wght@600;700&family=JetBrains+Mono:wght@700&display=block" rel="stylesheet">'
BASE_CSS = """*{margin:0;padding:0;box-sizing:border-box} html,body{width:1080px;height:1920px;background:transparent;overflow:hidden}
.abs{position:absolute} .c{left:0;right:0;text-align:center}
.retro{font-family:'Bungee';color:#fff;line-height:1.08;text-shadow:5px 5px 0 #FF4FA3,10px 10px 0 #18D6C9}
.sub{font:700 54px 'Space Grotesk';color:#fff;line-height:1.2;-webkit-text-stroke:2px #000;paint-order:stroke fill;text-shadow:0 4px 14px rgba(0,0,0,.6);padding:0 70px}
.tt{display:inline-block;background:#fff;color:#111;font:800 50px 'Archivo';line-height:1.25;padding:22px 34px;border-radius:22px;max-width:920px}
.meme{font-family:'Anton';color:#fff;-webkit-text-stroke:6px #000;paint-order:stroke fill;text-transform:uppercase;line-height:1}
.doc{font-family:'Playfair Display';color:#fff;text-shadow:0 3px 18px rgba(0,0,0,.55)}
.toast{background:#fff;border-radius:30px;padding:24px 30px;display:flex;gap:22px;align-items:center;box-shadow:0 30px 60px rgba(0,0,0,.45);font-family:'Space Grotesk'}
.toast .t1{font-size:24px;font-weight:700;color:#16A34A;letter-spacing:1.5px;text-transform:uppercase}
.toast .amt{font:700 58px 'JetBrains Mono';color:#0A0712} .toast .t2{font-size:22px;color:#6B6680;font-weight:600}
.wm{font-family:'Anton';font-size:40px;color:#fff;letter-spacing:1px;text-shadow:0 2px 10px rgba(0,0,0,.6)} .wm b{color:#A78BFA;font-weight:400}
"""
CHECK = '<svg viewBox="0 0 52 52" width="90" height="90"><circle cx="26" cy="26" r="24" fill="#22C55E"/><path d="M15 27l7 7 15-16" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def toast(title, amt, who, y):
    return f'<div class="abs" style="left:110px;top:{y}px;width:860px"><div class="toast">{CHECK}<div><div class="t1">{title}</div><div class="amt">{amt}</div><div class="t2">{who}</div></div></div></div>'


def sub(text, y=1430):
    return f'<div class="abs c sub" style="top:{y}px">{text}</div>'


WM = '<div class="abs wm" style="right:60px;top:96px">GYMBOSS<b>_VVO</b></div>'

REELS = {
    "a": {
        "name": "GymBoss_Panda_Ep1_SixTomorrows_9x16",
        "clips": ["a1", "a2", "a3"],
        "grade": "eq=saturation=1.18:contrast=1.04,rgbashift=rh=3:bh=-3,noise=alls=9:allf=t",
        "music": ("music_a", 0.55),
        "end": 3.2,
        "caps": [
            ('<div class="abs c retro" style="top:250px;font-size:74px">when a member says<br><span style="color:#FFE45C">"I\'ll pay tomorrow"</span><br>for the 6th time</div>', 0.0, 4.95),
            (sub("Tomorrow. He said... tomorrow."), 0.55, 2.7),
            ('<div class="abs c retro" style="top:250px;font-size:80px">6 tomorrows.<br><span style="color:#FFE45C">₹0 received.</span></div>', 5.0, 9.95),
            (sub("That was six tomorrows ago."), 5.6, 7.7),
            ('<div class="abs c retro" style="top:250px;font-size:64px">GymBoss sent<br>ONE reminder</div>', 10.0, 14.95),
            (sub("So I let the app ask."), 10.35, 11.9),
            (sub("Paid in ten minutes.<br>I love technology."), 11.9, 14.6),
            (toast("Payment received", "₹2,500", "Rahul · after 1 reminder", 600), 12.0, 14.95),
        ],
        "audio": [("a_1", 0.55), ("sfx_dundun", 5.0), ("a_2", 5.6), ("sfx_slurp", 10.05), ("a_3", 10.35), ("sfx_ding", 12.0), ("a_4", 15.5)],
    },
    "b": {
        "name": "GymBoss_Panda_Ep2_MissingCash_9x16",
        "clips": ["b1", "b2", "b3"],
        "grade": "eq=contrast=1.1:saturation=0.9,vignette=PI/4,noise=alls=13:allf=t",
        "music": ("music_b", 0.8),
        "end": 2.8,
        "caps": [
            ('<div class="abs c" style="top:240px"><span class="tt">day 3 of investigating where ₹12,000 vanished from my gym register</span></div>', 0.0, 4.95),
            ('<div class="abs c" style="top:240px"><span class="tt">me at 3AM connecting receipts that have nothing to do with each other</span></div>', 5.0, 9.95),
            ('<div class="abs c" style="top:240px"><span class="tt">and then I found the culprit...</span></div>', 10.0, 12.5),
            ('<div class="abs c" style="top:240px"><span class="tt">I wrote ₹1,200 as ₹12,000</span></div>', 12.5, 14.95),
            ('<div class="abs c meme" style="top:1380px;font-size:190px">it was me.</div>', 13.1, 14.95),
        ],
        "audio": [("sfx_thunder", 0.05), ("sfx_whoosh", 4.85), ("sfx_dundun", 10.0), ("sfx_vineboom", 13.1)],
    },
    "c": {
        "name": "GymBoss_Panda_Ep3_PlanetGym_9x16",
        "clips": ["c1", "c2", "c3"],
        "grade": "eq=saturation=1.08,vignette=PI/6",
        "music": ("music_c", 0.6),
        "end": 3.6,
        "caps": [
            ('<div class="abs" style="left:70px;top:230px"><div style="display:inline-block;border:10px solid #FFCE1F;padding:14px 30px;font:900 64px Archivo;color:#fff;letter-spacing:6px;text-shadow:0 3px 14px rgba(0,0,0,.5)">PLANET GYM</div><div class="doc" style="font-size:52px;font-style:italic;margin-top:22px">Episode 1: The Wild Gym Owner</div></div>', 0.0, 4.95),
            (sub("Here, we observe the wild gym owner...<br>silently stalking his prey."), 0.4, 4.85),
            ('<div class="abs" style="left:70px;top:250px"><div class="doc" style="font-size:40px;font-weight:800;letter-spacing:4px;color:#FFCE1F">SPECIES</div><div class="doc" style="font-size:66px;font-style:italic">Membrus Expiredus</div><div style="width:280px;height:6px;background:#FFCE1F;margin-top:14px"></div></div>', 5.0, 9.95),
            (sub("The member who forgot to renew. Again."), 5.3, 7.6),
            (sub("A tragic chase."), 7.6, 9.6),
            ('<div class="abs" style="left:70px;top:250px"><div class="doc" style="font-size:40px;font-weight:800;letter-spacing:4px;color:#FFCE1F">SPECIES</div><div class="doc" style="font-size:66px;font-style:italic">Gym Owner (Evolved)</div><div style="width:280px;height:6px;background:#FFCE1F;margin-top:14px"></div></div>', 10.0, 14.95),
            (sub("But this one has evolved. He uses GymBoss..."), 10.2, 12.8),
            (sub("...and renewals simply arrive."), 12.8, 14.9),
            (toast("Renewal received", "₹6,000", "Quarterly plan · auto reminder", 560), 12.9, 14.95),
        ],
        "audio": [("c_1", 0.4), ("sfx_whoosh", 4.85), ("c_2", 5.3), ("sfx_ding", 12.9), ("c_3", 10.2), ("c_4", 15.6)],
    },
}

ENDCARD = """<!doctype html><html><head><meta charset="utf-8">""" + FONTS + """<style>""" + BASE_CSS + """
html,body{background:var(--bg)} #s{position:absolute;inset:0;overflow:hidden;background:var(--bg)}
.lock{font-family:Anton;color:#fff;font-size:150px;line-height:1} .lock b{font-weight:400;color:var(--acc2)}
.cta{display:inline-block;background:var(--acc);color:#0A0712;font:700 50px 'Space Grotesk';padding:28px 56px;border-radius:999px;box-shadow:0 0 0 12px rgba(255,255,255,.15)}
.tag{font:700 34px 'Space Grotesk';letter-spacing:12px;color:rgba(255,255,255,.8)}
</style></head><body><div id="s"></div><script>
const V=new URLSearchParams(location.search).get('v');
const C={a:{bg:'linear-gradient(180deg,#2B1055 0%,#7A2A8C 45%,#FF4FA3 75%,#FFB86B 100%)',acc:'#18D6C9',acc2:'#FFE45C',panda:'panda_wave',line:"You're welcome.",cta:'Start your free trial'},
 b:{bg:'#05100F',acc:'#2DD4BF',acc2:'#2DD4BF',panda:null,line:'Track fees in an app.<br>Save your sanity.',cta:null},
 c:{bg:'linear-gradient(180deg,#9FE3D0 0%,#FFD9B8 60%,#FFB38A 100%)',acc:'#0A0712',acc2:'#7C3AED',panda:'panda_cash',line:'GymBoss got you.',cta:'Start your free trial'}}[V];
document.documentElement.style.setProperty('--bg',C.bg);document.documentElement.style.setProperty('--acc',C.acc);document.documentElement.style.setProperty('--acc2',C.acc2);
const s=document.getElementById('s');
const mk=(h,css)=>{const e=document.createElement('div');e.className='abs';e.innerHTML=h;Object.assign(e.style,css);s.appendChild(e);return e};
const lock=mk('<div style="text-align:center"><div class="lock">GYMBOSS<b>_VVO</b></div><div class="tag" style="margin-top:18px">MANAGE · GROW · REPEAT</div></div>',{left:0,right:0,top:V==='b'?'640px':'230px'});
const line=mk(`<div style="text-align:center;font:700 ${V==='b'?66:80}px 'Space Grotesk';color:${V==='c'?'#0A0712':'#fff'};line-height:1.15">${C.line}</div>`,{left:0,right:0,top:V==='b'?'960px':'520px'});
const cta=C.cta?mk(`<div style="text-align:center"><div class="cta" style="${V==='c'?'color:#fff':''}">${C.cta}</div></div>`,{left:0,right:0,top:'680px'}):null;
const p=C.panda?mk(`<img src="../assets/cut/${C.panda}.png" style="height:980px">`,{left:0,right:0,top:'900px',textAlign:'center',transformOrigin:'50% 100%'}):null;
if(V==='c'){lock.querySelector('.lock').style.color='#0A0712';lock.querySelector('.tag').style.color='#3B2F5C'}
const cl=(x)=>Math.max(0,Math.min(1,x)),eb=(x)=>{const c1=1.8,c3=c1+1;return 1+c3*Math.pow(x-1,3)+c1*Math.pow(x-1,2)};
window.render=(t)=>{const q=cl(t/0.5);lock.style.transform=`scale(${0.6+0.4*eb(q)})`;lock.style.opacity=q;
 const q2=cl((t-0.35)/0.4);line.style.opacity=q2;line.style.transform=`translateY(${(1-q2)*40}px)`;
 if(cta){const q3=cl((t-0.7)/0.45);cta.style.opacity=q3>0?1:0;cta.style.transform=`scale(${q3>0?eb(q3)*(1+0.03*Math.abs(Math.sin(t*5))):0})`}
 if(p){const q4=cl((t-0.1)/0.6);p.style.transform=`translateY(${(1-eb(q4))*900-Math.abs(Math.sin(t*4.5))*14}px)`}};
window.render(0);
</script></body></html>"""


async def build_visuals(key, cfg):
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        page = await b.new_page(viewport={"width": 1080, "height": 1920})
        for i, (html, _, _) in enumerate(cfg["caps"] + [(WM, 0, 0)]):
            await page.set_content(f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{BASE_CSS}</style></head><body>{html}</body></html>', wait_until="networkidle")
            await page.evaluate("document.fonts.ready")
            await page.screenshot(path=str(OV / f"{key}_{i}.png"), omit_background=True)
        (ROOT / "endcard.html").write_text(ENDCARD)
        await page.goto(f"file://{ROOT}/endcard.html?v={key}", wait_until="networkidle")
        await page.evaluate("document.fonts.ready")
        await page.wait_for_timeout(500)
        end = OUT / f"end_{key}.mp4"
        proc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                                 "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", str(end)], stdin=subprocess.PIPE)
        for f in range(int(cfg["end"] * FPS)):
            await page.evaluate(f"render({f / FPS})")
            proc.stdin.write(await page.screenshot(type="jpeg", quality=93))
        proc.stdin.close()
        proc.wait()
        await b.close()


def read_wav(path):
    raw = path.read_bytes()
    with wave.open(str(path)) as w:
        sr = w.getframerate()
    x = np.frombuffer(raw[44:][: (len(raw) - 44) // 2 * 2], dtype=np.int16).astype(np.float32) / 32768
    if sr != SR:
        x = np.interp(np.arange(int(len(x) / sr * SR)) / SR, np.arange(len(x)) / sr, x)
    return x


def mix(key, cfg, total, dst):
    n = int(total * SR)
    name, mg = cfg["music"]
    music = read_wav(ROOT / "audio" / f"{name}.wav")
    music = np.pad(music, (0, max(0, n - len(music))))[:n]
    voice, fx = np.zeros(n, np.float32), np.zeros(n, np.float32)
    for slug, at in cfg["audio"]:
        x = read_wav(ROOT / "audio" / f"{slug}.wav")
        i = int(at * SR)
        x = x[: n - i]
        (fx if slug.startswith("sfx") else voice)[i:i + len(x)] += x
    if voice.any():
        voice = voice / np.abs(voice).max() * 0.95
    act = np.convolve(np.abs(voice), np.ones(2205) / 2205, mode="same") > 0.01
    duck = np.convolve(act.astype(np.float32), np.ones(8820) / 8820, mode="same")
    out = music * (mg - (mg * 0.7) * np.clip(duck * 1.5, 0, 1)) + voice + fx * 0.8
    fade = int(0.8 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out = np.tanh(out * 1.1) / np.tanh(1.1)
    out = out / (np.abs(out).max() + 1e-9) * 0.95
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


def compose(key, cfg):
    clips = cfg["clips"]
    total = 5.0 * len(clips) + cfg["end"]
    args = [FF, "-y", "-loglevel", "error"]
    for c in clips:
        args += ["-i", str(ROOT / "clips" / f"{c}.mp4")]
    args += ["-i", str(OUT / f"end_{key}.mp4")]
    caps = cfg["caps"] + [(WM, 0.0, 15.0)]
    for i in range(len(caps)):
        args += ["-loop", "1", "-framerate", str(FPS), "-t", str(total), "-i", str(OV / f"{key}_{i}.png")]
    audio = OUT / f"{key}_mix.wav"
    mix(key, cfg, total, audio)
    args += ["-i", str(audio)]
    fc = []
    for i in range(len(clips)):
        fc.append(f"[{i}:v]trim=0:5,setpts=PTS-STARTPTS,fps={FPS},crop=ih*9/16:ih,scale=1080:1920:flags=lanczos,setsar=1,{cfg['grade']}[v{i}]")
    e = len(clips)
    fc.append(f"[{e}:v]fps={FPS},setsar=1[v{e}]")
    fc.append("".join(f"[v{i}]" for i in range(e + 1)) + f"concat=n={e + 1}:v=1:a=0,format=yuv420p[base]")
    last = "base"
    for k, (_, st, en) in enumerate(caps):
        idx = e + 1 + k
        fin = f"fade=in:st={st}:d=0.18:alpha=1," if st > 0 else ""
        fc.append(f"[{idx}:v]format=rgba,{fin}fade=out:st={max(st, en - 0.15)}:d=0.15:alpha=1[o{k}]")
        fc.append(f"[{last}][o{k}]overlay=0:0:enable='between(t,{st},{en})'[b{k}]")
        last = f"b{k}"
    aidx = e + 1 + len(caps)
    dst = OUT / f"{cfg['name']}.mp4"
    args += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", f"{aidx}:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-t", str(total), "-movflags", "+faststart", str(dst)]
    subprocess.run(args, check=True)
    audio.unlink()
    print("DONE", dst, total, flush=True)


if __name__ == "__main__":
    for key in sys.argv[1:] or list(REELS):
        asyncio.run(build_visuals(key, REELS[key]))
        compose(key, REELS[key])
