#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
沙雕动画工业化流程 - 主控制脚本
支持增量更新和最小人工干预
"""

import json
import sys
import os
import argparse
import soundfile as sf
import numpy as np
import cv2
import random
import subprocess
import requests
from pathlib import Path
from datetime import datetime


# ======================
# 全局配置
# ======================
API_URL = "http://127.0.0.1:9880/tts"
FPS = 25
FRAME_DURATION = 1.0 / FPS
SILENCE_GAP = 0.3  # 台词间隔（秒）

# 音频归一化配置
TARGET_RMS = 0.03  # 目标RMS音量值（0.01-0.05之间，越大声音越响）
MAX_NORMALIZATION_GAIN = 15.0  # 最大归一化增益倍数（防止爆音）

# 项目目录结构
PROJECT_ROOT = Path(__file__).parent
STAGES_DIR = PROJECT_ROOT / "stages"
SCRIPT_DIR = STAGES_DIR / "01_script"
AUDIO_DIR = STAGES_DIR / "02_audio"
FRAMES_DIR = STAGES_DIR / "03_frames"
RES_DIR = PROJECT_ROOT / "res"

# 角色配置
ROLE_CONFIG = {
    "A": {
        "base_speed_factor": 1.0,  # 从1.2降低到1.0，让语速更自然
        "正常": {
            "ref_audio": str(RES_DIR / "ref" / "ref_a_normal.wav"),
            "prompt_text": "盼望着，盼望着，东风来了。春天的脚步近了。"
        },
        "开心": {
            "ref_audio": str(RES_DIR / "ref" / "ref_a_happy.wav"),
            "prompt_text": "今天真开心啊！感觉一切都很美好！"
        },
        "生气": {
            "ref_audio": str(RES_DIR / "ref" / "ref_a_angry.wav"),
            "prompt_text": "你到底在干什么！我真的很生气！"
        }
    },
    "B": {
        "base_speed_factor": 1.0,  # 从1.2降低到1.0，保持与A一致
        "正常": {
            "ref_audio": str(RES_DIR / "ref" / "ref_b_normal.wav"),
            "prompt_text": "生活或许是一地鸡毛，但浪漫让我们学会，用这些鸡毛，扎一个会飞的毽子。"
        },
        "开心": {
            "ref_audio": str(RES_DIR / "ref" / "ref_b_normal.wav"),
            "prompt_text": "生活或许是一地鸡毛，但浪漫让我们学会，用这些鸡毛，扎一个会飞的毽子。"  # 使用与normal相同的prompt_text
        },
        "生气": {
            "ref_audio": str(RES_DIR / "ref" / "ref_b_normal.wav"),
            "prompt_text": "生活或许是一地鸡毛，但浪漫让我们学会，用这些鸡毛，扎一个会飞的毽子。"  # 使用与normal相同的prompt_text
        }
    }

}

EMOTION_CONFIG = {
    "正常": {"temperature": 0.8, "speed_factor": 1.0},
    "开心": {"temperature": 0.9, "speed_factor": 1.15},
    "生气": {"temperature": 0.9, "speed_factor": 1.2},
    "悲伤": {"temperature": 0.7, "speed_factor": 0.85},
}

# 角色音量增益
ROLE_VOLUME_GAIN = {
    "A": 1.0,
    "B": 2.5,  # 提高角色B的增益，补偿参考音频音量偏低的问题
}


# ======================
# 工具函数
# ======================
def check_reference_audio_files():
    """检查所有角色配置中引用的参考音频文件是否存在"""
    print("\n🔍 检查参考音频文件...")
    
    missing_files = set()
    existing_files = set()
    
    for role, emotions in ROLE_CONFIG.items():
        for emotion_name, config in emotions.items():
            if isinstance(config, dict) and "ref_audio" in config:
                ref_path = Path(config["ref_audio"])
                if ref_path.exists():
                    existing_files.add(str(ref_path))
                else:
                    missing_files.add(str(ref_path))
    
    if missing_files:
        print(f"⚠️  发现 {len(missing_files)} 个缺失的参考音频文件:")
        for file in sorted(missing_files):
            print(f"   ❌ {file}")
        
        print(f"\n✅ 已找到 {len(existing_files)} 个存在的文件")
        
        # 提供修复建议
        print("\n💡 修复建议:")
        print("   1. 录制或准备缺失的参考音频文件")
        print("   2. 或者修改 pipeline.py 中的 ROLE_CONFIG，让缺失的情绪指向已存在的文件")
        print("   3. 系统会在运行时自动降级到'正常'情绪（如果可用）")
        
        return False
    else:
        print(f"✅ 所有参考音频文件都存在 (共 {len(existing_files)} 个)")
        return True


def ensure_dirs():
    """自动创建所有必需的目录"""
    dirs = [
        SCRIPT_DIR,
        AUDIO_DIR / "audio_files",
        FRAMES_DIR / "frames",
        RES_DIR / "bg",
        RES_DIR / "characters" / "A" / "mouth",
        RES_DIR / "characters" / "A" / "eye",
        RES_DIR / "characters" / "B" / "mouth",
        RES_DIR / "characters" / "B" / "eye",
        RES_DIR / "effects",
        RES_DIR / "sfx",
        RES_DIR / "ref",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("✅ 目录结构已就绪")


def load_json(filepath):
    """加载JSON文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath, data):
    """保存JSON文件"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def check_tts_server():
    """检查TTS服务器是否运行"""
    try:
        response = requests.get(API_URL.replace("/tts", ""), timeout=5)
        return True
    except requests.exceptions.ConnectionError:
        return False
    except Exception:
        return True


# ======================
# Stage 1: 剧本加载（已废弃，请使用 gen_script.py）
# ======================

def load_script():
    """
    加载剧本文件
    
    逻辑：
    - 固定读取 stages/01_script/script.json
    - 如果文件不存在，直接报错退出
    - 不进行任何模板匹配或自动生成
    """
    script_file = SCRIPT_DIR / "script.json"
    
    if not script_file.exists():
        print(f"❌ 错误：剧本文件不存在: {script_file}")
        print(f"\n💡 请先使用 gen_script.py 生成剧本:")
        print(f"   python gen_script.py --prompt \"你的剧本主题\"")
        print(f"\n或者手动创建剧本文件，格式参考:")
        print(f"""{{
  "title": "剧本标题",
  "dialogs": [
    {{"id": "D001", "role": "A", "text": "第一句台词", "emotion": "正常"}},
    {{"id": "D002", "role": "B", "text": "第二句台词", "emotion": "开心"}}
  ]
}}""")
        sys.exit(1)
    
    print(f"✅ 加载剧本: {script_file}")
    script_data = load_json(script_file)
    print(f"   标题: {script_data.get('title', '未命名')}")
    print(f"   共 {len(script_data.get('dialogs', []))} 句台词")
    
    return script_data


# ======================
# Stage 2: 音频 + 动作生成
# ======================

def generate_tts(text, role, emotion, output_file, max_retries=3):
    """
    生成单句TTS音频（带自动重试机制）
    
    降级策略：
    1. 优先使用指定情绪的参考音频
    2. 如果文件不存在，降级到"正常"情绪
    3. 如果生成的音频质量差（文件过小），自动更换种子重试（最多3次）
    
    参数:
        text: 要合成的文本
        role: 角色标识 (A/B)
        emotion: 情绪类型
        output_file: 输出文件路径
        max_retries: 最大重试次数（默认3次）
    """
    if role not in ROLE_CONFIG:
        print(f"❌ 错误：角色 '{role}' 不存在")
        return None
    
    # 如果该角色没有指定情绪，使用"正常"作为默认值
    original_emotion = emotion
    if emotion not in ROLE_CONFIG[role]:
        print(f"⚠️  警告：角色 '{role}' 没有 '{emotion}' 情绪配置，使用'正常'代替")
        emotion = "正常"
    
    if emotion not in EMOTION_CONFIG:
        print(f"⚠️  警告：'{original_emotion}' 不是有效情绪，使用'正常'代替")
        emotion = "正常"
    
    # 获取当前情绪的配置
    config = ROLE_CONFIG[role][emotion]
    ref_audio_path = config["ref_audio"]
    prompt_text = config["prompt_text"]
    
    # 检查参考音频文件是否存在
    if not Path(ref_audio_path).exists():
        print(f"⚠️  警告：参考音频文件不存在: {ref_audio_path}")
        
        # 尝试降级到"正常"情绪
        if emotion != "正常":
            print(f"   🔄 尝试降级到'正常'情绪...")
            if "正常" in ROLE_CONFIG[role]:
                config = ROLE_CONFIG[role]["正常"]
                ref_audio_path = config["ref_audio"]
                prompt_text = config["prompt_text"]
                emotion = "正常"
                
                if not Path(ref_audio_path).exists():
                    print(f"   ❌ 错误：'正常'情绪的参考音频也不存在: {ref_audio_path}")
                    print(f"   💡 请确保以下文件存在:")
                    print(f"      - {RES_DIR / 'ref' / f'ref_{role.lower()}_normal.wav'}")
                    return None
                else:
                    print(f"   ✅ 成功降级到'正常'情绪")
                    print(f"      使用参考音频: {ref_audio_path}")
                    print(f"      使用提示文本: {prompt_text[:30]}...")
            else:
                print(f"   ❌ 错误：角色 '{role}' 没有'正常'情绪配置")
                return None
        else:
            print(f"   ❌ 错误：无法找到可用的参考音频")
            print(f"   💡 请确保以下文件存在:")
            print(f"      - {ref_audio_path}")
            return None
    
    # 计算最终语速
    base_speed = ROLE_CONFIG[role].get("base_speed_factor", 1.0)
    emotion_speed = EMOTION_CONFIG[emotion]["speed_factor"]
    final_speed = base_speed * emotion_speed
    
    # 根据文本长度估算最小文件大小（经验公式）
    # 每个中文字符约需要 8000-12000 bytes
    estimated_min_size = len(text) * 7000  # 保守估计
    
    # 自动重试逻辑
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            print(f"\n   🔄 第 {attempt}/{max_retries} 次重试（更换随机种子）...")
        
        # 为每次重试生成不同的种子
        import hashlib
        seed_text = f"{role}_{text}_{emotion}_attempt{attempt}"
        fixed_seed = int(hashlib.md5(seed_text.encode()).hexdigest(), 16) % (2**31)
        
        data = {
            "text": text,
            "text_lang": "zh",
            "ref_audio_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_lang": "zh",
            "top_k": 5,
            "top_p": 1,
            "temperature": EMOTION_CONFIG[emotion]["temperature"],
            "speed_factor": final_speed,
            "seed": fixed_seed  # 使用固定但可变的种子
        }
        
        print(f"   📤 调用TTS API...")
        print(f"      文本长度: {len(text)} 字符")
        print(f"      参考音频: {Path(ref_audio_path).name}")
        print(f"      语速系数: {final_speed:.2f}")
        print(f"      随机种子: {fixed_seed}")
        print(f"      预估最小大小: {estimated_min_size} bytes")
        
        try:
            response = requests.post(API_URL, json=data, timeout=60)
            if response.status_code == 200:
                # 检查响应内容是否为空
                if len(response.content) == 0:
                    print(f"   ⚠️  TTS API返回空内容")
                    if attempt < max_retries:
                        continue
                    else:
                        print(f"   ❌ 错误：重试{max_retries}次后仍失败")
                        return None
                
                # 写入文件
                with open(output_file, "wb") as f:
                    f.write(response.content)
                
                file_size = Path(output_file).stat().st_size
                print(f"   📥 收到响应，文件大小: {file_size} bytes")
                
                # 如果文件过小，重试
                if file_size < estimated_min_size:
                    print(f"   ⚠️  警告：文件过小 ({file_size} bytes < {estimated_min_size} bytes)")
                    if attempt < max_retries:
                        print(f"      将更换种子重试...")
                        # 删除低质量文件
                        try:
                            Path(output_file).unlink()
                        except:
                            pass
                        continue
                    else:
                        print(f"   ⚠️  警告：重试{max_retries}次后文件仍然偏小，但将继续使用")
                
                # 验证生成的音频是否有效
                try:
                    audio_data, sr = sf.read(str(output_file))
                    if len(audio_data.shape) > 1:
                        audio_data = audio_data.mean(axis=1)
                        
                    duration = len(audio_data) / sr
                    rms = float(np.sqrt(np.mean(audio_data**2))) if len(audio_data) > 0 else 0
                    
                    if len(audio_data) == 0 or duration <= 0:
                        print(f"   ⚠️  错误：生成的音频为空或时长为0")
                        if attempt < max_retries:
                            try:
                                Path(output_file).unlink()
                            except:
                                pass
                            continue
                        else:
                            print(f"   ❌ 错误：重试{max_retries}次后仍失败")
                            return None
                    
                    # 检查音量是否过低（正常音频RMS应在0.01-0.05之间）
                    # RMS < 0.005 通常是生成质量问题，需要重试
                    MIN_ACCEPTABLE_RMS = 0.005
                    
                    if rms < MIN_ACCEPTABLE_RMS:
                        print(f"   ⚠️  警告：音量过低 (RMS={rms:.6f} < {MIN_ACCEPTABLE_RMS})，可能是低质量生成")
                        if attempt < max_retries:
                            print(f"      将更换种子重试...")
                            # 删除低质量文件
                            try:
                                Path(output_file).unlink()
                            except:
                                pass
                            continue
                        else:
                            print(f"   ⚠️  警告：重试{max_retries}次后音量仍然过低，但将继续使用")
                    
                    print(f"   ✅ 音频验证通过 | 时长: {duration:.2f}s | RMS: {rms:.4f} | 尝试次数: {attempt}")
                    return output_file
                    
                except Exception as e:
                    print(f"   ⚠️  错误：读取生成的音频失败: {e}")
                    if attempt < max_retries:
                        try:
                            Path(output_file).unlink()
                        except:
                            pass
                        continue
                    else:
                        print(f"   ❌ 错误：重试{max_retries}次后仍失败")
                        return None
            else:
                print(f"   ⚠️  HTTP {response.status_code}: {response.text[:200]}")
                if attempt < max_retries:
                    continue
                else:
                    return None
        except requests.exceptions.ConnectionError:
            print(f"   ⚠️  错误：无法连接到TTS服务器")
            if attempt < max_retries:
                import time
                time.sleep(2)  # 等待2秒后重试
                continue
            else:
                print(f"      请确保TTS服务器正在运行: python api_v2.py -a 127.0.0.1 -p 9880")
                return None
        except requests.exceptions.Timeout:
            print(f"   ⚠️  错误：TTS请求超时（60秒）")
            if attempt < max_retries:
                continue
            else:
                return None
        except Exception as e:
            print(f"   ⚠️  错误：TTS生成失败: {e}")
            if attempt < max_retries:
                continue
            else:
                import traceback
                traceback.print_exc()
                return None
    
    print(f"   ❌ 错误：达到最大重试次数 ({max_retries})")
    return None


def generate_actions_for_line(text, emotion):
    """根据台词内容和情绪自动生成动作配置（简化版）"""
    actions = []
    
    # 基础面部表情
    face_map = {
        "开心": "smile",
        "生气": "shocked_mouth",
        "悲伤": "sad_mouth",
        "正常": "normal"
    }
    face_name = face_map.get(emotion, "normal")
    actions.append({
        "type": "face",
        "name": face_name,
        "start_offset": 0.0,
        "duration": -1  # -1表示持续到该行结束
    })
    
    # 根据关键词添加特效
    if "？" in text or "???" in text:
        actions.append({
            "type": "effect",
            "name": "question_marks",
            "start_offset": 0.1,
            "duration": 0.5
        })
    
    if "！" in text or "!" in text:
        actions.append({
            "type": "effect",
            "name": "shock_lines",
            "start_offset": 0.0,
            "duration": 0.3
        })
    
    # 简单运镜
    if emotion in ["生气", "开心"]:
        actions.append({
            "type": "camera",
            "name": "zoom",
            "value": 1.1,
            "start_offset": 0.0,
            "duration": 0.5,
            "easing": "ease-out"
        })
    
    return actions


def stage2_generate_all(script_data):
    """Stage 2: 生成所有音频、时间轴和动作配置"""
    print("\n【Stage 2】生成音频和动作配置...")
    
    # 检查参考音频文件
    check_reference_audio_files()
    
    if not check_tts_server():
        print("❌ TTS服务器未运行，请先启动:")
        print("   python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml")
        sys.exit(1)
    
    timeline_data = {
        "metadata": {
            "title": script_data.get("title", "未命名"),
            "created_at": datetime.now().isoformat(),
            "fps": FPS
        },
        "lines": []
    }
    
    current_time = 0.0
    audio_files = []
    lines_for_merge = []  # 用于音频合并的行数据
    
    for dialog in script_data["dialogs"]:
        dialog_id = dialog["id"]
        role = dialog["role"]
        text = dialog["text"]
        emotion = dialog.get("emotion", "正常")
        
        print(f"\n  处理 {dialog_id}: [{role}] {text} (情绪: {emotion})")
        
        # 生成音频文件
        audio_file = AUDIO_DIR / "audio_files" / f"{role}_{dialog_id}.wav"
        result = generate_tts(text, role, emotion, str(audio_file))
        
        if not result:
            print(f"  ⚠️ 跳过 {dialog_id} (音频生成失败)")
            continue
        
        # 验证生成的音频文件
        try:
            audio_data, sr = sf.read(str(audio_file))
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            duration = len(audio_data) / sr
            
            # 验证音频是否有效
            if duration <= 0 or len(audio_data) == 0:
                print(f"  ❌ 错误：{dialog_id} 生成的音频为空")
                continue
            
            # 计算音量（RMS）
            rms = np.sqrt(np.mean(audio_data**2))
            print(f"  ✅ 音频生成成功 | 时长: {duration:.2f}s | 音量(RMS): {rms:.4f}")
            
        except Exception as e:
            print(f"  ❌ 错误：读取 {dialog_id} 音频失败: {e}")
            continue
        
        # 生成动作配置
        actions = generate_actions_for_line(text, emotion)
        
        # 构建时间轴条目
        line_data = {
            "dialog_id": dialog_id,
            "role": role,
            "text": text,
            "emotion": emotion,
            "audio_file": str(audio_file.relative_to(AUDIO_DIR)),
            "start": round(current_time, 2),
            "end": round(current_time + duration, 2),
            "duration": round(duration, 2),
            "actions": actions
        }
        
        timeline_data["lines"].append(line_data)
        audio_files.append(str(audio_file))
        lines_for_merge.append({"role": role})  # 保存对应的角色信息
        
        current_time += duration + SILENCE_GAP
    
    # 保存 timeline.json
    timeline_file = AUDIO_DIR / "timeline.json"
    save_json(timeline_file, timeline_data)
    print(f"\n✅ 时间轴已保存: {timeline_file}")
    print(f"   成功生成 {len(timeline_data['lines'])} 句台词")
    
    # 统计各角色的音频数量
    role_count = {}
    for line in timeline_data['lines']:
        role = line['role']
        role_count[role] = role_count.get(role, 0) + 1
    print(f"   角色统计: {role_count}")
    
    # 合并音频
    merge_audio_files(audio_files, lines_for_merge)
    
    return timeline_data


def merge_audio_files(audio_files, lines_data):
    """合并所有音频文件，并应用音量归一化"""
    print("\n🎧 合并音频...")
    
    if not audio_files:
        print("❌ 没有音频可合并")
        return
    
    merged_audio = []
    sample_rate = None
    all_segments = []  # 存储所有音频片段及其角色信息
    
    # 第一遍：读取所有音频并应用角色增益
    print("   📊 处理音频片段...")
    for i, file in enumerate(audio_files):
        audio, sr = sf.read(file)
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        if sample_rate is None:
            sample_rate = sr
        
        # 应用角色音量增益
        role = lines_data[i]["role"]
        gain = ROLE_VOLUME_GAIN.get(role, 1.0)
        if gain != 1.0:
            audio = audio * gain
            audio = np.clip(audio, -1.0, 1.0)
        
        # 计算该片段的RMS
        rms = float(np.sqrt(np.mean(audio**2))) if len(audio) > 0 else 0
        
        all_segments.append({
            "audio": audio,
            "role": role,
            "rms": rms,
            "index": i
        })
        
        print(f"      [{i+1}/{len(audio_files)}] {Path(file).name} | 角色: {role} | RMS: {rms:.6f}")
    
    # 第二遍：计算整体目标音量
    # 策略：使用配置的目标RMS，但如果所有片段都很响，则使用中位数避免过度压缩
    all_rms_values = [seg["rms"] for seg in all_segments if seg["rms"] > 0.0001]
    
    if all_rms_values:
        median_rms = float(np.median(all_rms_values))
        # 如果中位数已经高于目标值，说明整体音量不错，使用中位数
        # 否则使用配置的目标值，确保低音量片段被提升
        target_rms = max(TARGET_RMS, median_rms)
        print(f"\n   📈 音量归一化:")
        print(f"      配置目标RMS: {TARGET_RMS:.6f}")
        print(f"      实际使用中位数: {median_rms:.6f}")
        print(f"      最终目标RMS: {target_rms:.6f}")
    else:
        target_rms = TARGET_RMS
        print(f"\n   ⚠️  无法计算目标音量，使用配置值: {target_rms}")
    
    # 第三遍：应用归一化并合并
    print("   🔧 应用归一化并合并...")
    for i, seg in enumerate(all_segments):
        audio = seg["audio"]
        current_rms = seg["rms"]
        
        # 如果音量低于目标值的50%，进行归一化提升
        if current_rms > 0.0001 and current_rms < target_rms * 0.5:
            # 计算需要的增益
            normalization_gain = target_rms / current_rms
            # 限制最大增益，避免爆音
            normalization_gain = min(normalization_gain, MAX_NORMALIZATION_GAIN)
            
            audio = audio * normalization_gain
            audio = np.clip(audio, -1.0, 1.0)
            
            new_rms = float(np.sqrt(np.mean(audio**2)))
            print(f"      [{i+1}] {seg['role']} | 归一化: {current_rms:.6f} → {new_rms:.6f} (增益: {normalization_gain:.2f}x)")
        elif current_rms >= target_rms * 0.5:
            print(f"      [{i+1}] {seg['role']} | 音量正常: {current_rms:.6f}")
        else:
            print(f"      [{i+1}] {seg['role']} | 音量极低: {current_rms:.6f} (跳过)")

        # 插入静音间隔
        if i > 0:
            silence = [0.0] * int(sample_rate * SILENCE_GAP)
            merged_audio.extend(silence)
        
        merged_audio.extend(audio)
    
    # 保存合并后的音频
    output_file = AUDIO_DIR / "merged_audio.wav"
    sf.write(str(output_file), merged_audio, sample_rate)
    
    # 验证最终输出
    final_audio, _ = sf.read(str(output_file))
    final_rms = float(np.sqrt(np.mean(final_audio**2)))
    final_duration = len(final_audio) / sample_rate
    
    print(f"\n✅ 音频合并完成: {output_file}")
    print(f"   总时长: {final_duration:.2f}s")
    print(f"   整体RMS: {final_rms:.6f}")
    
    if final_rms < 0.01:
        print(f"   ⚠️  警告：整体音量偏低，建议在视频编辑软件中后期增强")


def regenerate_single_line(dialog_id):
    """重新生成单句台词的音频和动作"""
    print(f"\n🔄 重新生成 {dialog_id}...")
    
    # 加载剧本和时间轴
    script_data = load_json(SCRIPT_DIR / "script.json")
    timeline_data = load_json(AUDIO_DIR / "timeline.json")
    
    # 找到对应的对话
    dialog = None
    for d in script_data["dialogs"]:
        if d["id"] == dialog_id:
            dialog = d
            break
    
    if not dialog:
        print(f"❌ 找不到 {dialog_id}")
        return
    
    # 重新生成音频
    role = dialog["role"]
    text = dialog["text"]
    emotion = dialog.get("emotion", "正常")
    audio_file = AUDIO_DIR / "audio_files" / f"{role}_{dialog_id}.wav"
    
    result = generate_tts(text, role, emotion, str(audio_file))
    if not result:
        print("❌ 音频生成失败")
        return
    
    # 获取新时长
    audio_data, sr = sf.read(str(audio_file))
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)
    new_duration = len(audio_data) / sr
    
    # 更新时间轴中的该条目
    time_shift = 0
    for line in timeline_data["lines"]:
        if line["dialog_id"] == dialog_id:
            old_duration = line["duration"]
            line["duration"] = round(new_duration, 2)
            line["end"] = round(line["start"] + new_duration, 2)
            time_shift = new_duration - old_duration
            
            # 重新生成动作
            line["actions"] = generate_actions_for_line(text, emotion)
            print(f"  ✅ 已更新音频和动作")
        elif line["start"] > line.get("start", 0):  # 后续所有行
            line["start"] = round(line["start"] + time_shift, 2)
            line["end"] = round(line["end"] + time_shift, 2)
    
    # 保存更新后的时间轴
    save_json(AUDIO_DIR / "timeline.json", timeline_data)
    
    # 重新合并音频
    audio_files = [str(AUDIO_DIR / line["audio_file"]) for line in timeline_data["lines"]]
    merge_audio_files(audio_files, timeline_data["lines"])
    
    print(f"✅ {dialog_id} 重新生成完成")


# ======================
# Stage 3: 帧渲染
# ======================
def load_image(p):
    """加载图片，如果不存在返回None"""
    img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    return img


def overlay(bg, fg, x, y):
    """将前景图叠加到背景图上"""
    if fg is None or bg is None:
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
    """生成眨眼序列"""
    arr = np.zeros(n, dtype=bool)
    i = 0
    while i < n:
        i += random.randint(40, 100)
        if i < n:
            arr[i:i+3] = True
    return arr


def draw_character(frame, base, mouth_open, mouth_close, eye_open, eye_close,
                   x, y, is_talking, blink_arr, i, mouth_threshold=0.15):
    """绘制角色（支持口型同步）"""
    if base is None:
        return
    
    bh, bw = base.shape[:2]
    top_left_x = x - bw // 2
    top_left_y = y - bh // 2
    
    # 绘制基础身体
    overlay(frame, base, top_left_x, top_left_y)
    
    # 五官位置（根据实际角色图片调整）
    # 调整说明：
    # - eye_y: 眼睛垂直位置（从顶部算起的比例），值越小越靠上
    # - mouth_y: 嘴巴垂直位置，值越小越靠上
    # - eye_offset_x: 眼睛水平偏移（负数向左，正数向右）
    # - mouth_offset_x: 嘴巴水平偏移（负数向左，正数向右）
    eye_y = int(bh * 0.35)      # 从0.58调整为0.35，眼睛上移
    mouth_y = int(bh * 0.55)    # 从0.75调整为0.55，嘴巴上移
    eye_offset_x = -12          # 眼睛水平偏移
    mouth_offset_x = -20        # 嘴巴水平偏移
    eye_dx = int(bw * 0.15)     # 两眼间距
    
    # 调试信息：打印实际坐标
    if i == 0:  # 只在第一帧打印，避免刷屏
        print(f"   📍 角色定位调试 | 身体尺寸: {bw}x{bh}")
        print(f"      眼睛位置: y={top_left_y + eye_y}, 偏移={eye_offset_x}")
        print(f"      嘴巴位置: y={top_left_y + mouth_y}, 偏移={mouth_offset_x}")
    
    # 绘制眼睛
    eye_img = eye_close if blink_arr[i] else eye_open
    if eye_img is not None:
        overlay(frame, eye_img, top_left_x + bw//2 - eye_dx + eye_offset_x, top_left_y + eye_y)
        overlay(frame, eye_img, top_left_x + bw//2 + eye_dx + eye_offset_x, top_left_y + eye_y)
    
    # 绘制嘴巴
    if is_talking:
        mouth_img = mouth_open
    else:
        mouth_img = mouth_close
    
    if mouth_img is not None:
        overlay(frame, mouth_img, top_left_x + bw//2 + mouth_offset_x, top_left_y + mouth_y)


def render_frames(timeline_data, target_lines=None):
    """渲染帧序列
    
    Args:
        timeline_data: 时间轴数据
        target_lines: 指定要渲染的行ID列表，None表示渲染所有行
    """
    print("\n【Stage 3】渲染帧序列...")
    
    # 加载背景
    bg_file = RES_DIR / "bg" / "office.png"
    BG = load_image(bg_file)
    if BG is None:
        print(f"⚠️ 警告：找不到背景图 {bg_file}，使用默认背景")
        BG = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    if BG.shape[2] == 4:
        BG = BG[:, :, :3]
    
    H, W = BG.shape[:2]
    
    # 加载音频用于口型同步
    audio_file = AUDIO_DIR / "merged_audio.wav"
    audio, sr = sf.read(str(audio_file))
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
        print("❌ 音频为空")
        return
    
    mx = max(vols)
    vols = [v / mx for v in vols]
    MOUTH_THRESHOLD = 0.15
    states = ["open" if v > MOUTH_THRESHOLD else "close" for v in vols]
    N = len(states)
    
    # 加载角色资源
    def load_char_resources(role):
        base_dir = RES_DIR / "characters" / role
        return {
            "base": load_image(base_dir / "base.png"),
            "mouth_open": load_image(base_dir / "mouth" / "open.png"),
            "mouth_close": load_image(base_dir / "mouth" / "close.png"),
            "eye_open": load_image(base_dir / "eye" / "open.png"),
            "eye_close": load_image(base_dir / "eye" / "close.png"),
        }
    
    char_A = load_char_resources("A")
    char_B = load_char_resources("B")
    
    # 角色位置
    A_X, A_Y = int(W * 0.25), int(H * 0.65)
    B_X, B_Y = int(W * 0.75), int(H * 0.65)
    
    # 眨眼序列
    blink_A = blink(N)
    blink_B = blink(N)
    
    # 确定要渲染的行
    if target_lines:
        lines_to_render = [l for l in timeline_data["lines"] if l["dialog_id"] in target_lines]
        print(f"  增量渲染: {target_lines}")
    else:
        lines_to_render = timeline_data["lines"]
        print(f"  全量渲染: {len(lines_to_render)} 行")
    
    # 构建 dialog_id -> 行的映射
    line_map = {l["dialog_id"]: l for l in timeline_data["lines"]}
    
    # 逐帧渲染
    frame_index = {}
    for i in range(N):
        t = i / FPS
        
        # 确定当前说话的角色
        current_role = None
        for line in timeline_data["lines"]:
            if line["start"] <= t < line["end"]:
                current_role = line["role"]
                break
        
        # 创建新帧
        frame = BG.copy()
        
        # 绘制角色A
        force_speak_A = states[i] == "open" if current_role == "A" else False
        draw_character(
            frame, char_A["base"], char_A["mouth_open"], char_A["mouth_close"],
            char_A["eye_open"], char_A["eye_close"],
            A_X, A_Y, force_speak_A, blink_A, i
        )
        
        # 绘制角色B
        force_speak_B = states[i] == "open" if current_role == "B" else False
        draw_character(
            frame, char_B["base"], char_B["mouth_open"], char_B["mouth_close"],
            char_B["eye_open"], char_B["eye_close"],
            B_X, B_Y, force_speak_B, blink_B, i
        )
        
        # 保存帧
        frame_file = FRAMES_DIR / "frames" / f"frame_{i:04d}.png"
        cv2.imwrite(str(frame_file), frame)
    
    # 构建帧索引
    for line in timeline_data["lines"]:
        dialog_id = line["dialog_id"]
        start_frame = int(line["start"] * FPS)
        end_frame = int(line["end"] * FPS)
        frame_index[dialog_id] = {
            "start_frame": start_frame,
            "end_frame": end_frame
        }
    
    # 更新 timeline.json 中的帧范围
    for line in timeline_data["lines"]:
        if line["dialog_id"] in frame_index:
            line["frame_range"] = frame_index[line["dialog_id"]]
    
    save_json(AUDIO_DIR / "timeline.json", timeline_data)
    
    print(f"✅ 帧渲染完成，共 {N} 帧")
    print(f"   保存至: {FRAMES_DIR / 'frames'}")


# ======================
# Stage 4: 视频合成
# ======================
def assemble_video():
    """合成最终视频"""
    print("\n【Stage 4】合成视频...")
    
    frames_pattern = str(FRAMES_DIR / "frames" / "frame_%04d.png")
    audio_file = AUDIO_DIR / "merged_audio.wav"
    output_file = PROJECT_ROOT / "output.mp4"
    
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", frames_pattern,
        "-i", str(audio_file),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(output_file)
    ]
    
    print("  执行 FFmpeg 命令...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ 视频合成完成: {output_file}")
    else:
        print(f"❌ 视频合成失败")
        print(result.stderr)


# ======================
# 命令行接口
# ======================
def main():
    parser = argparse.ArgumentParser(description="沙雕动画工业化流程")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # init
    parser_init = subparsers.add_parser("init", help="初始化项目目录")
    
    # stage1: 生成剧本
    parser_stage1 = subparsers.add_parser("stage1", help="生成剧本")
    parser_stage1.add_argument("--topic", type=str, help="剧本主题")
    
    # stage2: 生成音频和动作
    parser_stage2 = subparsers.add_parser("stage2", help="生成音频和动作配置")
    
    # stage3: 渲染帧
    parser_stage3 = subparsers.add_parser("stage3", help="渲染帧序列")
    parser_stage3.add_argument("--line", type=str, nargs="+", help="指定要渲染的行ID")
    
    # stage4: 合成视频
    parser_stage4 = subparsers.add_parser("stage4", help="合成视频")
    
    # regenerate-line: 重新生成单句
    parser_regen = subparsers.add_parser("regenerate-line", help="重新生成单句台词")
    parser_regen.add_argument("--line", type=str, required=True, help="行ID")
    
    # run-all: 一键运行全流程
    parser_runall = subparsers.add_parser("run-all", help="一键运行全流程")
    # 移除 --topic 参数，因为不再支持自动生成剧本
    
    args = parser.parse_args()
    
    if args.command == "init":
        ensure_dirs()
    
    elif args.command == "stage1":
        print("❌ 错误：stage1 命令已废弃")
        print("   请使用 gen_script.py 生成剧本:")
        print("   python gen_script.py --prompt \"你的剧本主题\"")
        sys.exit(1)
    
    elif args.command == "stage2":
        script_data = load_script()  # 改为load_script
        stage2_generate_all(script_data)
    
    elif args.command == "stage3":
        timeline_data = load_json(AUDIO_DIR / "timeline.json")
        render_frames(timeline_data, target_lines=args.line)
    
    elif args.command == "stage4":
        assemble_video()
    
    elif args.command == "regenerate-line":
        regenerate_single_line(args.line)
        # 自动重新渲染和合成
        timeline_data = load_json(AUDIO_DIR / "timeline.json")
        render_frames(timeline_data, target_lines=[args.line])
        assemble_video()
    
    elif args.command == "run-all":
        print("=" * 60)
        print("🎬 开始完整流程")
        print("=" * 60)
        
        ensure_dirs()
        script_data = load_script()  # 改为load_script，移除topic参数
        
        # 加载现有剧本后直接继续，无需人工确认
        print("\n✅ 剧本加载成功，开始后续流程...\n")

        stage2_generate_all(script_data)
        
        timeline_data = load_json(AUDIO_DIR / "timeline.json")
        render_frames(timeline_data)
        
        assemble_video()
        
        print("\n" + "=" * 60)
        print("🎉 全部完成！请查看 output.mp4")
        print("=" * 60)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
