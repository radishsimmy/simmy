#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
import os
import soundfile as sf
import numpy as np
import cv2
import random
import subprocess
import requests

# ======================
# TTS Configuration
# ======================
API_URL = "http://127.0.0.1:9880/tts"

ROLE_CONFIG = {
    "A": {
        # 角色A的基础语速倍率（1.0为正常，>1.0更快，<1.0更慢）
        "base_speed_factor": 1.2,
        "正常": {
            "ref_audio": "res/ref/ref_a_normal.wav",
            "prompt_text": "盼望着，盼望着，东风来了。春天的脚步近了。"
        },
        "开心": {
            "ref_audio": "res/ref/ref_a_happy.wav",
            "prompt_text": "今天真开心啊！感觉一切都很美好！"
        },
        "生气": {
            "ref_audio": "res/ref/ref_a_angry.wav",
            "prompt_text": "你到底在干什么！我真的很生气！"
        }
    },
    "B": {
        # 角色B的基础语速倍率（可以设置为0.9让B说话稍慢）
        "base_speed_factor": 1.2,
        "正常": {
            "ref_audio": "res/ref/ref_b_normal.wav",
            "prompt_text": "生活或许是一地鸡毛，但浪漫让我们学会，用这些鸡毛，扎一个会飞的毽子。"
        }
    }
}

EMOTION_CONFIG = {
    "正常": {"temperature": 0.8, "emotion_intensity": 0.5, "speed_factor": 1.0},    # 正常语速
    "开心": {"temperature": 0.9, "emotion_intensity": 0.9, "speed_factor": 1.15},   # 开心时语速稍快（15%）
    "生气": {"temperature": 0.9, "emotion_intensity": 1.1, "speed_factor": 1.2},    # 生气时语速更快（20%）
    "悲伤": {"temperature": 0.7, "emotion_intensity": 0.7, "speed_factor": 0.85},   # 悲伤时语速更慢（慢15%）
}

COUNTER_FILE = "tts_counter.json"

# ======================
# Video Generation Parameters
# ======================
FPS = 25
FRAME_DURATION = 1.0 / FPS

AUDIO_PATH = "audio/audio.wav"
TIMELINE_PATH = "audio/timeline.json"

OUTPUT_DIR = "frames"


# ======================
# TTS Functions
# ======================
def get_next_seq(role):
    """获取角色的下一个序号"""
    counter = {}
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, 'r') as f:
            counter = json.load(f)
    seq = counter.get(role, 1)
    counter[role] = seq + 1
    with open(COUNTER_FILE, 'w') as f:
        json.dump(counter, f)
    return seq


def generate_tts(text, role, emotion):
    """生成语音，返回文件名"""
    if role not in ROLE_CONFIG:
        print(f"❌ 错误：角色 '{role}' 不存在")
        return None
    if emotion not in EMOTION_CONFIG:
        print(f"❌ 错误：语气 '{emotion}' 不存在")
        return None
    
    config = ROLE_CONFIG[role][emotion]
    
    # 计算最终语速：角色基础语速 × 情绪语速
    base_speed = ROLE_CONFIG[role].get("base_speed_factor", 1.0)
    emotion_speed = EMOTION_CONFIG[emotion]["speed_factor"]
    final_speed = base_speed * emotion_speed
    
    data = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": config["ref_audio"],
        "prompt_text": config["prompt_text"],
        "prompt_lang": "zh",
        "top_k": 5,
        "top_p": 1,
        "temperature": EMOTION_CONFIG[emotion]["temperature"],
        "speed_factor": final_speed  # 使用组合后的语速
    }
    
    try:
        response = requests.post(API_URL, json=data, timeout=60)
        if response.status_code == 200:
            seq = get_next_seq(role)
            filename = f"audio/{role}_{seq}.wav"
            with open(filename, "wb") as f:
                f.write(response.content)
            return filename
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
            return None
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接错误: 无法连接到TTS服务器 ({API_URL})")
        print(f"   请确保已启动TTS服务器: python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml")
        print(f"   或者检查服务器是否正在运行在端口 9880")
        return None
    except requests.exceptions.Timeout as e:
        print(f"❌ 请求超时: TTS服务器响应时间过长")
        return None
    except Exception as e:
        print(f"❌ 异常: {e}")
        return None


