#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成沙雕动画动作系统所需的完整素材
包括：角色基础图、五官、表情覆盖层、特效等
"""

import numpy as np
import cv2
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
RES_DIR = PROJECT_ROOT / "res"


def create_character_base(output_path, size=(200, 300), color_bgr=(255, 200, 150)):
    """生成角色基础身体图 - 简单矩形，方便计算五官位置"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    # 绘制简单矩形身体（包含头部区域）
    margin = 20  # 边距
    rect_x1 = margin
    rect_y1 = margin
    rect_x2 = size[0] - margin
    rect_y2 = size[1] - margin
    
    # 填充矩形
    cv2.rectangle(img, (rect_x1, rect_y1), (rect_x2, rect_y2), 
                  color_bgr + (255,), -1)
    
    # 黑色描边
    cv2.rectangle(img, (rect_x1, rect_y1), (rect_x2, rect_y2), 
                  (0, 0, 0, 255), 3)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_character_base_side_left(output_path, size=(200, 300), color_bgr=(255, 200, 150)):
    """生成左侧脸角色基础身体图 - 带透视感的梯形"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    # 绘制梯形（模拟侧脸透视效果）
    margin_top = 20
    margin_bottom = 20
    margin_left = 30  # 左边距更大，模拟远离视角
    margin_right = 10  # 右边距更小，模拟靠近视角
    
    # 定义梯形的四个顶点（左上、右上、右下、左下）
    pts = np.array([
        [margin_left, margin_top],      # 左上
        [size[0] - margin_right, margin_top],   # 右上
        [size[0] - margin_right, size[1] - margin_bottom],  # 右下
        [margin_left + 20, size[1] - margin_bottom]  # 左下（稍微向右收缩）
    ], dtype=np.int32)
    
    # 填充梯形
    cv2.fillPoly(img, [pts], color_bgr + (255,))
    
    # 黑色描边
    cv2.polylines(img, [pts], isClosed=True, color=(0, 0, 0, 255), thickness=3)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]}, 侧脸梯形)")


def create_character_base_side_right(output_path, size=(200, 300), color_bgr=(255, 200, 150)):
    """生成右侧脸角色基础身体图 - 带透视感的梯形"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    # 绘制梯形（模拟侧脸透视效果，与左侧脸镜像对称）
    margin_top = 20
    margin_bottom = 20
    margin_left = 10  # 左边距更小，模拟靠近视角
    margin_right = 30  # 右边距更大，模拟远离视角
    
    # 定义梯形的四个顶点（左上、右上、右下、左下）
    pts = np.array([
        [margin_left, margin_top],      # 左上
        [size[0] - margin_right, margin_top],   # 右上
        [size[0] - margin_right - 20, size[1] - margin_bottom],  # 右下（稍微向左收缩）
        [margin_left, size[1] - margin_bottom]  # 左下
    ], dtype=np.int32)
    
    # 填充梯形
    cv2.fillPoly(img, [pts], color_bgr + (255,))
    
    # 黑色描边
    cv2.polylines(img, [pts], isClosed=True, color=(0, 0, 0, 255), thickness=3)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]}, 侧脸梯形)")


def create_normal_eyes(output_path, size=(60, 60)):
    """生成正常睁眼 - 黑色圆形带瞳孔（缩小尺寸）"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    center = (size[0] // 2, size[1] // 2)
    radius = min(size) // 2 - 6
    
    # 眼白
    cv2.circle(img, center, radius, (255, 255, 255, 255), -1)
    cv2.circle(img, center, radius, (0, 0, 0, 255), 2)
    
    # 瞳孔
    pupil_radius = radius // 3
    cv2.circle(img, center, pupil_radius, (0, 0, 0, 255), -1)
    
    # 高光
    highlight_pos = (center[0] + radius // 3, center[1] - radius // 3)
    cv2.circle(img, highlight_pos, pupil_radius // 2, (255, 255, 255, 255), -1)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_single_eye_open(output_path, size=(60, 60), direction="left"):
    """生成单眼睁开（侧脸用）"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    center = (size[0] // 2, size[1] // 2)
    radius = min(size) // 2 - 6
    
    # 眼白
    cv2.circle(img, center, radius, (255, 255, 255, 255), -1)
    cv2.circle(img, center, radius, (0, 0, 0, 255), 2)
    
    # 瞳孔（稍微偏向一侧模拟侧视）
    pupil_offset = 5 if direction == "left" else -5
    pupil_center = (center[0] + pupil_offset, center[1])
    pupil_radius = radius // 3
    cv2.circle(img, pupil_center, pupil_radius, (0, 0, 0, 255), -1)
    
    # 高光
    highlight_pos = (pupil_center[0] + radius // 3, pupil_center[1] - radius // 3)
    cv2.circle(img, highlight_pos, pupil_radius // 2, (255, 255, 255, 255), -1)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]}, {direction})")


def create_close_eyes(output_path, size=(60, 15)):
    """生成闭眼 - 黑色弧线（缩小尺寸）"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    center = (size[0] // 2, size[1] // 2)
    
    # 绘制闭合的眼线（向下弯曲的弧线）
    start_angle = 200
    end_angle = 340
    axes = (size[0] // 2 - 5, size[1] // 2)
    cv2.ellipse(img, center, axes, 0, start_angle, end_angle, (0, 0, 0, 255), 3)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_single_eye_close(output_path, size=(60, 15), direction="left"):
    """生成单眼闭合（侧脸用）"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    center = (size[0] // 2, size[1] // 2)
    
    # 绘制闭合的眼线（向下弯曲的弧线）
    start_angle = 200
    end_angle = 340
    axes = (size[0] // 2 - 5, size[1] // 2)
    cv2.ellipse(img, center, axes, 0, start_angle, end_angle, (0, 0, 0, 255), 3)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]}, {direction})")


