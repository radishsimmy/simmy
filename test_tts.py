#!/usr/bin/env python3
"""
TTS API 直接测试脚本
用于快速测试 GPT-SoVITS TTS API 是否正常工作
"""

import requests
import json
import re
from pathlib import Path
import soundfile as sf
import numpy as np

# TTS API 配置
API_URL = "http://127.0.0.1:9880/tts"

# 参考音频配置（根据您的项目配置）
REF_AUDIO_PATH = "/home/simmy/code/sddh/res/ref/ref_a_normal.wav"

# ⚠️ 重要：prompt_text 必须是参考音频中实际说的内容！
# 如果不知道，请使用 ASR 工具识别参考音频的内容
PROMPT_TEXT = ""  # 留空表示未知，需要在下面配置
PROMPT_LANG = "zh"


def diagnose_audio(audio_path):
    """诊断音频文件的基本信息"""
    print(f"\n{'='*60}")
    print(f"🔍 参考音频诊断: {audio_path}")
    print(f"{'='*60}")
    
    if not Path(audio_path).exists():
        print(f"❌ 错误：文件不存在")
        return False
    
    try:
        audio_data, sr = sf.read(audio_path)
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
        
        duration = len(audio_data) / sr
        rms = float(np.sqrt(np.mean(audio_data**2)))
        peak = float(np.max(np.abs(audio_data)))
        
        print(f"   采样率: {sr} Hz")
        print(f"   时长: {duration:.2f} 秒")
        print(f"   RMS 音量: {rms:.6f}")
        print(f"   峰值音量: {peak:.6f}")
        
        if rms < 0.01:
            print(f"   ❌ 音量过低，可能导致生成质量差")
            return False
        elif rms < 0.05:
            print(f"   ⚠️  音量偏低")
        else:
            print(f"   ✅ 音量正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误：{e}")
        return False


