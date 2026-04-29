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


def load_character_config(role_name, camera_angle="front"):
    """
    加载角色配置文件
    
    参数:
        role_name: 角色名称（如 "A", "B"）
        camera_angle: 拍摄角度（如 "front", "side_left", "side_right"）
    
    返回:
        配置字典，包含脸型方向和五官位置信息
    """
    # 如果是正脸，直接加载角色的config.json
    if camera_angle == "front":
        config_path = RES_DIR / "characters" / role_name / "config.json"
    else:
        # 否则从angles子目录加载对应视角的配置
        config_path = RES_DIR / "characters" / role_name / "angles" / camera_angle / "config.json"
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"   ⚠️ 警告：读取角色配置失败 {role_name}/{camera_angle}: {e}")
    
    # 默认正脸配置
    return {
        "face_direction": "front",
        "features": {
            "eye": {
                "visible_count": 2,
                "position": {"x_ratio": 0.5, "y_ratio": 0.35}
            },
            "mouth": {
                "position": {"x_ratio": 0.5, "y_ratio": 0.55}
            }
        }
    }


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
    """加载剧本文件"""
    script_file = SCRIPT_DIR / "script.json"
    
    if not script_file.exists():
        print(f"❌ 错误：找不到剧本文件 {script_file}")
        print("   请先运行 gen_script.py 生成剧本")
        sys.exit(1)
    
    print(f"📖 加载剧本: {script_file}")
    script_data = load_json(script_file)
    
    if not script_data or "dialogs" not in script_data:
        print("❌ 错误：剧本文件格式无效")
        sys.exit(1)
    
    print(f"   标题: {script_data.get('title', '未命名')}")
    print(f"   对话数: {len(script_data['dialogs'])}")
    
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
    
    # ==================== 文本预处理（防止TTS截断）====================
    # GPT-SoVITS在遇到标点时容易提前截断，即使句子很短
    # 根据项目规范：发送给 TTS API 的文本必须移除所有标点符号
    # 同时处理中英文混合问题
    
    import re
    
    processed_text = text
    
    # 步骤1：移除所有英文单词（避免 "WiFi" 被分成 "Wi Fi"）
    # 将常见英文缩写替换为中文表述
    english_replacements = {
        'WiFi': '无线网络',
        'wifi': '无线网络',
        'WIFI': '无线网络',
        'Wi-Fi': '无线网络',
        'wi-fi': '无线网络',
        'OK': '好的',
        'ok': '好的',
        'OK': '好的',
        'APP': '应用',
        'app': '应用',
        'CPU': '处理器',
        'GPU': '显卡',
        'AI': '人工智能',
        'IP': '网络地址',
        'VIP': '会员',
        'CEO': '首席执行官',
        'CFO': '首席财务官',
        'CTO': '首席技术官',
    }
    
    for eng, chi in english_replacements.items():
        processed_text = processed_text.replace(eng, chi)
    
    # 如果还有剩余的英文字母，直接移除
    processed_text = re.sub(r'[a-zA-Z]+', '', processed_text)
    
    # 步骤2：处理连续标点符号（如 "..."、"……"）
    # 将省略号统一替换为逗号
    processed_text = processed_text.replace('...', '，')
    processed_text = processed_text.replace('…', '，')
    processed_text = processed_text.replace('……', '，')
    
    # 步骤3：将所有标点符号替换为逗号（除了句末保留一个句号）
    # 定义标点分类
    punctuations_strong = ["？", "?", "！", "!"]  # 强标点：极易触发截断
    punctuations_special = ["——", "—", "~", "～"]  # 特殊标点
    punctuations_weak = ["，", ",", "；", ";", "、"]  # 弱标点
    
    # 找出所有标点位置
    all_punct_positions = []
    for punct in punctuations_strong + punctuations_special + punctuations_weak + ["。", "."]:
        start = 0
        while True:
            pos = processed_text.find(punct, start)
            if pos == -1:
                break
            all_punct_positions.append((pos, punct))
            start = pos + len(punct)
    
    punct_count = len(all_punct_positions)
    
    # 如果有标点，进行优化
    if punct_count >= 1:
        # 找到最后一个标点的位置
        last_pos, last_punct = max(all_punct_positions, key=lambda x: x[0])
        
        # 处理最后一个标点之前的部分
        before_last = processed_text[:last_pos]
        after_last = processed_text[last_pos:]  # 包含最后一个标点
        
        # 【激进策略】将前面的所有标点都替换为逗号
        for strong_punct in punctuations_strong:
            before_last = before_last.replace(strong_punct, "，")
        
        for special_punct in punctuations_special:
            before_last = before_last.replace(special_punct, "，")
        
        for weak_punct in punctuations_weak:
            before_last = before_last.replace(weak_punct, "，")
        
        # 最后一个标点统一为句号
        final_punct = "。"
        
        processed_text = before_last + final_punct
        
        if processed_text != text:
            print(f"   📝 文本优化（防截断+去英文）:")
            print(f"      原始: '{text}'")
            print(f"      处理后: '{processed_text}'")
            if len(text) != len(processed_text):
                print(f"      原因：已移除英文单词并优化标点符号")
            else:
                print(f"      原因：检测到 {punct_count} 个标点，已将句中所有标点替换为逗号")
    
    # 根据文本长度估算最小文件大小（经验公式）
    # 每个中文字符约需要 8000-12000 bytes
    estimated_min_size = len(processed_text) * 7000  # 使用处理后的文本长度
    
    # 自动重试逻辑
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            print(f"\n   🔄 第 {attempt}/{max_retries} 次重试（更换随机种子）...")
        
        # 为每次重试生成不同的种子
        import hashlib
        seed_text = f"{role}_{text}_{emotion}_attempt{attempt}"
        fixed_seed = int(hashlib.md5(seed_text.encode()).hexdigest(), 16) % (2**31)
        
        data = {
            "text": processed_text,  # 使用处理后的文本（防止截断）
            "text_lang": "zh",
            "ref_audio_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_lang": "zh",
            "top_k": 20,  # 增加top_k，让生成更连贯（从15增加到20）
            "top_p": 0.9,  # 提高top_p，允许更多多样性（从0.85提高到0.9）
            "temperature": EMOTION_CONFIG[emotion]["temperature"],
            "speed_factor": final_speed,
            "seed": fixed_seed,  # 使用固定但可变的种子
            "split_bucket": False,  # 禁用分桶，避免句子被分割
            "text_split_method": "cut0",  # 不使用切分方法
            "repetition_penalty": 1.2,  # 降低重复惩罚，避免过早停止
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
                    
                    # ==================== 检查音频是否被截断 ====================
                    # 估算预期时长：中文语速约每秒3-5个字符
                    estimated_duration_min = len(text) / 5.0  # 最慢语速
                    estimated_duration_max = len(text) / 3.0  # 最快语速
                    
                    # 考虑情绪对语速的影响
                    estimated_duration_min /= final_speed
                    estimated_duration_max /= final_speed
                    
                    # 【增强检测】如果实际时长远小于预期，可能被截断了
                    # 降低阈值从 0.6 到 0.7，更敏感地检测截断
                    if duration < estimated_duration_min * 0.7:  # 低于预期的70%（原为60%）
                        print(f"   ⚠️  警告：音频可能被截断！")
                        print(f"      文本长度: {len(text)} 字符")
                        print(f"      预期时长: {estimated_duration_min:.2f}s - {estimated_duration_max:.2f}s")
                        print(f"      实际时长: {duration:.2f}s (过短)")
                        
                        if attempt < max_retries:
                            print(f"      将更换种子重试...")
                            try:
                                Path(output_file).unlink()
                            except:
                                pass
                            continue
                        else:
                            print(f"   ⚠️  警告：重试{max_retries}次后仍然过短，但将继续使用")
                
                    
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


def generate_actions_for_line(text, emotion, duration):
    """
    根据台词内容和情绪自动生成动作配置（增强版）
    
    支持的动作类型：
    1. eye: 眼睛状态（睁大、眯眼等）
    2. mouth: 嘴巴夸张程度（正常、张大、超大）
    3. effect: 特效（问号、感叹号、震动线等）
    4. camera: 运镜（缩放、平移）
    5. shake: 角色抖动
    
    参数:
        text: 台词文本
        emotion: 情绪类型
        duration: 音频时长（秒）
    
    返回:
        动作列表
    """
    actions = []
    
    # ==================== 1. 眼睛状态控制 ====================
    # 惊讶/震惊时，眼睛睁大并停留（增加持续时间）
    if emotion == "惊讶" or any(word in text for word in ["震惊", "哇", "啊", "天哪"]):
        actions.append({
            "type": "eye",
            "name": "wide_open",  # 睁大眼睛
            "start_offset": 0.0,
            "duration": min(1.2, duration * 0.4)  # 增加到1.2秒或时长的40%
        })
    
    # 生气时，眼睛眯起（增加持续时间）
    elif emotion == "生气" and any(word in text for word in ["哼", "切", "就这"]):
        actions.append({
            "type": "eye",
            "name": "narrow",  # 眪眼
            "start_offset": 0.2,
            "duration": min(0.8, duration * 0.3)  # 增加到0.8秒
        })
    
    # ==================== 2. 嘴巴夸张程度 ====================
    # 大声说话/喊叫时，嘴巴张大（增加持续时间）
    if any(char in text for char in ["！", "!", "？", "?"]) and len(text) < 15:
        # 短句+标点 = 可能是大喊
        actions.append({
            "type": "mouth",
            "name": "extra_wide",  # 超大张嘴
            "start_offset": 0.0,
            "duration": min(0.6, duration * 0.2)  # 增加到0.6秒
        })
    
    # ==================== 3. 特效叠加 ====================
    # 问号特效（增加持续时间）
    if "？" in text or "???" in text or "？？" in text:
        actions.append({
            "type": "effect",
            "name": "question_marks",
            "start_offset": 0.2,
            "duration": 1.2,  # 从0.8增加到1.2秒
            "position": "above_head"  # 头顶位置
        })
    
    # 感叹号/震惊特效（增加持续时间）
    if "！" in text or "!!!" in text or "！！" in text:
        actions.append({
            "type": "effect",
            "name": "exclamation_marks",
            "start_offset": 0.0,
            "duration": 1.0,  # 从0.6增加到1.0秒
            "position": "above_head"
        })
        
        # 震惊时添加震动线（增加持续时间）
        if emotion in ["惊讶", "生气"]:
            actions.append({
                "type": "effect",
                "name": "shock_lines",
                "start_offset": 0.0,
                "duration": 0.8,  # 从0.5增加到0.8秒
                "intensity": "high"
            })
    
    # 省略号特效（无语、思考，增加持续时间）
    if "..." in text or "……" in text:
        actions.append({
            "type": "effect",
            "name": "dots",
            "start_offset": 0.3,
            "duration": 1.5,  # 从1.0增加到1.5秒
            "position": "side"
        })
    
    # ==================== 4. 运镜效果 ====================
    # 仅在极度激动的情况下才添加运镜（严格控制触发条件）
    # 必须同时满足：强烈情绪 + 短句 + 强烈标点
    if emotion in ["生气", "惊讶"]:
        # 必须包含强烈标点
        has_strong_punctuation = any(char in text for char in ["！", "!", "？", "?"])
        
        # 必须是短句（情绪爆发通常是短句）
        is_short = len(text) < 12
        
        # 只有同时满足才触发运镜
        if has_strong_punctuation and is_short:
            zoom_duration = min(0.5, duration * 0.25)
            actions.append({
                "type": "camera",
                "name": "zoom_in",
                "value": 1.15,  # 放大15%
                "start_offset": 0.0,
                "duration": zoom_duration,
                "easing": "ease-out"
            })
            
            # 快速拉回
            actions.append({
                "type": "camera",
                "name": "zoom_out",
                "value": 1.0,  # 恢复原大小
                "start_offset": zoom_duration,
                "duration": 0.3,
                "easing": "ease-in"
            })
    
    # ==================== 5. 角色抖动 ====================
    # 极度生气时抖动
    if emotion == "生气" and any(word in text for word in ["气死", "混蛋", "可恶"]):
        actions.append({
            "type": "shake",
            "intensity": 5,  # 抖动强度（像素）
            "frequency": 10,  # 频率（Hz）
            "start_offset": 0.0,
            "duration": min(0.5, duration * 0.2)
        })
    
    # ==================== 6. 关键词触发的特殊动作 ====================
    # "看"相关词汇 → 指向动作（未来可扩展）
    if any(word in text for word in ["看", "瞧", "注意"]):
        pass  # TODO: 添加指向手势
    
    # "笑"相关词汇 → 大笑动作
    if any(word in text for word in ["哈哈", "嘿嘿", "嘻嘻"]):
        actions.append({
            "type": "face",
            "name": "laughing",  # 大笑表情
            "start_offset": 0.1,
            "duration": min(0.6, duration * 0.25)
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
        actions = generate_actions_for_line(text, emotion, duration)
        
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
            "actions": actions,
            "camera_angle": dialog.get("camera_angle", "front")  # 添加视角信息
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
    
    # 合并音频（会返回实际的时间偏移信息）
    actual_timings = merge_audio_files(audio_files, lines_for_merge)
    
    # ==================== 根据实际音频时长重新校准时间轴 ====================
    if actual_timings:
        print("\n   🔄 根据实际音频重新校准时间轴...")
        
        for idx, line in enumerate(timeline_data["lines"]):
            if idx < len(actual_timings):
                actual_start, actual_duration = actual_timings[idx]
                line["start"] = round(actual_start, 3)
                line["end"] = round(actual_start + actual_duration, 3)
                line["duration"] = round(actual_duration, 3)
        
        # 保存校准后的时间轴
        save_json(AUDIO_DIR / "timeline.json", timeline_data)
        print(f"   ✅ 时间轴已重新校准")
    
    return timeline_data


def merge_audio_files(audio_files, lines_data):
    """
    合并所有音频文件，并应用音量归一化，随机添加背景音效
    
    返回:
        list of tuples: [(start_time, duration), ...] 每句台词的实际起始时间和时长
    """
    print("\n🎧 合并音频...")
    
    if not audio_files:
        print("❌ 没有音频可合并")
        return []
    
    merged_audio = []
    sample_rate = None
    all_segments = []  # 存储所有音频片段及其角色信息
    actual_timings = []  # 记录每句台词的实际时间
    current_time = 0.0  # 当前累计时间（秒）
    
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
    
    # 加载音效素材（用于随机插入）
    sfx_dir = RES_DIR / "sfx"
    sfx_files = list(sfx_dir.glob("*.wav"))
    sfx_samples = {}
    if sfx_files:
        print(f"\n   🔊 加载音效素材: {len(sfx_files)} 个")
        for sfx_file in sfx_files:
            try:
                sfx_audio, sfx_sr = sf.read(str(sfx_file))
                if len(sfx_audio.shape) > 1:
                    sfx_audio = sfx_audio.mean(axis=1)
                # 重采样到目标采样率
                if sfx_sr != sample_rate:
                    import librosa
                    sfx_audio = librosa.resample(sfx_audio, orig_sr=sfx_sr, target_sr=sample_rate)
                sfx_samples[sfx_file.stem] = sfx_audio
                print(f"      ✅ {sfx_file.name}")
            except Exception as e:
                print(f"      ⚠️  加载失败 {sfx_file.name}: {e}")
    
    # 第三遍：应用归一化并合并，随机插入音效
    print("\n   🔧 应用归一化、插入音效并合并...")
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
            current_time += SILENCE_GAP  # 更新当前时间
        
        # 随机插入音效（30%概率，在台词开始前）
        sfx_duration = 0.0
        if sfx_samples and random.random() < 0.3:
            sfx_name = random.choice(list(sfx_samples.keys()))
            sfx_audio = sfx_samples[sfx_name]
            
            # 降低音效音量，避免盖过语音
            sfx_volume = 0.15
            sfx_audio = sfx_audio * sfx_volume
            
            # 计算音效时长
            sfx_duration = len(sfx_audio) / sample_rate
            
            # 在台词前插入短促静音和音效
            pre_silence = [0.0] * int(sample_rate * 0.1)  # 100ms前置静音
            merged_audio.extend(pre_silence)
            merged_audio.extend(sfx_audio)
            
            post_silence = [0.0] * int(sample_rate * 0.05)  # 50ms后置静音
            merged_audio.extend(post_silence)
            
            current_time += 0.1 + sfx_duration + 0.05  # 更新当前时间
            
            print(f"      🎵 插入音效: {sfx_name}.wav (时长:{sfx_duration:.2f}s)")
        
        # 记录该句台词的起始时间（音效插入后，台词开始前）
        line_start_time = current_time
        
        # 添加台词音频
        merged_audio.extend(audio)
        audio_duration = len(audio) / sample_rate
        current_time += audio_duration  # 更新当前时间
        
        # 记录该句的实际起始时间和时长（用于音画同步）
        actual_timings.append((line_start_time, audio_duration))
    
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
    
    # 返回实际的时间信息，用于校准时间轴
    print(f"\n   📊 实际时间统计:")
    for idx, (start, dur) in enumerate(actual_timings):
        print(f"      [{idx+1}] start={start:.3f}s, duration={dur:.3f}s")
    
    return actual_timings


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

def check_and_create_placeholder_resources():
    """检查并生成缺失的资源占位符"""
    print("   🔍 检查资源文件...")
    
    # 定义需要检查的资源路径
    required_resources = {
        "背景图": [
            RES_DIR / "background.png",
            RES_DIR / "bg" / "office.png",
            RES_DIR / "bg" / "default.png",
        ],
        "角色A基础图": [RES_DIR / "characters" / "A" / "base.png"],
        "角色B基础图": [RES_DIR / "characters" / "B" / "base.png"],
        "角色A眼睛-睁开": [RES_DIR / "characters" / "A" / "eye" / "open.png"],
        "角色A眼睛-闭合": [RES_DIR / "characters" / "A" / "eye" / "close.png"],
        "角色A嘴巴-张开": [RES_DIR / "characters" / "A" / "mouth" / "open.png"],
        "角色A嘴巴-闭合": [RES_DIR / "characters" / "A" / "mouth" / "close.png"],
        "角色B眼睛-睁开": [RES_DIR / "characters" / "B" / "eye" / "open.png"],
        "角色B眼睛-闭合": [RES_DIR / "characters" / "B" / "eye" / "close.png"],
        "角色B嘴巴-张开": [RES_DIR / "characters" / "B" / "mouth" / "open.png"],
        "角色B嘴巴-闭合": [RES_DIR / "characters" / "B" / "mouth" / "close.png"],
    }
    
    created_count = 0
    
    for resource_name, paths in required_resources.items():
        # 检查是否有任何一个路径存在
        exists = any(p.exists() for p in paths)
        
        if not exists:
            # 使用第一个路径创建占位符
            target_path = paths[0]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 根据资源类型创建不同尺寸的占位符
            if "背景" in resource_name:
                # 背景图：1280x720 渐变蓝色
                bg = np.zeros((720, 1280, 3), dtype=np.uint8)
                for i in range(720):
                    blue_value = int(150 + (i / 720) * 105)
                    green_value = int(100 + (i / 720) * 50)
                    red_value = int(50 + (i / 720) * 50)
                    bg[i, :] = [red_value, green_value, blue_value]
                cv2.imwrite(str(target_path), bg)
                print(f"      ⚠️  创建背景占位符: {target_path}")
            
            elif "base" in str(target_path):
                # 角色基础图：矩形 200x300，纯色+描边
                base = np.ones((300, 200, 4), dtype=np.uint8) * 255  # 白色背景
                # 绘制灰色矩形身体（带透明度的纯色填充）
                cv2.rectangle(base, (10, 10), (190, 290), (200, 200, 200, 255), -1)
                # 绘制黑色描边
                cv2.rectangle(base, (10, 10), (190, 290), (0, 0, 0, 255), 3)
                cv2.imwrite(str(target_path), base)
                print(f"      ⚠️  创建{resource_name}占位符: {target_path}")
            
            elif "eye" in str(target_path):
                # 眼睛素材：60x60 圆形
                eye = np.zeros((60, 60, 4), dtype=np.uint8)
                # 绘制白色眼白
                cv2.circle(eye, (30, 30), 25, (255, 255, 255, 255), -1)
                # 绘制黑色瞳孔
                cv2.circle(eye, (30, 30), 10, (0, 0, 0, 255), -1)
                cv2.imwrite(str(target_path), eye)
                print(f"      ⚠️  创建{resource_name}占位符: {target_path}")
            
            elif "mouth" in str(target_path):
                # 嘴巴素材：80x40 椭圆形
                mouth = np.zeros((40, 80, 4), dtype=np.uint8)
                if "open" in str(target_path):
                    # 张开的嘴巴：红色椭圆
                    cv2.ellipse(mouth, (40, 20), (30, 15), 0, 0, 360, (255, 0, 0, 255), -1)
                else:
                    # 闭合的嘴巴：细线
                    cv2.line(mouth, (20, 20), (60, 20), (0, 0, 0, 255), 3)
                cv2.imwrite(str(target_path), mouth)
                print(f"      ⚠️  创建{resource_name}占位符: {target_path}")
            
            created_count += 1
    
    if created_count > 0:
        print(f"   ✅ 共创建了 {created_count} 个资源占位符")
    else:
        print(f"   ✅ 所有资源文件已存在")


def get_active_actions(timeline_line, current_time):
    """
    获取当前时间点生效的所有动作
    
    参数:
        timeline_line: 时间轴中的一行数据（包含actions列表）
        current_time: 当前时间（秒）
    
    返回:
        字典，按类型分组的活跃动作
        {
            "face": [{"name": "angry", ...}],
            "eye": [{"name": "wide_open", ...}],
            "mouth": [{"name": "extra_wide", ...}],
            "effect": [...],
            "camera": [...],
            "shake": [...]
        }
    """
    if not timeline_line or "actions" not in timeline_line:
        return {}
    
    active = {}
    line_start = timeline_line["start"]
    
    for action in timeline_line["actions"]:
        start_offset = action.get("start_offset", 0.0)
        duration = action.get("duration", -1)
        
        # 计算绝对时间
        action_start = line_start + start_offset
        if duration == -1:
            # 持续到行结束
            action_end = timeline_line["end"]
        else:
            action_end = action_start + duration
        
        # 检查当前时间是否在动作有效期内
        if action_start <= current_time < action_end:
            action_type = action.get("type")
            if action_type not in active:
                active[action_type] = []
            active[action_type].append(action)
    
    return active


def apply_camera_effect(frame, camera_actions):
    """应用运镜效果"""
    if not camera_actions:
        return frame, 1.0
    
    # 取最后一个相机动作（优先级最高）
    latest_camera = camera_actions[-1]
    camera_name = latest_camera.get("name", "")
    
    if camera_name == "zoom_in":
        scale = latest_camera.get("value", 1.15)
    elif camera_name == "zoom_out":
        scale = latest_camera.get("value", 1.0)
    else:
        return frame, 1.0
    
    # 简单的缩放实现（居中缩放）
    h, w = frame.shape[:2]
    new_h, new_w = int(h / scale), int(w / scale)
    
    # 裁剪中心区域
    start_y = (h - new_h) // 2
    start_x = (w - new_w) // 2
    
    cropped = frame[start_y:start_y+new_h, start_x:start_x+new_w]
    
    # 缩放回原尺寸
    zoomed = cv2.resize(cropped, (w, h))
    
    return zoomed, scale


def apply_shake_effect(x, y, shake_actions, frame_index):
    """应用抖动效果"""
    if not shake_actions:
        return x, y
    
    # 取强度最高的抖动
    strongest = max(shake_actions, key=lambda a: a.get("intensity", 0))
    intensity = strongest.get("intensity", 5)
    frequency = strongest.get("frequency", 10)
    
    # 基于帧索引和频率计算偏移
    import math
    offset_x = int(intensity * math.sin(2 * math.pi * frequency * frame_index / FPS))
    offset_y = int(intensity * math.cos(2 * math.pi * frequency * frame_index / FPS))
    
    return x + offset_x, y + offset_y


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


def draw_character_with_actions(frame, base, mouth_open, mouth_close, eye_open, eye_close,
                                x, y, is_talking, blink_arr, i, active_actions=None, role="A", camera_angle="front"):
    """
    绘制角色（支持正脸/侧脸多视角）
    
    参数:
        frame: 画布
        base: 角色基础图
        mouth_open/mouth_close: 张嘴/闭嘴素材
        eye_open/eye_close: 睁眼/闭眼素材
        x, y: 角色中心坐标
        is_talking: 是否在说话
        blink_arr: 眨眼序列
        i: 当前帧索引
        active_actions: 当前生效的动作字典
        role: 角色名称（用于加载配置）
        camera_angle: 拍摄角度（front, side_left, side_right等）
    """
    if base is None:
        return
    
    bh, bw = base.shape[:2]

    top_left_x = x - bw // 2
    top_left_y = y - bh // 2
    
    # 加载角色配置（根据拍摄角度）
    config = load_character_config(role, camera_angle)
    face_direction = config.get("face_direction", "front")
    features = config.get("features", {})
    
    # 绘制基础身体
    overlay(frame, base, top_left_x, top_left_y)
    
    # ==================== 根据脸型确定五官位置 ====================
    if face_direction == "front":
        # ========== 正脸：两只眼睛 + 居中嘴巴 ==========
        head_height = int(bh * 0.35)
        head_top = top_left_y + 15
        
        # 眼睛位置：头部区域的35%处
        eye_y = head_top + int(head_height * 0.35)
        eye_dx = int(bw * 0.20)
        
        # 嘴巴位置：头部区域的85%处
        mouth_y = head_top + int(head_height * 0.85)
        
        center_x = top_left_x + bw // 2
        
        # 获取眼睛状态
        default_eye = eye_close if blink_arr[i] else eye_open
        
        # 检查是否有特殊眼睛动作
        if active_actions and "eye" in active_actions:
            eye_action = active_actions["eye"][-1]
            eye_name = eye_action.get("name", "")
            
            if eye_name == "wide_open":
                wide_eye_path = RES_DIR / "characters" / role / "eye" / "surprised.png"
                wide_eye = load_image(wide_eye_path)
                if wide_eye is not None:
                    default_eye = wide_eye
        
        # 绘制双眼
        if default_eye is not None:
            overlay(frame, default_eye, 
                   center_x - eye_dx - int(default_eye.shape[1]//2), 
                   eye_y - int(default_eye.shape[0]//2))
            overlay(frame, default_eye, 
                   center_x + eye_dx - int(default_eye.shape[1]//2), 
                   eye_y - int(default_eye.shape[0]//2))
        
        # 获取嘴巴状态
        default_mouth = mouth_open if is_talking else mouth_close
        
        # 检查是否有特殊嘴巴动作
        if active_actions and "mouth" in active_actions:
            mouth_action = active_actions["mouth"][-1]
            mouth_name = mouth_action.get("name", "")
            
            if mouth_name == "extra_wide":
                extra_wide_path = RES_DIR / "characters" / role / "mouth" / "extra_wide.png"
                extra_wide = load_image(extra_wide_path)
                if extra_wide is not None:
                    default_mouth = extra_wide
        
        # 绘制嘴巴（水平居中）
        if default_mouth is not None:
            overlay(frame, default_mouth, 
                   center_x - int(default_mouth.shape[1]//2), 
                   mouth_y - int(default_mouth.shape[0]//2))
    
    elif face_direction in ["side_left", "side_right"]:
        # ========== 侧脸：双眼整体偏移 + 嘴巴偏移 ==========
        eye_pos = features.get("eye", {}).get("position", {"x_ratio": 0.65, "y_ratio": 0.35})
        mouth_pos = features.get("mouth", {}).get("position", {"x_ratio": 0.70, "y_ratio": 0.55})
        
        # 计算绝对坐标
        center_x = top_left_x + int(bw * eye_pos.get("x_ratio", 0.65))
        eye_y = top_left_y + int(bh * eye_pos.get("y_ratio", 0.35))
        
        mouth_x = top_left_x + int(bw * mouth_pos.get("x_ratio", 0.70))
        mouth_y = top_left_y + int(bh * mouth_pos.get("y_ratio", 0.55))
        
        # 眼睛间距（比正脸略小，模拟透视）
        eye_dx = int(bw * 0.15)
        
        # 获取眼睛状态
        default_eye = eye_close if blink_arr[i] else eye_open
        
        # 检查是否有特殊眼睛动作
        if active_actions and "eye" in active_actions:
            eye_action = active_actions["eye"][-1]
            eye_name = eye_action.get("name", "")
            
            if eye_name == "wide_open":
                wide_eye_path = RES_DIR / "characters" / role / "eye" / "surprised.png"
                wide_eye = load_image(wide_eye_path)
                if wide_eye is not None:
                    default_eye = wide_eye
        
        # 绘制双眼（整体偏移）
        if default_eye is not None:
            overlay(frame, default_eye, 
                   center_x - eye_dx - int(default_eye.shape[1]//2), 
                   eye_y - int(default_eye.shape[0]//2))
            overlay(frame, default_eye, 
                   center_x + eye_dx - int(default_eye.shape[1]//2), 
                   eye_y - int(default_eye.shape[0]//2))
        
        # 获取嘴巴状态
        default_mouth = mouth_open if is_talking else mouth_close
        
        # 检查是否有特殊嘴巴动作
        if active_actions and "mouth" in active_actions:
            mouth_action = active_actions["mouth"][-1]
            mouth_name = mouth_action.get("name", "")
            
            if mouth_name == "extra_wide":
                extra_wide_path = RES_DIR / "characters" / role / "mouth" / "extra_wide.png"
                extra_wide = load_image(extra_wide_path)
                if extra_wide is not None:
                    default_mouth = extra_wide
        
        # 绘制嘴巴（偏移位置）
        if default_mouth is not None:
            overlay(frame, default_mouth, 
                   mouth_x - int(default_mouth.shape[1]//2), 
                   mouth_y - int(default_mouth.shape[0]//2))


def render_frames():

        mouth_x = top_left_x + int(bw * mouth_pos.get("x_ratio", 0.70))
        mouth_y = top_left_y + int(bh * mouth_pos.get("y_ratio", 0.55))
        
        # 获取眼睛状态
        default_eye = eye_close if blink_arr[i] else eye_open
        
        # 检查是否有特殊眼睛动作（侧脸暂不支持特殊眼睛）
        # TODO: 未来可以添加侧脸专用的惊讶眼神等
        
        # 绘制单眼
        if default_eye is not None:
            overlay(frame, default_eye, 
                   eye_x - int(default_eye.shape[1]//2), 
                   eye_y - int(default_eye.shape[0]//2))
        
        # 获取嘴巴状态
        default_mouth = mouth_open if is_talking else mouth_close
        
        # 检查是否有特殊嘴巴动作（侧脸暂不支持）
        
        # 绘制单边嘴巴
        if default_mouth is not None:
            overlay(frame, default_mouth, 
                   mouth_x - int(default_mouth.shape[1]//2), 
                   mouth_y - int(default_mouth.shape[0]//2))


def render_frames():
    """渲染所有帧（支持动作系统）"""
    print("\n【Stage 3】渲染帧序列...")
    
    # ==================== 创建必要的目录 ====================
    frames_dir = FRAMES_DIR / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    print(f"   ✅ 确保帧目录存在: {frames_dir}")
    
    # ==================== 检查并生成缺失的资源占位符 ====================
    check_and_create_placeholder_resources()
    
    # 加载时间轴
    timeline_data = load_json(AUDIO_DIR / "timeline.json")
    if not timeline_data or "lines" not in timeline_data:
        print("❌ 时间轴文件无效")
        return
    
    # 加载背景图（尝试多个可能的路径）
    bg_candidates = [
        RES_DIR / "background.png",
        RES_DIR / "bg" / "office.png",
        RES_DIR / "bg" / "default.png",
    ]
    
    BG = None
    for bg_file in bg_candidates:
        if bg_file.exists():
            BG = cv2.imread(str(bg_file))
            if BG is not None:
                print(f"   ✅ 使用背景图: {bg_file}")
                break
    
    if BG is None:
        print(f"   ⚠️ 警告：找不到背景图，使用渐变蓝色背景")
        # 创建渐变蓝色背景（从上到下的渐变）
        BG = np.zeros((720, 1280, 3), dtype=np.uint8)
        for i in range(720):
            # 从浅蓝到深蓝的渐变
            blue_value = int(150 + (i / 720) * 105)  # 150-255
            green_value = int(100 + (i / 720) * 50)   # 100-150
            red_value = int(50 + (i / 720) * 50)      # 50-100
            BG[i, :] = [red_value, green_value, blue_value]
    
    if BG.shape[2] == 4:
        BG = BG[:, :, :3]
    
    H, W = BG.shape[:2]
    
    # 加载音频用于口型同步
    audio_file = AUDIO_DIR / "merged_audio.wav"
    audio, sr = sf.read(str(audio_file))
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)
    
    # ==================== 去除前端静音（关键修复）====================
    # TTS生成的音频开头可能有静音，导致音画不同步
    # 检测并去除开头的静音部分
    
    # 计算短时能量
    frame_length = int(sr * 0.02)  # 20ms帧长
    hop_length = int(sr * 0.01)    # 10ms跳步
    
    # 找到第一个非静音帧
    silence_threshold = 0.001  # 静音阈值
    first_speech_frame = 0
    
    for i in range(0, min(len(audio), sr * 2), hop_length):  # 只检查前2秒
        frame = audio[i:i+frame_length]
        if len(frame) == 0:
            break
        energy = np.sqrt(np.mean(frame**2))
        if energy > silence_threshold:
            first_speech_frame = i
            break
    
    # 如果检测到前端静音，裁剪掉
    if first_speech_frame > 0:
        silence_duration = first_speech_frame / sr
        print(f"   ⚠️  检测到前端静音: {silence_duration:.3f}s，正在裁剪...")
        audio = audio[first_speech_frame:]
        
        # ==================== 关键修复：重新计算并校准时间轴 ====================
        # 注意：这里不应该直接修改 timeline.json，因为 merge_audio_files 已经记录了精确的时间
        # 我们只需要确保渲染时使用正确的音频即可
        
        # 重新加载时间轴（确保使用最新校准的数据）
        timeline_data = load_json(AUDIO_DIR / "timeline.json")
        
        print(f"   ✅ 已裁剪前端静音，音频时长减少: {silence_duration:.3f}s")
        print(f"   📊 当前音频总帧数: {len(audio)} ({len(audio)/sr:.2f}s)")
    
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
    
    # ==================== 关键修复：根据实际音频时长验证时间轴 ====================
    actual_audio_duration = len(audio) / sr
    expected_frames = int(actual_audio_duration * FPS)
    
    print(f"\n   🔍 音画同步检查:")
    print(f"      实际音频时长: {actual_audio_duration:.3f}s")
    print(f"      理论帧数: {expected_frames} 帧")
    print(f"      实际渲染帧数: {N} 帧")
    
    if abs(N - expected_frames) > 2:  # 允许2帧误差
        print(f"   ⚠️  警告：帧数不匹配！可能存在音画不同步")
        print(f"      建议：检查 TTS 生成的音频是否有异常静音或截断")
    
    # 加载角色资源（支持多视角）
    def load_char_resources(role_name, camera_angle="front"):
        """
        加载角色资源，支持正脸和不同视角
        
        参数:
            role_name: 角色名称（如 "A", "B"）
            camera_angle: 拍摄角度（如 "front", "side_left", "side_right"）
        
        返回:
            角色资源字典
        """
        if camera_angle == "front":
            base_dir = RES_DIR / "characters" / role_name
        else:
            # 从angles子目录加载对应视角的素材
            base_dir = RES_DIR / "characters" / role_name / "angles" / camera_angle
            
            # 如果视角素材不存在，降级到正脸
            if not base_dir.exists():
                print(f"   ⚠️ 警告：{role_name}的{camera_angle}视角素材不存在，使用正脸")
                base_dir = RES_DIR / "characters" / role_name
                camera_angle = "front"
        
        return {
            "base": load_image(base_dir / "base.png"),
            "mouth_open": load_image(base_dir / "mouth" / "open.png"),
            "mouth_close": load_image(base_dir / "mouth" / "close.png"),
            "eye_open": load_image(base_dir / "eye" / "open.png"),
            "eye_close": load_image(base_dir / "eye" / "close.png"),
            "camera_angle": camera_angle  # 记录实际使用的视角
        }
    
    # 预加载基础角色资源（正脸）
    char_resources_cache = {}
    for role in ["A", "B"]:
        char_resources_cache[role] = load_char_resources(role, "front")
    
    # 角色位置
    A_X, A_Y = int(W * 0.25), int(H * 0.65)
    B_X, B_Y = int(W * 0.75), int(H * 0.65)
    
    # 眨眼序列
    blink_A = blink(N)
    blink_B = blink(N)
    
    # 创建帧索引
    frame_index = {}
    
    # 用于跟踪视角变化的变量
    last_dialog_id = None
    
    # 逐帧渲染
    print(f"   开始渲染 {N} 帧...")
    for i in range(N):
        t = i * FRAME_DURATION
        
        # 确定当前台词
        current_role = None
        current_line = None
        current_camera_angle = "front"  # 默认正脸
        
        for line in timeline_data["lines"]:
            if line["start"] <= t < line["end"]:
                current_role = line["role"]
                current_line = line
                # 提取拍摄角度，默认为front
                current_camera_angle = line.get("camera_angle", "front")
                break
        
        # 调试输出：在每句台词开始时输出视角信息
        if current_line:
            dialog_id = current_line.get("dialog_id")
            if dialog_id != last_dialog_id:
                print(f"   📷 [{dialog_id}] 角色={current_role}, 视角={current_camera_angle}, 台词={current_line.get('text', '')[:15]}...")
                last_dialog_id = dialog_id
        
        # 创建新帧
        frame = BG.copy()
        
        # ==================== 应用运镜效果 ====================
        # 默认不缩放
        scale = 1.0
        
        if current_line:
            active_actions = get_active_actions(current_line, t)
            camera_actions = active_actions.get("camera", [])
            
            # 只有当有camera动作时才应用缩放
            if camera_actions:
                frame, scale = apply_camera_effect(frame, camera_actions)
        
        # 根据缩放调整角色位置（仅在缩放时调整）
        A_X_scaled = int(A_X * scale)
        B_X_scaled = int(B_X * scale)
        A_Y_scaled = int(A_Y * scale)
        B_Y_scaled = int(A_Y * scale)
        
        # ==================== 获取A角色的活跃动作 ====================
        active_actions_A = {}
        if current_line and current_role == "A":
            active_actions_A = get_active_actions(current_line, t)
        
        # 应用抖动效果
        A_X_final, A_Y_final = apply_shake_effect(A_X_scaled, A_Y_scaled, 
                                                   active_actions_A.get("shake", []), i)
        
        # 绘制角色A（根据camera_angle动态加载资源）
        force_speak_A = states[i] == "open" if current_role == "A" else False
        
        if current_role == "A":
            # 根据拍摄角度加载对应的角色资源
            role_resources_A = load_char_resources("A", current_camera_angle)
        else:
            # 如果当前不是A说话，使用缓存的正脸资源
            role_resources_A = char_resources_cache["A"]

        
        draw_character_with_actions(
            frame, 
            role_resources_A["base"], 
            role_resources_A["mouth_open"], 
            role_resources_A["mouth_close"],
            role_resources_A["eye_open"], 
            role_resources_A["eye_close"],
            A_X_final, A_Y_final, force_speak_A, blink_A, i,
            active_actions=active_actions_A,
            role="A",  # 传递基础角色名称用于加载配置
            camera_angle=role_resources_A.get("camera_angle", "front")  # 传递实际使用的视角
        )
        
        # ==================== 获取B角色的活跃动作 ====================
        active_actions_B = {}
        if current_line and current_role == "B":
            active_actions_B = get_active_actions(current_line, t)
        
        # 应用抖动效果
        B_X_final, B_Y_final = apply_shake_effect(B_X_scaled, B_Y_scaled,
                                                   active_actions_B.get("shake", []), i)
        
        # 绘制角色B（根据camera_angle动态加载资源）
        force_speak_B = states[i] == "open" if current_role == "B" else False
        
        if current_role == "B":
            # 根据拍摄角度加载对应的角色资源
            role_resources_B = load_char_resources("B", current_camera_angle)
        else:
            # 如果当前不是B说话，使用缓存的正脸资源
            role_resources_B = char_resources_cache["B"]
        draw_character_with_actions(
            frame, 
            role_resources_B["base"], 
            role_resources_B["mouth_open"], 
            role_resources_B["mouth_close"],
            role_resources_B["eye_open"], 
            role_resources_B["eye_close"],
            B_X_final, B_Y_final, force_speak_B, blink_B, i,
            active_actions=active_actions_B,
            role="B",  # 传递基础角色名称用于加载配置
            camera_angle=role_resources_B.get("camera_angle", "front")  # 传递实际使用的视角
        )

        # ==================== 渲染特效层 ====================
        # TODO: 这里可以添加特效渲染逻辑（问号、感叹号等）
        # 需要加载特效图片并叠加到frame上
        
        # 保存帧
        frame_file = FRAMES_DIR / "frames" / f"frame_{i:04d}.png"
        cv2.imwrite(str(frame_file), frame)
        
        # 进度提示（每100帧）
        if i % 100 == 0:
            print(f"     渲染进度: {i}/{N} ({i*100//N}%)")
    
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
def generate_subtitle_file(timeline_data):
    """生成SRT字幕文件"""
    print("\n  📝 生成字幕文件...")
    
    subtitle_file = AUDIO_DIR / "subtitles.srt"
    
    import re
    
    with open(subtitle_file, 'w', encoding='utf-8') as f:
        idx = 1
        for line in timeline_data["lines"]:
            start_time = line["start"]
            end_time = line["end"]
            
            # 转换为SRT时间格式 (HH:MM:SS,mmm)
            def format_srt_time(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                millis = int((seconds % 1) * 1000)
                return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
            
            start_str = format_srt_time(start_time)
            end_str = format_srt_time(end_time)
            
            # ==================== 清理字幕文本 ====================
            subtitle_text = line['text']
            
            # 移除开头的标点符号（问号、感叹号等）
            subtitle_text = re.sub(r'^[？?！!。，,；;：:""''（）()【】\[\]]+', '', subtitle_text)
            
            # 写入字幕块
            f.write(f"{idx}\n")
            f.write(f"{start_str} --> {end_str}\n")
            f.write(f"{subtitle_text}\n\n")
            
            idx += 1
    
    print(f"  ✅ 字幕文件已生成: {subtitle_file}")
    return subtitle_file


def assemble_video():
    """合成最终视频（带字幕）"""
    print("\n【Stage 4】合成视频...")
    
    frames_pattern = str(FRAMES_DIR / "frames" / "frame_%04d.png")
    audio_file = AUDIO_DIR / "merged_audio.wav"
    output_file = PROJECT_ROOT / "output.mp4"
    
    # 加载timeline数据以生成字幕
    timeline_data = load_json(AUDIO_DIR / "timeline.json")
    subtitle_file = generate_subtitle_file(timeline_data)
    
    # FFmpeg命令：添加字幕滤镜
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", frames_pattern,
        "-i", str(audio_file),
        "-vf", f"scale=trunc(iw/2)*2:trunc(ih/2)*2,subtitles={subtitle_file}:force_style='FontName=SimHei,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,Alignment=2,MarginV=30'",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_file)
    ]
    
    print(f"   执行FFmpeg命令...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ FFmpeg错误:")
        print(result.stderr)
        return
    
    print(f"\n✅ 视频合成完成: {output_file}")
    print(f"   时长: {len(load_json(AUDIO_DIR / 'timeline.json')['lines'])} 句台词")


# ======================
# 主流程控制
# ======================
def run_stage(stage_name):
    """运行指定阶段"""
    stage_map = {
        "stage1": lambda: None,  # 剧本已存在
        "stage2": lambda: stage2_generate_all(load_script()),
        "stage3": render_frames,
        "stage4": assemble_video,
    }
    
    if stage_name not in stage_map:
        print(f"❌ 未知阶段: {stage_name}")
        print(f"可用阶段: {', '.join(stage_map.keys())}")
        return
    
    print(f"\n{'='*60}")
    print(f"开始执行: {stage_name}")
    print('='*60)
    
    stage_map[stage_name]()


def main():
    """主函数"""
    import sys
    
    # 映射关系：p1 -> stage1, p2 -> stage2, 以此类推
    stage_mapping = {
        "p1": "stage1",
        "p2": "stage2",
        "p3": "stage3",
        "p4": "stage4",
    }
    
    if len(sys.argv) == 1:
        # 不带参数，执行全部流程
        print("\n" + "="*60)
        print("🎬 开始执行完整流程")
        print("="*60)
        
        run_stage("stage2")  # 生成音频（剧本已存在）
        run_stage("stage3")  # 渲染帧
        run_stage("stage4")  # 合成视频
        
        print("\n" + "="*60)
        print("✅ 完整流程执行完毕！")
        print("="*60)
        return
    
    command = sys.argv[1]
    
    # 支持两种格式：p1/p2/p3/p4 或 stage1/stage2/stage3/stage4
    if command in stage_mapping:
        stage_name = stage_mapping[command]
    elif command.startswith("stage"):
        stage_name = command
    else:
        print(f"❌ 未知命令: {command}")
        print("\n用法:")
        print("  python pipeline.py          # 执行完整流程")
        print("  python pipeline.py p1       # 执行 Stage 1 (剧本)")
        print("  python pipeline.py p2       # 执行 Stage 2 (音频)")
        print("  python pipeline.py p3       # 执行 Stage 3 (帧渲染)")
        print("  python pipeline.py p4       # 执行 Stage 4 (视频合成)")
        print("  python pipeline.py stage1   # 同上（兼容旧格式）")
        return
    
    run_stage(stage_name)


if __name__ == "__main__":
    main()