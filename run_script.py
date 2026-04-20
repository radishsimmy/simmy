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
    silence_gap = 0.3  # 每句间隔（你可以调）

    for i, item in enumerate(script, 1):
        role = item.get("role", "未知")
        text = item.get("text", "")
        emotion = item.get("emotion", "正常")

        print(f"[{i}/{len(script)}] {role} {emotion}")

        filename = run_tts(text, role, emotion)

        if filename:

            audio_files.append(filename)

            # ===== 关键：获取音频时长 =====
            audio, sr = sf.read(filename)
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

    print(f"\n✅ 完成！生成音频: {len(audio_files)} 条")


if __name__ == "__main__":
    main()