def create_normal_mouth_open(output_path, size=(50, 35)):
    """生成正常张嘴 - 深红色椭圆（缩小尺寸）"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    center = (size[0] // 2, size[1] // 2)
    axes = (size[0] // 2 - 4, size[1] // 2 - 4)
    
    cv2.ellipse(img, center, axes, 0, 0, 360, (0, 0, 0, 255), 2)
    inner_axes = (axes[0] - 3, axes[1] - 3)
    cv2.ellipse(img, center, inner_axes, 0, 0, 360, (0, 0, 139, 255), -1)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_single_mouth_open(output_path, size=(50, 35), direction="left"):
    """生成单边张嘴（侧脸用）- 半椭圆"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    center = (size[0] // 2, size[1] // 2)
    axes = (size[0] // 2 - 4, size[1] // 2 - 4)
    
    # 绘制半椭圆（只显示一半）
    cv2.ellipse(img, center, axes, 0, 0, 180 if direction == "left" else 180, (0, 0, 0, 255), 2)
    inner_axes = (axes[0] - 3, axes[1] - 3)
    cv2.ellipse(img, center, inner_axes, 0, 0, 180 if direction == "left" else 180, (0, 0, 139, 255), -1)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]}, {direction})")


def create_normal_mouth_close(output_path, size=(50, 8)):
    """生成正常闭嘴 - 黑色细线（缩小尺寸）"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    center = (size[0] // 2, size[1] // 2)
    pt1 = (8, center[1])
    pt2 = (size[0] - 8, center[1])
    cv2.line(img, pt1, pt2, (0, 0, 0, 255), 3)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_single_mouth_close(output_path, size=(50, 8), direction="left"):
    """生成单边闭嘴（侧脸用）"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    center = (size[0] // 2, size[1] // 2)
    pt1 = (8, center[1])
    pt2 = (size[0] - 8, center[1])
    cv2.line(img, pt1, pt2, (0, 0, 0, 255), 3)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]}, {direction})")