# ======================
# Audio Merge Function
# ======================
def merge_audio(audio_files, timeline=None, output="audio/audio.wav", gap=0.3):
    """
    合并音频文件
    
    Args:
        audio_files: 音频文件路径列表
        timeline: 时间线信息（包含角色信息），用于调整不同角色的音量
        output: 输出文件路径
        gap: 音频间隔（秒）
    """
    if len(audio_files) == 0:
        print("❌ 没有音频可合成")
        return False

    print("\n🎧 开始合成 audio.wav ...")
    
    # 角色音量增益配置（1.0为原始音量，>1.0增大音量，<1.0降低音量）
    ROLE_VOLUME_GAIN = {
        "A": 1.0,   # 角色A保持原音量
        "B": 1.5,   # 角色B音量提升50%（可根据需要调整）
    }

    merged_audio = []
    sample_rate = None

    for i, file in enumerate(audio_files):
        audio, sr = sf.read(file)

        # 转单声道
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        if sample_rate is None:
            sample_rate = sr
        
        # 根据角色调整音量
        if timeline and i < len(timeline):
            role = timeline[i].get("role", "")
            gain = ROLE_VOLUME_GAIN.get(role, 1.0)
            
            if gain != 1.0:
                audio = audio * gain
                # 防止爆音：限制振幅在 -1.0 到 1.0 之间
                audio = np.clip(audio, -1.0, 1.0)
                print(f"   📢 角色 {role} 音量增益: {gain}x")

        # 插入静音
        if i > 0:
            silence = [0.0] * int(sr * gap)
            merged_audio.extend(silence)

        merged_audio.extend(audio)

    # 保存
    sf.write(output, merged_audio, sample_rate)

    print(f"🎉 audio.wav 合成完成，总时长: {len(merged_audio)/sample_rate:.2f}s")
    return True


# ======================
# Video Generation Functions
# ======================
def load_image(p):
    img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"⚠️ 缺失资源: {p}")
    return img


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