def clean_text_for_tts(text: str, remove_english=False) -> str:
    """
    清理文本中的标点符号，符合 TTS 文本预处理规范
    
    根据项目规范：发送给 TTS API 的文本必须移除所有标点符号（包括问号、感叹号、省略号等），
    防止 TTS 自动按标点切分句子导致音频截断或只生成前半部分。
    
    参数:
        text: 原始文本
        remove_english: 是否移除英文单词（默认False，设为True可避免英文分词问题）
    返回:
        清理后的文本（完全移除所有标点符号）
    """
    # 移除所有标点符号（包括中文和英文标点）
    # 保留字母、数字、汉字和空格
    cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
    
    # 如果需要移除英文，只保留中文和数字
    if remove_english:
        # 移除所有英文字母，只保留中文、数字和空格
        cleaned = re.sub(r'[a-zA-Z]+', '', cleaned)
        # 清理多余空格
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    else:
        # 移除多余的空格
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def test_tts(text, output_file="test_output.wav", clean_punctuation=True, remove_english=False, prompt_text=None, prompt_lang="zh"):
    """
    直接调用 TTS API 生成音频
    
    参数:
        text: 要合成的文本
        output_file: 输出文件路径
        clean_punctuation: 是否清理标点符号（默认True，符合项目规范）
        remove_english: 是否移除英文单词（避免英文分词问题）
        prompt_text: 参考音频对应的文本（必须与参考音频内容匹配）
        prompt_lang: 提示文本的语言
    """
    print(f"\n{'='*60}")
    print(f"🎤 TTS API 测试")
    print(f"{'='*60}")
    
    # 诊断参考音频
    diagnose_audio(REF_AUDIO_PATH)
    
    # 使用传入的 prompt_text 或全局配置
    if prompt_text is None:
        prompt_text = PROMPT_TEXT
    
    if not prompt_text:
        print(f"\n⚠️  警告：未设置 prompt_text！")
        print(f"   prompt_text 必须是参考音频中实际说的内容")
        print(f"   否则生成的语音会混乱或不准确")
        print(f"   建议使用 ASR 工具识别参考音频的内容")
        return False
    
    # 根据配置决定是否清理标点
    original_text = text
    if clean_punctuation:
        text = clean_text_for_tts(text, remove_english=remove_english)
        print(f"\n原始文本: '{original_text}'")
        if remove_english:
            print(f"清理后（已过滤英文）: '{text}'")
        else:
            print(f"清理后: '{text}'")
    else:
        print(f"文本: '{text}'")
        print("⚠️  警告：未清理标点符号，可能导致生成异常")
    
    print(f"参考音频: {REF_AUDIO_PATH}")
    print(f"提示文本: '{prompt_text}'")
    print(f"提示语言: {prompt_lang}")
    print(f"输出文件: {output_file}")
    print(f"{'='*60}\n")
    
    # 检查参考音频是否存在
    if not Path(REF_AUDIO_PATH).exists():
        print(f"❌ 错误：参考音频文件不存在: {REF_AUDIO_PATH}")
        return False
    
    # 构建请求数据 - 优化参数以避免提前停止
    data = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": REF_AUDIO_PATH,
        "prompt_text": prompt_text,
        "prompt_lang": prompt_lang,
        # 提高温度和采样参数，让模型更自由地生成
        "top_k": 20,           # 增加 top_k，提供更多选择
        "top_p": 0.9,          # 提高 top_p，允许更多多样性
        "temperature": 0.9,    # 提高温度，减少过度保守
        "speed_factor": 1.0,
        "seed": 42,
        "split_bucket": False,
        "text_split_method": "cut0",  # 不使用切分，避免再次处理标点
        "repetition_penalty": 1.2,    # 降低重复惩罚，避免过早停止
    }
    
    if remove_english:
        print("💡 提示：已启用英文过滤模式，所有英文单词将被移除")
    
    print("📤 发送请求到 TTS API...")
    try:
        response = requests.post(API_URL, json=data, timeout=60)
        
        if response.status_code == 200:
            file_size = len(response.content)
            print(f"✅ 收到响应，文件大小: {file_size} bytes")
            
            if file_size == 0:
                print("❌ 错误：响应内容为空")
                return False
            
            # 保存音频文件
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            print(f"✅ 音频已保存到: {output_file}")
            
            # 验证音频文件
            try:
                audio_data, sr = sf.read(output_file)
                if len(audio_data.shape) > 1:
                    audio_data = audio_data.mean(axis=1)
                
                duration = len(audio_data) / sr
                rms = float(np.sqrt(np.mean(audio_data**2))) if len(audio_data) > 0 else 0
                
                print(f"\n📊 生成音频信息:")
                print(f"   采样率: {sr} Hz")
                print(f"   时长: {duration:.2f} 秒")
                print(f"   RMS音量: {rms:.6f}")
                print(f"   样本数: {len(audio_data)}")
                
                if duration <= 0:
                    print("❌ 错误：音频时长为0")
                    return False
                
                if rms < 0.005:
                    print("⚠️  警告：音量过低，可能是静音或低质量生成")
                    print("💡 建议：")
                    print("   1. 检查参考音频是否正常（见上方诊断信息）")
                    print("   2. 尝试使用不同的温度值 (0.8-1.0)")
                    print("   3. 确保 prompt_text 与参考音频内容匹配")
                    print("   4. 检查后端日志是否有 'T2S Decoding EOS' 提前停止")
                    return False
                else:
                    print("✅ 音频质量正常")
                
                print("\n✅ TTS API 测试成功！")
                return True
                
            except Exception as e:
                print(f"⚠️  警告：无法读取音频文件进行验证: {e}")
                print("但文件已保存，您可以手动播放检查")
                return True
        
        else:
            print(f"❌ HTTP 错误: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            return False
    
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接错误：无法连接到 TTS API ({API_URL})")
        print("请确保 TTS 服务已启动")
        print("启动命令: python api_v2.py -c GPT_SoVITS/configs/tts_infer.yaml")
        return False
    
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    
    # 解析命令行参数
    prompt_text_arg = None
    test_text = None
    remove_english_flag = False
    
    if "--prompt" in sys.argv:
        idx = sys.argv.index("--prompt")
        if idx + 1 < len(sys.argv):
            prompt_text_arg = sys.argv[idx + 1]
            # 剩余的参数作为测试文本
            remaining = sys.argv[idx + 2:]
            if remaining:
                test_text = " ".join(remaining)
    
    # 检查是否启用英文过滤
    if "--no-english" in sys.argv or "-ne" in sys.argv:
        remove_english_flag = True
        # 移除这个标志，不影响其他参数
        sys.argv = [arg for arg in sys.argv if arg not in ["--no-english", "-ne"]]
    
    if not test_text and len(sys.argv) > 1 and "--prompt" not in sys.argv:
        # 如果没有 --prompt 参数，直接使用所有参数作为测试文本
        test_text = " ".join(sys.argv[1:])
    
    # 确定最终使用的 prompt_text
    final_prompt_text = prompt_text_arg if prompt_text_arg else PROMPT_TEXT
    
    print("="*60)
    print("⚠️  重要提示：")
    print("="*60)
    print("TTS 生成质量取决于 prompt_text 的准确性！")
    print("")
    print("当前配置：")
    print(f"  参考音频: {REF_AUDIO_PATH}")
    print(f"  提示文本: '{final_prompt_text}'")
    print("")
    
    if not final_prompt_text:
        print("❌ 错误：未设置 prompt_text！")
        print("")
        print("解决方案：")
        print("  1. 如果您知道参考音频说的内容，请修改脚本中的 PROMPT_TEXT")
        print("  2. 或者使用 ASR 工具识别参考音频的内容")
        print("  3. 示例：python test_tts.py --prompt '参考音频实际说的内容' '要合成的文本'")
        sys.exit(1)
    
    print("="*60)
    print()
    
    if not test_text:
        # 默认测试用例
        test_cases = [
            ("等等，让我看看...你这请求参数传对了吗？", "test_d004.wav"),
            ("会不会是你网络有问题？换个WiFi试试？", "test_d010.wav"),
            ("真的假的？现在可是三伏天啊！", "test_simple.wav"),
            ("你好，这是一个测试。", "test_basic.wav"),
        ]
        
        # 执行测试
        success_count = 0
        for text, output_file in test_cases:
            if test_tts(text, output_file, clean_punctuation=True, 
                       remove_english=remove_english_flag,
                       prompt_text=final_prompt_text,
                       prompt_lang=PROMPT_LANG):
                success_count += 1
            print()
        
        print(f"\n{'='*60}")
        print(f"测试结果: {success_count}/{len(test_cases)} 成功")
        print(f"{'='*60}")
    else:
        # 单个测试
        if test_tts(test_text, "test_custom.wav", clean_punctuation=True,
                   remove_english=remove_english_flag,
                   prompt_text=final_prompt_text,
                   prompt_lang=PROMPT_LANG):
            print("\n✅ 测试成功！")
        else:
            print("\n❌ 测试失败！")
            sys.exit(1)
