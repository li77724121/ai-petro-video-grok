#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地零依赖宠物短视频渲染器：PIL 逐帧绘制 + ffmpeg 编码。

不调用任何外部 API，不需要下载模型权重（纯本地程序化渲染）。
用法：python render_pet_video.py
输出：~/Desktop/M1hermes/media/pet-ai-cartoon.mp4
"""

import math
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
DUR = 10.0
SS = 2  # 猫咪图层超采样倍数

OUT_DIR = os.path.expanduser("~/Desktop/M1hermes/media/pet-cartoon")
FRAME_DIR = os.path.join(OUT_DIR, "frames")
VIDEO = os.path.expanduser("~/Desktop/M1hermes/media/pet-ai-cartoon.mp4")

FONT_CN = "/System/Library/Fonts/Supplemental/Songti.ttc"
FONT_EN = "/System/Library/Fonts/Helvetica.ttc"

ORANGE = (247, 168, 92, 255)
ORANGE_D = (226, 137, 61, 255)
ORANGE_L = (252, 200, 150, 255)
CREAM = (255, 240, 219, 255)
PAW = (252, 228, 200, 255)
PINK = (255, 168, 176, 255)
DARK = (58, 36, 30, 255)
LINE = (200, 130, 78, 255)


def font(size, cn=True, index=1):
    path = FONT_CN if cn else FONT_EN
    try:
        return ImageFont.truetype(path, size, index=index)
    except Exception:
        return ImageFont.load_default()


def make_bg():
    """垂直渐变背景 + 光晕 + 散景 + 暗角，预计算一次。"""
    top = np.array([22, 14, 48], dtype=np.float32)
    bot = np.array([58, 30, 92], dtype=np.float32)
    ramp = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    arr = (top[None, None, :] * (1 - ramp) + bot[None, None, :] * ramp)
    arr = np.repeat(arr, W, axis=1)
    bg = Image.fromarray(arr.astype(np.uint8), "RGB")

    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse(
        [W * 0.5 - 520, H * 0.30, W * 0.5 + 520, H * 0.30 + 1040], fill=120
    )
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    halo = Image.new("RGB", (W, H), (120, 90, 220))
    bg = Image.composite(halo, bg, glow.point(lambda v: int(v * 0.55)))

    rng = np.random.default_rng(7)
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(dots)
    for _ in range(46):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(6, 46)
        a = int(rng.uniform(10, 46))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 214, 170, a))
    dots = dots.filter(ImageFilter.GaussianBlur(2.2))
    bg = Image.alpha_composite(bg.convert("RGBA"), dots).convert("RGB")

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (xx - W / 2) / (W / 2)
    ny = (yy - H / 2) / (H / 2)
    vig = np.clip(1.0 - 0.55 * (nx ** 2 + ny ** 2) ** 1.15, 0.45, 1.0)
    bg_arr = np.asarray(bg, dtype=np.float32) * vig[:, :, None]
    return Image.fromarray(bg_arr.clip(0, 255).astype(np.uint8), "RGB")


_LIGHT_MASK = None


def light_mask():
    global _LIGHT_MASK
    if _LIGHT_MASK is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        cx, cy = W * 0.42, H * 0.40
        sx, sy = W * 0.42, H * 0.34
        m = np.exp(-(((xx - cx) ** 2) / (2 * sx ** 2) + ((yy - cy) ** 2) / (2 * sy ** 2)))
        _LIGHT_MASK = Image.fromarray((m * 46).clip(0, 255).astype(np.uint8), "L")
    return _LIGHT_MASK


def lerp(a, b, u):
    return tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(len(a)))


def draw_cat(t):
    """在超采样图层上绘制卡通猫，t 为秒。返回 (W,H) RGBA。"""
    layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    S = SS

    cx, cy = W * S * 0.5, H * S * 0.60
    breath = 1.0 + 0.018 * math.sin(2 * math.pi * t / 2.2)
    bob = 14 * S * math.sin(2 * math.pi * t / 2.8)

    # ---------- 尾巴（软渐变，无硬环纹）----------
    wag = math.sin(2 * math.pi * t / 1.1)
    base = (cx + 200 * S, cy + 250 * S + bob)
    tail_pts = []
    for i in range(24):
        u = i / 23
        ang = -0.9 + 1.9 * u + 0.5 * wag * u
        rad = 260 * S * u
        tail_pts.append(
            (base[0] + rad * math.cos(ang * 0.9 + 0.6), base[1] - rad * math.sin(ang + 0.2))
        )
    d.ellipse([base[0] - 58 * S, base[1] - 58 * S, base[0] + 58 * S, base[1] + 58 * S], fill=ORANGE_D)

    def tail_polygon(widths, fill):
        """按路径法线偏移生成单条闭合多边形，避免多段粗线的接头条纹。"""
        left, right = [], []
        n = len(tail_pts)
        for i in range(n):
            p0 = tail_pts[max(0, i - 1)]
            p1 = tail_pts[min(n - 1, i + 1)]
            tx, ty = p1[0] - p0[0], p1[1] - p0[1]
            ln = math.hypot(tx, ty) or 1.0
            nx, ny = -ty / ln, tx / ln
            w = widths[i]
            left.append((tail_pts[i][0] + nx * w, tail_pts[i][1] + ny * w))
            right.append((tail_pts[i][0] - nx * w, tail_pts[i][1] - ny * w))
        d.polygon(left + list(reversed(right)), fill=fill)

    n_pts = len(tail_pts)
    tail_polygon([(46 - 16 * (i / (n_pts - 1))) * S / 2 for i in range(n_pts)], ORANGE_D)
    # 内层柔光带（同法线偏移，仍是一条多边形）
    tail_polygon([(26 - 14 * (i / (n_pts - 1))) * S / 2 for i in range(n_pts)], (250, 186, 122, 110))
    tip = tail_pts[-1]
    d.ellipse([tip[0] - 19 * S, tip[1] - 19 * S, tip[0] + 19 * S, tip[1] + 19 * S], fill=CREAM)

    # ---------- 后腿（坐姿臀部，补足支撑感）----------
    for side in (-1, 1):
        hx2 = cx + side * 176 * S
        d.ellipse([hx2 - 104 * S, cy + 150 * S + bob, hx2 + 104 * S, cy + 400 * S + bob],
                  fill=ORANGE, outline=LINE, width=int(6 * S))

    # ---------- 身体 ----------
    body_w = 420 * S * breath
    body_h = 400 * S
    body_box = [cx - body_w / 2, cy + 40 * S + bob, cx + body_w / 2, cy + 40 * S + body_h + bob]
    d.ellipse(body_box, fill=ORANGE, outline=LINE, width=int(6 * S))
    # 肚皮（上移，不再与爪子同色相接）
    d.ellipse([cx - body_w * 0.29, cy + 130 * S + bob, cx + body_w * 0.29, cy + 322 * S + bob],
              fill=CREAM)

    # ---------- 胡须（先画，腮红会盖住根部，杜绝穿模）----------
    hx = cx + 12 * S * math.sin(2 * math.pi * t / 3.4)
    hy = cy - 130 * S + bob
    for side in (-1, 1):
        for k, dy in enumerate((-8, 18, 44)):
            x0 = hx + side * 170 * S
            y0 = hy + 72 * S + dy * S
            wob = 8 * S * math.sin(2 * math.pi * t / 1.9 + k)
            p1 = (x0 + side * 74 * S, y0 - 14 * S + wob * 0.6)
            p2 = (x0 + side * 142 * S, y0 - 36 * S + wob)
            d.line([(x0, y0), p1], fill=(255, 245, 230, 175), width=int(5 * S))
            d.line([p1, p2], fill=(255, 245, 230, 155), width=int(4 * S))

    # ---------- 前爪（比肚皮更深一档 + 阴影，明确分层）----------
    for side in (-1, 1):
        px = cx + side * 118 * S
        d.ellipse([px - 66 * S, cy + 336 * S + bob, px + 66 * S, cy + 428 * S + bob],
                  fill=PAW, outline=LINE, width=int(8 * S))
        for k in (-1, 0, 1):
            d.line([(px + k * 20 * S, cy + 372 * S + bob), (px + k * 27 * S, cy + 404 * S + bob)],
                   fill=(206, 158, 118, 255), width=int(5 * S))

    # ---------- 耳朵 ----------
    head_r = 232 * S
    ear_tw = 0.06 * math.sin(2 * math.pi * t / 1.6 + 1.0)
    for side in (-1, 1):
        bx = hx + side * head_r * 0.62
        by = hy - head_r * 0.62
        tip_pt = (bx + side * head_r * 0.42, by - head_r * 0.66 + 40 * S * ear_tw * side)
        outer = [(bx - side * 66 * S, by + 30 * S), tip_pt, (bx + side * 74 * S, by + 96 * S)]
        d.polygon(outer, fill=ORANGE)
        gx = sum(p[0] for p in outer) / 3.0
        gy = sum(p[1] for p in outer) / 3.0
        # 内耳向耳尖方向偏移一点，避免贴边
        tx = gx + (tip_pt[0] - gx) * 0.18
        ty = gy + (tip_pt[1] - gy) * 0.18
        k2 = 0.50
        inner = [(tx + (p[0] - gx) * k2, ty + (p[1] - gy) * k2) for p in outer]
        d.polygon(inner, fill=PINK)

    d.ellipse([hx - head_r, hy - head_r * 0.92, hx + head_r, hy + head_r * 0.92], fill=ORANGE)

    # 额头花纹（带弧度的短笔画）
    for off in (-46, 0, 46):
        x0 = hx + off * S
        y0 = hy - head_r * 0.86
        y1 = hy - head_r * 0.60
        mx = x0 + off * 0.16 * S
        d.line([(x0, y0), (mx, (y0 + y1) / 2)], fill=ORANGE_D, width=int(12 * S))
        d.line([(mx, (y0 + y1) / 2), (x0 + off * 0.04 * S, y1)], fill=ORANGE_D, width=int(8 * S))

    # 口鼻区
    d.ellipse([hx - 128 * S, hy + 30 * S, hx + 128 * S, hy + 158 * S], fill=CREAM)

    # ---------- 眼睛（同向注视，共用一个视线偏移）----------
    gaze_x, gaze_y = -10 * S, 6 * S
    period = 2.6
    blink = (t % period) < 0.14
    for side in (-1, 1):
        ex = hx + side * 96 * S
        ey = hy - 18 * S
        if blink:
            d.arc([ex - 52 * S, ey - 26 * S, ex + 52 * S, ey + 42 * S], 200, 340,
                  fill=DARK, width=int(13 * S))
        else:
            d.ellipse([ex - 54 * S, ey - 62 * S, ex + 54 * S, ey + 62 * S], fill=DARK)
            d.ellipse([ex - 36 * S + gaze_x, ey - 42 * S + gaze_y,
                       ex + 36 * S + gaze_x, ey + 42 * S + gaze_y], fill=(96, 176, 158, 255))
            d.ellipse([ex - 19 * S + gaze_x, ey - 25 * S + gaze_y,
                       ex + 19 * S + gaze_x, ey + 25 * S + gaze_y], fill=(16, 20, 24, 255))
            d.ellipse([ex - 32 * S, ey - 48 * S, ex - 8 * S, ey - 20 * S], fill=(255, 255, 255, 235))
            d.ellipse([ex + 8 * S, ey + 4 * S, ex + 20 * S, ey + 16 * S], fill=(255, 255, 255, 150))

    # 腮红（后画，盖住胡须根部）
    for side in (-1, 1):
        bx = hx + side * 150 * S
        d.ellipse([bx - 46 * S, hy + 44 * S, bx + 46 * S, hy + 102 * S], fill=(255, 150, 160, 135))

    # 鼻子 + 嘴
    d.polygon([(hx - 26 * S, hy + 46 * S), (hx + 26 * S, hy + 46 * S), (hx, hy + 76 * S)], fill=PINK)
    mouth_open = 0.5 + 0.5 * math.sin(2 * math.pi * t / 2.0)
    if mouth_open > 0.72:
        d.ellipse([hx - 34 * S, hy + 84 * S, hx + 34 * S, hy + 138 * S], fill=(150, 66, 72, 255))
        d.ellipse([hx - 22 * S, hy + 112 * S, hx + 22 * S, hy + 138 * S], fill=(240, 130, 140, 255))
    else:
        d.arc([hx - 60 * S, hy + 62 * S, hx, hy + 112 * S], 20, 160, fill=DARK, width=int(9 * S))
        d.arc([hx, hy + 62 * S, hx + 60 * S, hy + 112 * S], 20, 160, fill=DARK, width=int(9 * S))

    out = layer.resize((W, H), Image.LANCZOS)
    arr = np.asarray(out).astype(np.float32)
    m = (np.asarray(light_mask()).astype(np.float32) / 255.0 * 0.40)[:, :, None]
    arr[:, :, :3] = arr[:, :, :3] * (1 - m) + 255.0 * 0.92 * m
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")


def draw_hearts(frame, t):
    """漂浮爱心粒子（2x 超采样抗锯齿）。"""
    S2 = 2
    layer = Image.new("RGBA", (W * S2, H * S2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = np.random.default_rng(21)
    for i in range(10):
        born = rng.uniform(0, DUR)
        x0 = rng.uniform(150, 930)
        sc = rng.uniform(0.5, 1.1)
        speed = rng.uniform(120, 230)
        age = (t - born) % DUR
        y = H * 0.95 - speed * age
        alpha = int(190 * max(0.0, min(1.0, (y - 220) / 900)))
        if alpha <= 4:
            continue
        x = x0 + 26 * math.sin(age * 1.6 + i)
        r = 22 * sc
        col = (255, 120, 160, alpha)
        X, Y, R = x * S2, y * S2, r * S2
        d.ellipse([X - R, Y - R * 0.9, X, Y + R * 0.1], fill=col)
        d.ellipse([X, Y - R * 0.9, X + R, Y + R * 0.1], fill=col)
        d.polygon([(X - R, Y - R * 0.15), (X + R, Y - R * 0.15), (X, Y + R * 1.25)], fill=col)
    return Image.alpha_composite(frame, layer.resize((W, H), Image.LANCZOS))


def draw_text(frame, t):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f_title = font(96, cn=True, index=3)
    f_sub = font(46, cn=True, index=3)
    f_tag = font(34, cn=False, index=0)

    a1 = max(0.0, min(1.0, (t - 0.4) / 0.9))
    if a1 > 0:
        y = 250 - 20 * (1 - a1)
        txt = "我的 AI 宠物 · 豆豆"
        bb = d.textbbox((0, 0), txt, font=f_title)
        x = (W - (bb[2] - bb[0])) / 2
        d.text((x + 3, y + 4), txt, font=f_title, fill=(0, 0, 0, int(120 * a1)))
        d.text((x, y), txt, font=f_title, fill=(255, 236, 214, int(255 * a1)))

    a2 = max(0.0, min(1.0, (t - 1.4) / 0.9))
    if a2 > 0:
        txt2 = "本地渲染 · 零 API 费用"
        bb = d.textbbox((0, 0), txt2, font=f_sub)
        d.text(((W - (bb[2] - bb[0])) / 2, 372), txt2, font=f_sub, fill=(208, 196, 255, int(230 * a2)))

    a3 = max(0.0, min(1.0, (t - 2.2) / 0.8))
    if a3 > 0:
        txt3 = "MADE WITH HERMES · LOCAL"
        bb = d.textbbox((0, 0), txt3, font=f_tag)
        d.text(((W - (bb[2] - bb[0])) / 2, H - 160), txt3, font=f_tag, fill=(255, 214, 170, int(150 * a3)))

    return Image.alpha_composite(frame, layer)


def render():
    if os.path.isdir(FRAME_DIR):
        shutil.rmtree(FRAME_DIR)
    os.makedirs(FRAME_DIR, exist_ok=True)

    bg = make_bg()
    total = int(DUR * FPS)
    for i in range(total):
        t = i / FPS
        frame = bg.convert("RGBA")
        # 爱心在猫身后，避免糊在脸上
        frame = draw_hearts(frame, t)
        cat = draw_cat(t)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([W * 0.5 - 300, H * 0.615, W * 0.5 + 300, H * 0.655], fill=(0, 0, 0, 90))
        sh = sh.filter(ImageFilter.GaussianBlur(28))
        frame = Image.alpha_composite(frame, sh)
        frame = Image.alpha_composite(frame, cat)
        frame = draw_text(frame, t)
        z = 1.0 + 0.035 * (t / DUR)
        nw, nh = int(W * z), int(H * z)
        frame = frame.resize((nw, nh), Image.BILINEAR).crop(
            ((nw - W) // 2, (nh - H) // 2, (nw - W) // 2 + W, (nh - H) // 2 + H)
        )
        frame.convert("RGB").save(os.path.join(FRAME_DIR, f"{i:05d}.png"), compress_level=1)
        if i % 30 == 0:
            print(f"  frame {i}/{total}", flush=True)

    audio = os.path.join(OUT_DIR, "bed.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         "aevalsrc='0.09*(sin(2*PI*261.63*t)+0.7*sin(2*PI*329.63*t)+0.55*sin(2*PI*392*t))"
         "*(1-exp(-2.5*t))*(0.6+0.4*sin(2*PI*0.11*t))*(0.5+0.5*sin(2*PI*0.07*t))':s=44100:d="
         + str(DUR),
         "-af", "afade=t=out:st=8.6:d=1.4", audio],
        check=True, capture_output=True,
    )

    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(FRAME_DIR, "%05d.png"),
         "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", VIDEO],
        check=True, capture_output=True,
    )
    print(f"OK -> {VIDEO}")


if __name__ == "__main__":
    render()
    sys.exit(0)