def blink(n):
    arr = np.zeros(n, dtype=bool)
    i = 0
    while i < n:
        i += random.randint(40, 100)
        if i < n:
            arr[i:i+3] = True
    return arr


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
    # 可根据实际角色图片调整这些比例值
    
    # Y坐标（垂直位置）
    eye_y = int(bh * 0.58)   # 眼睛Y坐标
    mouth_y = int(bh * 0.75) # 嘴巴Y坐标
    
    # X坐标（水平位置）- 相对于头部中心的偏移
    eye_offset_x = -12       # 眼睛X偏移（负数向左，正数向右）
    mouth_offset_x = -20       # 嘴巴X偏移（负数向左，正数向右）
    
    # 眼睛水平间距
    eye_dx = int(bw * 0.15)  # 眼睛距离中心的水平距离

    # eyes
    eye_img = eye_close if blink_arr[i] else eye_open

    overlay(frame, eye_img, top_left_x + bw//2 - eye_dx + eye_offset_x,
                        top_left_y + eye_y)
    overlay(frame, eye_img, top_left_x + bw//2 + eye_dx + eye_offset_x,
                        top_left_y + eye_y)

    # mouth
    if is_talking:
        overlay(frame, mouth_open, top_left_x + bw//2 + mouth_offset_x, top_left_y + mouth_y)
    else:
        overlay(frame, mouth_close, top_left_x + bw//2 + mouth_offset_x, top_left_y + mouth_y)


def generate_video():
    """生成视频"""
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

    # 嘴巴开合阈值（可根据需要调整）
    # 如果角色B音量偏低导致嘴巴不动，可以降低这个值
    MOUTH_THRESHOLD = 0.15  # 从0.28降低到0.15，让小声也能触发动画
    
    states = ["open" if v > MOUTH_THRESHOLD else "close" for v in vols]
    N = len(states)

    # ======================
    # load resources
    # ======================
    A_BASE = load_image("res/A/base.png")
    B_BASE = load_image("res/B/base.png")

    A_MOUTH_OPEN = load_image("res/A/mouth/open.png")
    A_MOUTH_CLOSE = load_image("res/A/mouth/close.png")
    A_EYE_OPEN = load_image("res/A/eye/open.png")
    A_EYE_CLOSE = load_image("res/A/eye/close.png")

    B_MOUTH_OPEN = load_image("res/B/mouth/open.png")
    B_MOUTH_CLOSE = load_image("res/B/mouth/close.png")
    B_EYE_OPEN = load_image("res/B/eye/open.png")
    B_EYE_CLOSE = load_image("res/B/eye/close.png")

    # ======================
    # layout anchor
    # ======================
    A_X, A_Y = int(W * 0.25), int(H * 0.65)
    B_X, B_Y = int(W * 0.75), int(H * 0.65)

    # ======================
    # blink
    # ======================
    blink_A = blink(N)
    blink_B = blink(N)

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

        # B
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


# ======================
# Main Workflow
# ======================
def check_tts_server():
    """检查TTS服务器是否运行"""
    try:
        response = requests.get(API_URL.replace("/tts", ""), timeout=5)
        # 如果服务器运行，应该返回404或其他状态码（不是连接错误）
        return True
    except requests.exceptions.ConnectionError:
        return False
    except Exception:
        # 其他异常可能意味着服务器在运行但返回了错误
        return True


def run_script_to_audio():
    """从剧本生成音频"""
    # 检查TTS服务器
    print("🔍 检查TTS服务器状态...")
    if not check_tts_server():
        print(f"❌ 错误：无法连接到TTS服务器 ({API_URL})")
        print("\n请先启动TTS服务器:")
        print("   python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml")
        print("\n或者使用以下命令在后台运行:")
        print("   nohup python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml > tts_server.log 2>&1 &")
        print("\n等待服务器启动后，再运行此脚本。")
        sys.exit(1)
    
    print("✅ TTS服务器已连接\n")
    
    # 创建 audio 目录
    os.makedirs("audio", exist_ok=True)
    
    # 检查 script.json
    if not os.path.exists("script.json"):
        print("❌ 错误：找不到 script.json 文件")
        sys.exit(1)

    with open("script.json", "r", encoding="utf-8") as f:
        script = json.load(f)

    print(f"📖 读取到 {len(script)} 条台词\n")

    audio_files = []
    timeline = []

    current_time = 0.0
    silence_gap = 0.3  # 每句间隔

    for i, item in enumerate(script, 1):
        role = item.get("role", "未知")
        text = item.get("text", "")
        emotion = item.get("emotion", "正常")

        print(f"[{i}/{len(script)}] {role} {emotion}")

        filename = generate_tts(text, role, emotion)

        if filename:
            audio_files.append(filename)

            # ===== 获取音频时长 =====
            audio_data, sr = sf.read(filename)

            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)

            duration = len(audio_data) / sr

            # ===== 写入 timeline =====
            timeline.append({
                "role": role,
                "file": filename,
                "start": current_time,
                "end": current_time + duration
            })

            current_time += duration + silence_gap

    # ===== 输出 =====
    print("\n音频顺序：", audio_files)

    # ===== 保存 timeline =====
    with open("audio/timeline.json", "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)

    print("\n📌 timeline 已生成：audio/timeline.json")

    # ⭐⭐ 核心新增：合成 audio.wav
    if not merge_audio(audio_files, timeline=timeline):
        print("\n❌ 错误：没有成功生成任何音频文件")
        print("   请检查:")
        print("   1. TTS服务器是否正常运行")
        print("   2. 参考音频文件是否存在")
        print("   3. 查看上面的错误信息")
        sys.exit(1)

    print(f"\n✅ 完成！生成音频: {len(audio_files)} 条")


def main():
    """主流程：剧本 -> 音频 -> 视频"""
    print("=" * 50)
    print("🎬 开始剧本到视频生成流程")
    print("=" * 50)

    # Step 1: 生成音频
    print("\n【步骤 1】从剧本生成TTS音频...")
    run_script_to_audio()

    # Step 2: 生成视频
    print("\n【步骤 2】从音频生成视频...")
    generate_video()

    print("\n" + "=" * 50)
    print("🎉 全部完成！视频已生成: output.mp4")
    print("=" * 50)


if __name__ == "__main__":
    main()
