import asyncio
import subprocess
import sys
from pathlib import Path

import numpy as np

from render_series import BASE_CSS, CHECK, FF, FONTS, OUT, OV, SR, mix as _unused, read_wav  # noqa: F401
from playwright.async_api import async_playwright
import wave

ROOT = Path(__file__).parent
FPS = 24
D, X = 5.0, 0.25
MODEL = "v26pro"
S = [k * (D - X) for k in range(5)]

PG_CSS = BASE_CSS + """
.badge{display:inline-block;border:8px solid #FFCE1F;padding:10px 24px;font:900 50px Archivo;color:#fff;letter-spacing:6px;text-shadow:0 3px 14px rgba(0,0,0,.5)}
.ept{font-family:'Playfair Display';font-style:italic;font-size:44px;color:#fff;margin-top:14px;text-shadow:0 3px 16px rgba(0,0,0,.7)}
.sp1{font-family:'Playfair Display';font-size:36px;font-weight:800;letter-spacing:5px;color:#FFCE1F;text-shadow:0 2px 10px rgba(0,0,0,.6)}
.sp2{font-family:'Playfair Display';font-size:64px;font-style:italic;color:#fff;text-shadow:0 3px 16px rgba(0,0,0,.7)}
.bar{width:260px;height:6px;background:#FFCE1F;margin-top:12px}
.sub{font-size:50px}
"""


def hook(t):
    return f'<div class="abs c" style="top:230px"><span class="tt" style="font-size:52px">{t}</span></div>'


def title(n, name):
    return f'<div class="abs" style="left:70px;top:1180px"><div class="badge">PLANET GYM</div><div class="ept">Episode {n}: {name}</div></div>'


def species(a, b):
    return f'<div class="abs" style="left:70px;top:250px"><div class="sp1">{a}</div><div class="sp2">{b}</div><div class="bar"></div></div>'


def sub(t):
    return f'<div class="abs c sub" style="top:1440px">{t}</div>'


def toast(title_, amt, who, y=560):
    return f'<div class="abs" style="left:110px;top:{y}px;width:860px"><div class="toast">{CHECK}<div><div class="t1">{title_}</div><div class="amt">{amt}</div><div class="t2">{who}</div></div></div></div>'


WM = '<div class="abs wm" style="right:60px;top:96px">GYMBOSS<b>_VVO</b></div>'

