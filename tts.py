import requests
import json
import sys
import os

# API 地址
API_URL = "http://127.0.0.1:9880/tts"

# 角色配置
ROLE_CONFIG = {
    "A": {
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
        "正常": {
            "ref_audio": "res/ref/ref_b_normal.wav",
            "prompt_text": "生活或许是一地鸡毛，但浪漫让我们学会，用这些鸡毛，扎一个会飞的毽子。"
        }
    }
}

# 语气配置
EMOTION_CONFIG = {
    "正常": {"temperature": 0.8, "emotion_intensity": 0.5, "speed_factor": 1.0},
    "开心": {"temperature": 0.9, "emotion_intensity": 0.9, "speed_factor": 1.1},
    "生气": {"temperature": 0.9, "emotion_intensity": 1.1, "speed_factor": 1.15},
    "悲伤": {"temperature": 0.7, "emotion_intensity": 0.7, "speed_factor": 0.9},
}

# 计数器文件
COUNTER_FILE = "tts_counter.json"

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
    """生成语音，返回是否成功"""
    if role not in ROLE_CONFIG:
        print(f"❌ 错误：角色 '{role}' 不存在")
        return False
    if emotion not in EMOTION_CONFIG:
        print(f"❌ 错误：语气 '{emotion}' 不存在")
        return False
   
    config = ROLE_CONFIG[role][emotion]
    data = {
        "text": text,
        "text_lang": "zh",
        "ref_audio_path": config["ref_audio"],
        "prompt_text": config["prompt_text"],
        "prompt_lang": "zh",
        "top_k": 5,
        "top_p": 1,
        **EMOTION_CONFIG[emotion]
    }
    
    try:
        response = requests.post(API_URL, json=data, timeout=60)
        if response.status_code == 200:
            seq = get_next_seq(role)
            filename = f"audio/{role}_{seq}.wav"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"__FILE__:{filename}")
            return filename
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def main():
    if len(sys.argv) < 4:
        print("用法: python tts.py <文本> <角色> <语气>")
        print("示例: python tts.py '你怎么又迟到了！' A 生气")
        sys.exit(1)
    
    text = sys.argv[1]
    role = sys.argv[2]
    emotion = sys.argv[3]
    
    generate_tts(text, role, emotion)

if __name__ == "__main__":
    main()
