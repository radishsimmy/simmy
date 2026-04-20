#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import subprocess
import sys
import os
import soundfile as sf


def run_tts(text, role, emotion):
    cmd = [sys.executable, "tts.py", text, role, emotion]
    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    # 解析 __FILE__
    for line in result.stdout.splitlines():
        if line.startswith("__FILE__:"):
            return line.replace("__FILE__:", "").strip()

    return None


# ======================
# ⭐ 新增：合成音频
# ======================
def merge_audio(audio_files, output="audio.wav", gap=0.3):

    if len(audio_files) == 0:
        print("❌ 没有音频可合成")
        return

    print("\n🎧 开始合成 audio.wav ...")

    merged_audio = []
    sample_rate = None

    for i, file in enumerate(audio_files):
        audio, sr = sf.read(file)

        # 转单声道
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        if sample_rate is None:
            sample_rate = sr

        # 插入静音
        if i > 0:
            silence = [0.0] * int(sr * gap)
            merged_audio.extend(silence)

        merged_audio.extend(audio)

    # 保存
    sf.write(output, merged_audio, sample_rate)

    print(f"🎉 audio.wav 合成完成，总时长: {len(merged_audio)/sample_rate:.2f}s")


def main():

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

        filename = run_tts(text, role, emotion)

        if filename:

            audio_files.append(filename)

            # ===== 获取音频时长 =====
            audio, sr = sf.read(filename)

            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)

            duration = len(audio) / sr

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
    with open("timeline.json", "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)

    print("\n📌 timeline 已生成：timeline.json")

    # ⭐⭐ 核心新增：合成 audio.wav
    merge_audio(audio_files)

    print(f"\n✅ 完成！生成音频: {len(audio_files)} 条")


if __name__ == "__main__":
    main()