EPS = {
    1: {
        "name": "PlanetGym_Ep1_TheWildGymOwner", "clips": ["e1_1", "e1_2", "e1_3", "e1_4"], "grade": "eq=saturation=1.08:contrast=1.03,vignette=PI/6",
        "music": ("pg_music_1", 0.42), "amb": ("pg_amb_1", 0.35),
        "end": {"bg": "linear-gradient(180deg,#9FE3D0 0%,#FFD9B8 60%,#FFB38A 100%)", "ink": "#0A0712", "acc": "#0A0712", "acc2": "#7C3AED", "panda": "panda_cash", "line": "GymBoss got you.", "cta": True}, "end_dur": 4.2,
        "caps": [
            (hook("POV: you run a gym"), 0, 0.0, 4.75), (title(1, "The Wild Gym Owner"), 0, 0.0, 4.75),
            (sub("Here, we observe the wild gym owner...<br>silently stalking his prey."), 0, 0.2, 4.6),
            (species("SPECIES", "Membrus Expiredus"), 1, 0.15, 4.75), (sub("The member who forgot to renew. Again.<br>A tragic chase."), 1, 0.25, 4.6),
            (sub("Alas. The prey escapes...<br>as it does every month."), 2, 0.25, 4.6),
            (species("SPECIES", "Gym Owner (Evolved)"), 3, 0.15, 4.95), (sub("But this one has evolved. He uses GymBoss...<br>and renewals simply arrive."), 3, 0.2, 4.95),
            (toast("Renewal received", "₹6,000", "Quarterly plan · auto reminder"), 3, 2.6, 4.95),
        ],
        "audio": [("n1_1", 0, 0.2), ("n1_2", 1, 0.25), ("sfx_vineboom", 2, 0.3), ("n1_3", 2, 0.6), ("n1_4", 3, 0.2), ("sfx_ding", 3, 2.6), ("n_cta", 4, 0.7)],
    },
    2: {
        "name": "PlanetGym_Ep2_TheJanuaryMigration", "clips": ["e2_1", "e2_2", "e2_3", "e2_4"], "grade": "eq=saturation=1.05:contrast=1.04,vignette=PI/6",
        "music": ("pg_music_2", 0.45), "amb": ("pg_amb_2", 0.4),
        "end": {"bg": "linear-gradient(180deg,#0B1B3A 0%,#12485E 55%,#3FB8AF 100%)", "ink": "#fff", "acc": "#FFCE1F", "acc2": "#7DF9E2", "panda": "panda_wave", "line": "Brought to you by", "cta": False}, "end_dur": 3.8,
        "caps": [
            (hook("every gym in January vs February"), 0, 0.0, 4.75), (title(2, "The January Migration"), 0, 0.0, 4.75),
            (sub("Every January...<br>the great migration begins."), 0, 0.3, 4.6),
            (species("SPECIES", "Resolutionus Januarius"), 1, 0.15, 4.75), (sub("They arrive in thousands.<br>New shoes. Bold promises."), 1, 0.25, 4.6),
            (species("TIMESTAMP", "February 3rd"), 2, 0.15, 4.75), (sub("By February... silence.<br>Only the tumbleweed remains."), 2, 0.3, 4.6),
            (species("SPECIES", "Gym Owner (Patient)"), 3, 0.15, 4.95), (sub("But the gym owner is patient.<br>Only eleven months to go."), 3, 0.25, 4.95),
        ],
        "audio": [("n2_1", 0, 0.3), ("n2_2", 1, 0.25), ("n2_3", 2, 0.3), ("n2_4", 3, 0.25), ("n_brand", 4, 0.6)],
    },
    3: {
        "name": "PlanetGym_Ep3_TheGhostMember", "clips": ["e3_1", "e3_2", "e3_3", "e3_4"], "grade": "eq=saturation=1.08:contrast=1.05,vignette=PI/5",
        "music": ("pg_music_3", 0.45), "amb": ("pg_amb_3", 0.4),
        "end": {"bg": "linear-gradient(180deg,#120A2E 0%,#2E1A6B 55%,#6D4BD8 100%)", "ink": "#fff", "acc": "#C6FF3D", "acc2": "#A78BFA", "panda": "panda_excited", "line": "Even ghosts renew.", "cta": True}, "end_dur": 4.2,
        "caps": [
            (hook("that one member who paid once and vanished"), 0, 0.0, 4.75), (title(3, "The Ghost Member"), 0, 0.0, 4.75),
            (sub("Deep in the forest lives<br>the most elusive creature of all."), 0, 0.25, 4.6),
            (species("SPECIES", "Ghostus Membrus"), 1, 0.15, 4.75), (sub("The ghost member.<br>Paid once. Never seen again."), 1, 0.3, 4.6),
            (sub("The owner gives chase.<br>But ghosts... cannot be caught."), 2, 0.25, 4.6),
            (species("SPECIES", "Gym Owner (Evolved)"), 3, 0.15, 4.95), (sub("Unless you use GymBoss.<br>One reminder, and even ghosts renew."), 3, 0.2, 4.95),
            (toast("Renewal received", "₹3,000", "Monthly plan · after 1 reminder"), 3, 2.4, 4.95),
        ],
        "audio": [("n3_1", 0, 0.25), ("sfx_dundun", 1, 0.0), ("n3_2", 1, 0.3), ("n3_3", 2, 0.25), ("n3_4", 3, 0.2), ("sfx_ding", 3, 2.4), ("n_cta", 4, 0.7)],
    },
    4: {
        "name": "PlanetGym_Ep4_TheProteinShakeAddict", "clips": ["e4_1", "e4_2", "e4_3", "e4_4"], "grade": "eq=saturation=1.06:contrast=1.03,vignette=PI/6",
        "music": ("pg_music_4", 0.42), "amb": ("pg_amb_4", 0.35),
        "end": {"bg": "linear-gradient(180deg,#FF5FA8 0%,#FF9A7A 45%,#2ED3C6 100%)", "ink": "#fff", "acc": "#FFE45C", "acc2": "#2B0F4D", "panda": "panda_flex", "line": "Brought to you by", "cta": False}, "end_dur": 3.8,
        "caps": [
            (hook("every gym has THIS guy"), 0, 0.0, 4.75), (title(4, "The Protein Shake Addict"), 0, 0.0, 4.75),
            (sub("By the chocolate falls,<br>we find the rare shake addict."), 0, 0.25, 4.6),
            (species("SPECIES", "Shakus Maximus"), 1, 0.15, 4.75), (sub("His ritual is sacred.<br>Shake. Shake. Shake again."), 1, 0.25, 4.6),
            (sub("Our owner takes his very first sip...<br>and everything changes."), 2, 0.2, 4.6),
            (species("SPECIES", "Gym Owner (Compromised)"), 3, 0.15, 4.95), (sub("The addiction... is contagious."), 3, 0.3, 4.95),
        ],
        "audio": [("n4_1", 0, 0.25), ("n4_2", 1, 0.25), ("n4_3", 2, 0.2), ("sfx_vineboom", 2, 2.6), ("sfx_slurp", 3, 0.1), ("n4_4", 3, 0.3), ("n_brand", 4, 0.6)],
    },
}