def create_surprised_eyes(output_path, size=(70, 70)):
    """生成惊讶时的睁大眼睛 - 红色边框大圆（缩小尺寸）"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    center = (size[0] // 2, size[1] // 2)
    radius = min(size) // 2 - 5
    
    # 眼白背景
    cv2.circle(img, center, radius, (255, 255, 255, 255), -1)
    # 红色边框表示惊讶
    cv2.circle(img, center, radius, (0, 0, 255, 255), 4)
    
    # 瞳孔（更大）
    pupil_radius = radius // 3
    cv2.circle(img, center, pupil_radius, (0, 0, 0, 255), -1)
    
    # 高光
    highlight_offset = (radius // 3, -radius // 3)
    highlight_pos = (center[0] + highlight_offset[0], center[1] + highlight_offset[1])
    cv2.circle(img, highlight_pos, pupil_radius // 3, (255, 255, 255, 255), -1)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_narrow_eyes(output_path, size=(60, 18)):
    """生成生气时的眯眼 - 黑色细长椭圆（缩小尺寸）"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    center = (size[0] // 2, size[1] // 2)
    axes = (size[0] // 2 - 5, size[1] // 2 - 3)
    
    cv2.ellipse(img, center, axes, 0, 0, 360, (0, 0, 0, 255), -1)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_extra_wide_mouth(output_path, size=(80, 65)):
    """生成大喊时的超大张嘴 - 深蓝色大椭圆（缩小尺寸）"""
    img = np.ones((size[1], size[0], 4), dtype=np.uint8) * 255
    
    center = (size[0] // 2, size[1] // 2)
    axes = (size[0] // 2 - 5, size[1] // 2 - 5)
    
    # 外轮廓
    cv2.ellipse(img, center, axes, 0, 0, 360, (0, 0, 0, 255), 3)
    
    # 内部填充深色（口腔）
    inner_axes = (axes[0] - 5, axes[1] - 5)
    cv2.ellipse(img, center, inner_axes, 0, 0, 360, (0, 0, 139, 255), -1)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_smile_mouth(output_path, size=(60, 30)):
    """生成微笑嘴型 - 绿色弧线（缩小尺寸）"""
    img = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    
    center = (size[0] // 2, size[1] // 3)
    radius = min(size) // 2 - 5
    
    start_angle = 30
    end_angle = 150
    cv2.ellipse(img, center, (radius, radius), 0, start_angle, end_angle, 
                (0, 255, 0, 255), 4)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_question_marks_effect(output_path, size=(100, 100)):
    """生成问号特效 - 黑色问号"""
    img = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    
    # 绘制大问号
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, "?", (25, 75), font, 2, (255, 255, 255, 255), 4, cv2.LINE_AA)
    cv2.putText(img, "?", (25, 75), font, 2, (0, 0, 0, 255), 2, cv2.LINE_AA)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_exclamation_marks_effect(output_path, size=(100, 100)):
    """生成感叹号特效 - 红色感叹号"""
    img = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    
    # 绘制大感叹号
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, "!", (35, 75), font, 2, (255, 255, 255, 255), 4, cv2.LINE_AA)
    cv2.putText(img, "!", (35, 75), font, 2, (0, 0, 255, 255), 2, cv2.LINE_AA)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_shock_lines_effect(output_path, size=(150, 150)):
    """生成震动线特效 - 放射状线条"""
    img = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    
    center = (size[0] // 2, size[1] // 2)
    
    # 绘制放射状线条
    num_lines = 12
    for i in range(num_lines):
        angle = i * (360 / num_lines)
        rad = np.radians(angle)
        
        x1 = int(center[0] + 30 * np.cos(rad))
        y1 = int(center[1] + 30 * np.sin(rad))
        x2 = int(center[0] + 60 * np.cos(rad))
        y2 = int(center[1] + 60 * np.sin(rad))
        
        cv2.line(img, (x1, y1), (x2, y2), (255, 255, 255, 200), 3)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_dots_effect(output_path, size=(100, 50)):
    """生成省略号特效 - 灰色三个点"""
    img = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    
    centers = [(25, size[1]//2), (50, size[1]//2), (75, size[1]//2)]
    for center in centers:
        cv2.circle(img, center, 8, (128, 128, 128, 200), -1)
    
    cv2.imwrite(str(output_path), img)
    print(f"✅ {output_path.name} ({size[0]}x{size[1]})")


def create_comedy_boing_sound(output_path, duration=0.3, sample_rate=44100):
    """生成喜剧弹跳音效（类似弹簧声）"""
    import scipy.io.wavfile as wavfile
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # 频率从高到低快速下降（模拟弹簧声）
    frequency = 800 * np.exp(-t * 15) + 200
    
    # 生成调频信号
    phase = 2 * np.pi * np.cumsum(frequency) / sample_rate
    audio = 0.3 * np.sin(phase)
    
    # 添加包络（淡入淡出）
    envelope = np.ones_like(t)
    fade_in_len = int(sample_rate * 0.02)
    fade_out_len = int(sample_rate * 0.05)
    
    if fade_in_len < len(envelope):
        envelope[:fade_in_len] = np.linspace(0, 1, fade_in_len)
    if fade_out_len < len(envelope):
        envelope[-fade_out_len:] = np.linspace(1, 0, fade_out_len)
    
    audio = audio * envelope
    
    # 转换为16位整数
    audio_int16 = np.int16(audio * 32767)
    
    wavfile.write(str(output_path), sample_rate, audio_int16)
    print(f"✅ {output_path.name} (时长:{duration}s, 采样率:{sample_rate}Hz)")


def create_whoosh_sound(output_path, duration=0.4, sample_rate=44100):
    """生成呼啸声/风声特效"""
    import scipy.io.wavfile as wavfile
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # 白噪声
    noise = np.random.normal(0, 1, len(t))
    
    # 带通滤波效果（模拟风声）
    from scipy.signal import butter, filtfilt
    b, a = butter(4, [200/(sample_rate/2), 2000/(sample_rate/2)], btype='band')
    filtered_noise = filtfilt(b, a, noise)
    
    # 包络：快速上升，缓慢下降
    envelope = np.zeros_like(t)
    attack_len = int(sample_rate * 0.05)
    release_len = int(sample_rate * 0.25)
    
    if attack_len < len(envelope):
        envelope[:attack_len] = np.linspace(0, 1, attack_len)
    if release_len < len(envelope):
        envelope[-release_len:] = np.linspace(1, 0, release_len)
    else:
        envelope[attack_len:] = np.linspace(1, 0, len(envelope) - attack_len)
    
    audio = 0.25 * filtered_noise * envelope
    
    # 转换为16位整数
    audio_int16 = np.int16(np.clip(audio, -1, 1) * 32767)
    
    wavfile.write(str(output_path), sample_rate, audio_int16)
    print(f"✅ {output_path.name} (时长:{duration}s, 采样率:{sample_rate}Hz)")


def create_pop_sound(output_path, duration=0.15, sample_rate=44100):
    """生成 popping 音效（类似气泡破裂声）"""
    import scipy.io.wavfile as wavfile
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # 高频短促正弦波
    frequency = 1200
    audio = 0.4 * np.sin(2 * np.pi * frequency * t)
    
    # 指数衰减包络
    decay = np.exp(-t * 40)
    audio = audio * decay
    
    # 转换为16位整数
    audio_int16 = np.int16(np.clip(audio, -1, 1) * 32767)
    
    wavfile.write(str(output_path), sample_rate, audio_int16)
    print(f"✅ {output_path.name} (时长:{duration}s, 采样率:{sample_rate}Hz)")


def create_role_config(output_path, face_direction, eye_position, mouth_position):
    """创建角色配置文件"""
    import json
    
    config = {
        "face_direction": face_direction,
        "features": {
            "eye": {
                "visible_count": 1 if "side" in face_direction else 2,
                "position": eye_position
            },
            "mouth": {
                "position": mouth_position
            }
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {output_path.name} (脸型:{face_direction})")


def main():
    print("=" * 60)
    print("🎨 生成沙雕动画完整素材集（支持正脸+侧脸）")
    print("=" * 60)
    
    # ==================== 为角色A和B生成正脸素材 ====================
    for role in ['A', 'B']:
        print(f"\n{'='*60}")
        print(f"角色 {role} (正脸):")
        print('='*60)
        
        char_dir = RES_DIR / "characters" / role
        
        # 基础身体图（简单矩形）
        create_character_base(char_dir / "base.png", size=(200, 300))
        
        # 眼睛素材
        eye_dir = char_dir / "eye"
        eye_dir.mkdir(parents=True, exist_ok=True)
        create_normal_eyes(eye_dir / "open.png")
        create_close_eyes(eye_dir / "close.png")
        create_surprised_eyes(eye_dir / "surprised.png")
        create_narrow_eyes(eye_dir / "narrow.png")
        
        # 嘴巴素材
        mouth_dir = char_dir / "mouth"
        mouth_dir.mkdir(parents=True, exist_ok=True)
        create_normal_mouth_open(mouth_dir / "open.png")
        create_normal_mouth_close(mouth_dir / "close.png")
        create_extra_wide_mouth(mouth_dir / "extra_wide.png")
        create_smile_mouth(mouth_dir / "smile.png")
        
        # 创建正脸配置文件
        create_role_config(
            char_dir / "config.json",
            face_direction="front",
            eye_position={"x_ratio": 0.5, "y_ratio": 0.35},
            mouth_position={"x_ratio": 0.5, "y_ratio": 0.55}
        )
    
    # ==================== 为角色A生成左侧脸素材 ====================
    print(f"\n{'='*60}")
    print(f"角色 A - 视角素材:")
    print('='*60)
    
    # 创建视角目录：res/characters/A/angles/side_left/
    angles_dir_A = RES_DIR / "characters" / "A" / "angles"
    
    # 左侧脸素材
    side_left_dir = angles_dir_A / "side_left"
    side_left_dir.mkdir(parents=True, exist_ok=True)
    
    create_character_base_side_left(side_left_dir / "base.png", size=(200, 300))
    
    eye_dir = side_left_dir / "eye"
    eye_dir.mkdir(parents=True, exist_ok=True)
    create_single_eye_open(eye_dir / "open.png", direction="left")
    create_single_eye_close(eye_dir / "close.png", direction="left")
    
    mouth_dir = side_left_dir / "mouth"
    mouth_dir.mkdir(parents=True, exist_ok=True)
    create_single_mouth_open(mouth_dir / "open.png", direction="left")
    create_single_mouth_close(mouth_dir / "close.png", direction="left")
    
    # 创建左侧脸配置文件
    create_role_config(
        side_left_dir / "config.json",
        face_direction="side_left",
        eye_position={"x_ratio": 0.65, "y_ratio": 0.35},
        mouth_position={"x_ratio": 0.70, "y_ratio": 0.55}
    )
    
    print(f"✅ A/side_left 素材生成完成")
    
    # ==================== 为角色B生成右侧脸素材 ====================
    # 创建视角目录：res/characters/B/angles/side_right/
    angles_dir_B = RES_DIR / "characters" / "B" / "angles"
    
    # 右侧脸素材
    side_right_dir = angles_dir_B / "side_right"
    side_right_dir.mkdir(parents=True, exist_ok=True)
    
    create_character_base_side_right(side_right_dir / "base.png", size=(200, 300))
    
    eye_dir = side_right_dir / "eye"
    eye_dir.mkdir(parents=True, exist_ok=True)
    create_single_eye_open(eye_dir / "open.png", direction="right")
    create_single_eye_close(eye_dir / "close.png", direction="right")
    
    mouth_dir = side_right_dir / "mouth"
    mouth_dir.mkdir(parents=True, exist_ok=True)
    create_single_mouth_open(mouth_dir / "open.png", direction="right")
    create_single_mouth_close(mouth_dir / "close.png", direction="right")
    
    # 创建右侧脸配置文件
    create_role_config(
        side_right_dir / "config.json",
        face_direction="side_right",
        eye_position={"x_ratio": 0.35, "y_ratio": 0.35},
        mouth_position={"x_ratio": 0.30, "y_ratio": 0.55}
    )
    
    print(f"✅ B/side_right 素材生成完成")

    # ==================== 特效素材 ====================
    print(f"\n{'='*60}")
    print("视觉特效:")
    print('='*60)
    effects_dir = RES_DIR / "effects"
    effects_dir.mkdir(parents=True, exist_ok=True)
    create_question_marks_effect(effects_dir / "question_marks.png")
    create_exclamation_marks_effect(effects_dir / "exclamation_marks.png")
    create_shock_lines_effect(effects_dir / "shock_lines.png")
    create_dots_effect(effects_dir / "dots.png")
    
    # ==================== 音效素材 ====================
    print(f"\n{'='*60}")
    print("音效素材:")
    print('='*60)
    sfx_dir = RES_DIR / "sfx"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    create_comedy_boing_sound(sfx_dir / "boing.wav")
    create_whoosh_sound(sfx_dir / "whoosh.wav")
    create_pop_sound(sfx_dir / "pop.wav")
    
    print("\n" + "=" * 60)
    print("✅ 所有素材生成完成！")
    print("=" * 60)
    print(f"\n保存位置: {RES_DIR.absolute()}")
    
    # 统计生成的文件
    total_files = 0
    
    # 统计所有角色的素材（包括正脸和视角素材）
    for role in ['A', 'B']:
        char_dir = RES_DIR / "characters" / role
        if char_dir.exists():
            files = list(char_dir.rglob("*.png"))
            total_files += len(files)
            
            # 检查是否有angles子目录
            angles_dir = char_dir / "angles"
            if angles_dir.exists():
                angle_subdirs = [d.name for d in angles_dir.iterdir() if d.is_dir()]
                print(f"  角色{role}: {len(files)} 个图片文件 (包含视角: {', '.join(angle_subdirs)})")
            else:
                print(f"  角色{role}(正脸): {len(files)} 个图片文件")
    
    effect_files = list(effects_dir.glob("*.png"))
    total_files += len(effect_files)
    print(f"  视觉特效: {len(effect_files)} 个图片文件")
    
    sfx_files = list(sfx_dir.glob("*.wav"))
    total_files += len(sfx_files)
    print(f"  音效: {len(sfx_files)} 个音频文件")
    print(f"\n总计: {total_files} 个素材文件")


if __name__ == "__main__":
    main()
