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

AUDIO_PATH = "audio.wav"
TIMELINE_PATH = "timeline.json"

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
        if seg["start"] <= t <= seg["end"]:
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

states = ["open" if v > 0.35 else "close" for v in vols]
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
# overlay（稳定版）
# ======================
def overlay(bg, fg, x, y):
    if fg is None:
        return

    h, w = fg.shape[:2]

    if x >= bg.shape[1] or y >= bg.shape[0]:
        return

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
# center（防错位）
# ======================
def center(base_x, base_y, img):
    if img is None:
        return base_x, base_y
    h, w = img.shape[:2]
    return base_x - w//2, base_y - h//2

# ======================
# layout
# ======================
A_X, A_Y = int(W * 0.25), int(H * 0.65)
B_X, B_Y = int(W * 0.75), int(H * 0.65)

# ======================
# main loop
# ======================
for i in range(N):

    t = i / FPS
    role = get_role(t)

    frame = BG.copy()

    # ================= A =================
    ax, ay = center(A_X, A_Y, A_BASE)

    overlay(frame, A_BASE, ax, ay)

    overlay(frame, A_MOUTH_CLOSE, ax, ay)
    if role == "A" and states[i] == "open":
        overlay(frame, A_MOUTH_OPEN, ax, ay)

    eye = A_EYE_CLOSE if blink_A[i] else A_EYE_OPEN
    overlay(frame, eye, ax - 10, ay - 60)
    overlay(frame, eye, ax + 30, ay - 60)  # 右眼

    # ================= B =================
    bx, by = center(B_X, B_Y, B_BASE)

    overlay(frame, B_BASE, bx, by)

    overlay(frame, B_MOUTH_CLOSE, bx, by)
    if role == "B" and states[i] == "open":
        overlay(frame, B_MOUTH_OPEN, bx, by)

    eye = B_EYE_CLOSE if blink_B[i] else B_EYE_OPEN
    overlay(frame, eye, bx - 10, by - 60)
    overlay(frame, eye, bx + 30, by - 60)  # 右眼

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