ENDCARD = """<!doctype html><html><head><meta charset="utf-8">""" + FONTS + """<style>""" + PG_CSS + """
#s{position:absolute;inset:0;overflow:hidden}
.lock{font-family:Anton;font-size:150px;line-height:1} .lock b{font-weight:400}
.cta{display:inline-block;font:700 50px 'Space Grotesk';padding:28px 56px;border-radius:999px;box-shadow:0 0 0 12px rgba(255,255,255,.18)}
.tag{font:700 32px 'Space Grotesk';letter-spacing:12px;text-shadow:0 2px 12px rgba(0,0,0,.45)}
</style></head><body><div id="s"></div><script>
const C=JSON.parse(decodeURIComponent(location.hash.slice(1)));
const s=document.getElementById('s');s.style.background=C.bg;
const mk=(h,css)=>{const e=document.createElement('div');e.className='abs';e.innerHTML=h;Object.assign(e.style,css);s.appendChild(e);return e};
const badge=mk('<div style="text-align:center"><div class="badge" style="color:'+C.ink+';border-color:'+C.acc+'">PLANET GYM</div></div>',{left:0,right:0,top:'200px'});
const line=mk('<div style="text-align:center;font:700 54px Space Grotesk;color:'+C.ink+'">'+C.line+'</div>',{left:0,right:0,top:C.cta?'640px':'360px'});
const lock=mk('<div style="text-align:center"><div class="lock" style="color:'+C.ink+'">GYMBOSS<b style="color:'+C.acc2+'">_VVO</b></div><div class="tag" style="margin-top:16px;color:'+C.ink+'">MANAGE · GROW · REPEAT</div></div>',{left:0,right:0,top:C.cta?'360px':'450px'});
const cta=C.cta?mk('<div style="text-align:center"><div class="cta" style="background:'+C.acc+';color:'+(C.acc==='#0A0712'?'#fff':'#0A0712')+'">Start your free trial</div></div>',{left:0,right:0,top:'760px'}):null;
const p=mk('<img src="../assets/cut/'+C.panda+'.png" style="height:960px">',{left:0,right:0,top:'930px',textAlign:'center'});
const cl=(x)=>Math.max(0,Math.min(1,x)),eb=(x)=>{const c1=1.8,c3=c1+1;return 1+c3*Math.pow(x-1,3)+c1*Math.pow(x-1,2)};
window.render=(t)=>{const q0=cl(t/0.4);badge.style.opacity=q0;badge.style.transform='translateY('+(1-q0)*-30+'px)';
 const q=cl((t-0.2)/0.5);lock.style.opacity=q;lock.style.transform='scale('+(0.6+0.4*eb(q))+')';
 const q2=cl((t-(C.cta?0.5:0.1))/0.4);line.style.opacity=q2;line.style.transform='translateY('+(1-q2)*30+'px)';
 if(cta){const q3=cl((t-0.8)/0.45);cta.style.opacity=q3>0?1:0;cta.style.transform='scale('+(q3>0?eb(q3)*(1+0.03*Math.abs(Math.sin(t*5))):0)+')'}
 const q4=cl((t-0.15)/0.6);p.style.transform='translateY('+((1-eb(q4))*900-Math.abs(Math.sin(t*4.5))*14)+'px)'};
window.render(0);
</script></body></html>"""


