import numpy as np
import soundfile as sf
import cv2
import json
import os
import random
import subprocess

# ======================
# 参数
# ======================
FPS = 25
FRAME_DURATION = 1.0 / FPS

AUDIO_PATH = "audio/audio.wav"
TIMELINE_PATH = "audio/timeline.json"

OUTPUT_DIR = "frames"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ======================
# 背景
# ======================
BG = cv2.imread("res/bg.png", cv2.IMREAD_UNCHANGED)
if BG is None:
    raise ValueError("❌ 找不到 res/bg.png")

if BG.shape[2] == 4:
    BG = BG[:, :, :3]

H, W = BG.shape[:2]

# ======================
# timeline
# ======================
with open(TIMELINE_PATH, "r") as f:
    timeline = json.load(f)

def get_role(t):
    for seg in timeline:
        if seg["start"] <= t < seg["end"]:
            return seg["role"]
    return None

# ======================
# 音频分析
# ======================
audio, sr = sf.read(AUDIO_PATH)
if len(audio.shape) > 1:
    audio = audio.mean(axis=1)

step = int(sr * FRAME_DURATION)

vols = []
for i in range(0, len(audio), step):
    chunk = audio[i:i+step]
    if len(chunk) == 0:
        continue
    vols.append(np.sqrt(np.mean(chunk**2)))

if len(vols) == 0:
    raise ValueError("❌ 音频为空")

mx = max(vols)
vols = [v / mx for v in vols]

states = ["open" if v > 0.28 else "close" for v in vols]  # ↓ 稍微降阈值
N = len(states)

# ======================
# load
# ======================
def load(p):
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"⚠️ 缺失资源: {p}")
    return img

# ======================
# A / B 资源
# ======================
A_BASE = load("res/A/base.png")
B_BASE = load("res/B/base.png")

A_MOUTH_OPEN = load("res/A/mouth/open.png")
A_MOUTH_CLOSE = load("res/A/mouth/close.png")
A_EYE_OPEN = load("res/A/eye/open.png")
A_EYE_CLOSE = load("res/A/eye/close.png")

B_MOUTH_OPEN = load("res/B/mouth/open.png")
B_MOUTH_CLOSE = load("res/B/mouth/close.png")
B_EYE_OPEN = load("res/B/eye/open.png")
B_EYE_CLOSE = load("res/B/eye/close.png")

# ======================
# overlay
# ======================
def overlay(bg, fg, x, y):
    if fg is None:
        return

    h, w = fg.shape[:2]

    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(bg.shape[1], x + w), min(bg.shape[0], y + h)

    if x1 >= x2 or y1 >= y2:
        return

    fg_x1 = x1 - x
    fg_y1 = y1 - y
    fg_x2 = fg_x1 + (x2 - x1)
    fg_y2 = fg_y1 + (y2 - y1)

    roi = bg[y1:y2, x1:x2]
    fg_crop = fg[fg_y1:fg_y2, fg_x1:fg_x2]

    if fg.shape[2] == 4:
        alpha = fg_crop[:, :, 3:4] / 255.0
        fg_rgb = fg_crop[:, :, :3]
        bg[y1:y2, x1:x2] = (fg_rgb * alpha + roi * (1 - alpha)).astype(np.uint8)
    else:
        bg[y1:y2, x1:x2] = fg_crop

# ======================
# blink
# ======================
def blink(n):
    arr = np.zeros(n, dtype=bool)
    i = 0
    while i < n:
        i += random.randint(40, 100)
        if i < n:
            arr[i:i+3] = True
    return arr

blink_A = blink(N)
blink_B = blink(N)

# ======================
# layout anchor
# ======================
A_X, A_Y = int(W * 0.25), int(H * 0.65)
B_X, B_Y = int(W * 0.75), int(H * 0.65)

# ======================
# base-relative layout (关键修复)
# ======================
def draw_character(frame, base, mouth_open, mouth_close, eye_open, eye_close,
                   x, y, is_talking, blink_arr, i):

    if base is None:
        return

    bh, bw = base.shape[:2]

    top_left_x = x - bw // 2
    top_left_y = y - bh // 2

    # base
    overlay(frame, base, top_left_x, top_left_y)

    # ======= 关键：用比例定位五官 =======
    eye_y = int(bh * 0.28)
    eye_dx = int(bw * 0.18)

    mouth_y = int(bh * 0.60)

    # eyes
    eye_img = eye_close if blink_arr[i] else eye_open

    overlay(frame, eye_img, top_left_x + bw//2 - eye_dx - 10,
                        top_left_y + eye_y)
    overlay(frame, eye_img, top_left_x + bw//2 + eye_dx - 10,
                        top_left_y + eye_y)

    # mouth
    if is_talking:
        overlay(frame, mouth_open, top_left_x + bw//2, top_left_y + mouth_y)
    else:
        overlay(frame, mouth_close, top_left_x + bw//2, top_left_y + mouth_y)

# ======================
# main loop
# ======================
for i in range(N):

    t = i / FPS
    role = get_role(t)

    frame = BG.copy()

    # fallback：音量太大也允许说话（解决 B 不动嘴问题）
    force_speak = states[i] == "open"

    # A
    draw_character(
        frame,
        A_BASE,
        A_MOUTH_OPEN, A_MOUTH_CLOSE,
        A_EYE_OPEN, A_EYE_CLOSE,
        A_X, A_Y,
        is_talking=(role == "A" and force_speak),
        blink_arr=blink_A,
        i=i
    )

    # B（修复关键点：允许 fallback）
    draw_character(
        frame,
        B_BASE,
        B_MOUTH_OPEN, B_MOUTH_CLOSE,
        B_EYE_OPEN, B_EYE_CLOSE,
        B_X, B_Y,
        is_talking=(role == "B" and force_speak),
        blink_arr=blink_B,
        i=i
    )

    cv2.imwrite(f"{OUTPUT_DIR}/frame_{i:04d}.png", frame)

print("🎬 帧生成完成")

# ======================
# ffmpeg
# ======================
cmd = [
    "ffmpeg",
    "-y",
    "-framerate", str(FPS),
    "-i", f"{OUTPUT_DIR}/frame_%04d.png",
    "-i", AUDIO_PATH,
    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-shortest",
    "output.mp4"
]

subprocess.run(cmd)

print("🎉 output.mp4 完成")