async def visuals(n, cfg):
    import json
    from urllib.parse import quote
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        page = await b.new_page(viewport={"width": 1080, "height": 1920})
        for i, (html, *_r) in enumerate(cfg["caps"] + [(WM,)]):
            await page.set_content(f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{PG_CSS}</style></head><body>{html}</body></html>', wait_until="networkidle")
            await page.evaluate("document.fonts.ready")
            await page.screenshot(path=str(OV / f"pg{n}_{i}.png"), omit_background=True)
        (ROOT / "pg_endcard.html").write_text(ENDCARD)
        await page.goto(f"file://{ROOT}/pg_endcard.html#{quote(json.dumps(cfg['end']))}", wait_until="networkidle")
        await page.evaluate("document.fonts.ready")
        await page.wait_for_timeout(400)
        dst = OUT / f"pg_end_{n}.mp4"
        proc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                                 "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(dst)], stdin=subprocess.PIPE)
        for f in range(int(cfg["end_dur"] * FPS)):
            await page.evaluate(f"render({f / FPS})")
            proc.stdin.write(await page.screenshot(type="jpeg", quality=95))
        proc.stdin.close()
        proc.wait()
        await b.close()


def audio_mix(cfg, total, dst):
    n = int(total * SR)
    fit = lambda x: np.pad(x, (0, max(0, n - len(x))))[:n]
    music = fit(read_wav(ROOT / "audio" / f"{cfg['music'][0]}.wav"))
    amb = fit(read_wav(ROOT / "audio" / f"{cfg['amb'][0]}.wav"))
    amb[int(S[4] * SR):] *= np.linspace(1, 0, n - int(S[4] * SR))
    voice, fx = np.zeros(n, np.float32), np.zeros(n, np.float32)
    for slug, shot, rel in cfg["audio"]:
        x = read_wav(ROOT / "audio" / f"{slug}.wav")
        i = int((S[shot] + rel) * SR)
        x = x[: n - i]
        (fx if slug.startswith("sfx") else voice)[i:i + len(x)] += x
    voice = voice / np.abs(voice).max() * 0.95
    act = np.convolve(np.abs(voice), np.ones(2205) / 2205, mode="same") > 0.01
    duck = np.clip(np.convolve(act.astype(np.float32), np.ones(8820) / 8820, mode="same") * 1.5, 0, 1)
    mg, ag = cfg["music"][1], cfg["amb"][1]
    out = music * mg * (1 - 0.6 * duck) + amb * ag * (1 - 0.4 * duck) + voice + fx * 0.6
    fade = int(0.8 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out = np.tanh(out * 1.1) / np.tanh(1.1)
    out = out / (np.abs(out).max() + 1e-9) * 0.93
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


def compose(n, cfg):
    total = S[4] + cfg["end_dur"]
    args = [FF, "-y", "-loglevel", "error"]
    for c in cfg["clips"]:
        args += ["-i", str(ROOT / "pg_clips" / f"{c}_{MODEL}.mp4")]
    args += ["-i", str(OUT / f"pg_end_{n}.mp4")]
    caps = [(h, S[s] + a, S[s] + b) for h, s, a, b in cfg["caps"]] + [(WM, 0.0, S[4] + X)]
    for i in range(len(caps)):
        args += ["-loop", "1", "-framerate", str(FPS), "-t", str(total), "-i", str(OV / f"pg{n}_{i}.png")]
    aud = OUT / f"pg{n}_mix.wav"
    audio_mix(cfg, total, aud)
    args += ["-i", str(aud)]
    fc = [f"[{i}:v]trim=0:{D},setpts=PTS-STARTPTS,fps={FPS},crop=ih*9/16:ih,scale=1080:1920:flags=lanczos,unsharp=5:5:0.45,setsar=1,{cfg['grade']},format=yuv420p[v{i}]" for i in range(4)]
    fc.append(f"[4:v]fps={FPS},setsar=1,format=yuv420p[v4]")
    last = "v0"
    for k in range(1, 5):
        fc.append(f"[{last}][v{k}]xfade=transition=fade:duration={X}:offset={S[k]:.3f}[x{k}]")
        last = f"x{k}"
    for k, (_, st, en) in enumerate(caps):
        idx = 5 + k
        fin = f"fade=in:st={st:.3f}:d=0.2:alpha=1," if st > 0 else ""
        fc.append(f"[{idx}:v]format=rgba,{fin}fade=out:st={max(st, en - 0.18):.3f}:d=0.18:alpha=1[o{k}]")
        fc.append(f"[{last}][o{k}]overlay=0:0:enable='between(t,{st:.3f},{en:.3f})'[b{k}]")
        last = f"b{k}"
    dst = OUT / f"{cfg['name']}.mp4"
    args += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", f"{5 + len(caps)}:a", "-c:v", "libx264", "-preset", "slow", "-crf", "19",
             "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart", str(dst)]
    subprocess.run(args, check=True)
    aud.unlink()
    print("DONE", dst, round(total, 2), flush=True)


if __name__ == "__main__":
    for n in [int(a) for a in sys.argv[1:]] or list(EPS):
        asyncio.run(visuals(n, EPS[n]))
        compose(n, EPS[n])
