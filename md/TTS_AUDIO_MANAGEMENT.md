# TTS参考音频管理与容错策略

## 🎯 核心原则

**绝对不能生成无声音频！** 系统采用多级降级策略确保每句台词都有声音。

---

## 🔄 降级策略流程

```
请求生成TTS (角色B, 情绪"生气")
    ↓
检查配置中是否有"生气"情绪？
    ├─ 否 → 降级到"正常"情绪
    └─ 是 ↓
检查参考音频文件是否存在？
    ├─ 否 → 尝试降级到"正常"情绪
    │         ├─ "正常"存在 → 使用"正常"音频 ✅
    │         └─ "正常"也不存在 → 报错 ❌
    └─ 是 ↓
调用TTS API生成音频
    ↓
验证生成的音频是否有效？
    ├─ 无效 → 返回错误
    └─ 有效 → 保存文件 ✅
```

---

## ⚠️ 警告日志示例

### **情况1：情绪配置缺失**
```
⚠️  警告：角色 'B' 没有 '悲伤' 情绪配置，使用'正常'代替
```

### **情况2：参考音频文件不存在**
```
⚠️  警告：参考音频文件不存在: /home/simmy/code/sddh/res/ref/ref_b_angry.wav
   🔄 尝试降级到'正常'情绪...
   ✅ 成功降级到'正常'情绪
```

### **情况3：连"正常"音频都不存在**
```
⚠️  警告：参考音频文件不存在: /home/simmy/code/sddh/res/ref/ref_b_normal.wav
   🔄 尝试降级到'正常'情绪...
   ❌ 错误：'正常'情绪的参考音频也不存在: /home/simmy/code/sddh/res/ref/ref_b_normal.wav
   💡 请确保以下文件存在:
      - /home/simmy/code/sddh/res/ref/ref_b_normal.wav
```

---

## 🔍 启动时检查

在 Stage 2 开始时，系统会自动检查所有配置的参考音频文件：

```bash
python pipeline.py stage2

# 输出示例：
# 【Stage 2】生成音频和动作配置...
# 
# 🔍 检查参考音频文件...
# ⚠️  发现 2 个缺失的参考音频文件:
#    ❌ /home/simmy/code/sddh/res/ref/ref_a_happy.wav
#    ❌ /home/simmy/code/sddh/res/ref/ref_b_angry.wav
# 
# ✅ 已找到 4 个存在的文件
# 
# 💡 修复建议:
#    1. 录制或准备缺失的参考音频文件
#    2. 或者修改 pipeline.py 中的 ROLE_CONFIG，让缺失的情绪指向已存在的文件
#    3. 系统会在运行时自动降级到'正常'情绪（如果可用）
```

---

## 📋 必需的最小参考音频清单

为了让系统正常工作，**至少需要**以下文件：

```
res/ref/
├── ref_a_normal.wav    # 角色A的正常语气（必需）
└── ref_b_normal.wav    # 角色B的正常语气（必需）
```

**推荐准备的完整清单：**
```
res/ref/
├── ref_a_normal.wav    # 角色A - 正常
├── ref_a_happy.wav     # 角色A - 开心
├── ref_a_angry.wav     # 角色A - 生气
├── ref_b_normal.wav    # 角色B - 正常
├── ref_b_happy.wav     # 角色B - 开心（可选，可复用normal）
└── ref_b_angry.wav     # 角色B - 生气（可选，可复用normal）
```

---

## 🛠️ 快速修复方案

### **方案1：临时解决（复用现有音频）**

编辑 `pipeline.py` 中的 `ROLE_CONFIG`：

```python
"B": {
    "base_speed_factor": 1.2,
    "正常": {
        "ref_audio": str(RES_DIR / "ref" / "ref_b_normal.wav"),
        "prompt_text": "..."
    },
    "开心": {
        "ref_audio": str(RES_DIR / "ref" / "ref_b_normal.wav"),  # 复用normal
        "prompt_text": "太好了！今天真是美好的一天！"
    },
    "生气": {
        "ref_audio": str(RES_DIR / "ref" / "ref_b_normal.wav"),  # 复用normal
        "prompt_text": "你怎么能这样！我真的很失望！"
    }
}
```

---

### **方案2：长期解决（录制专用音频）**

为每个情绪录制专门的参考音频：

```bash
# 1. 录制音频（用手机录音App或其他工具）
# 2. 用Audacity剪辑成5-10秒干净片段
# 3. 导出为WAV格式（16bit, 16kHz或更高）
# 4. 放到 res/ref/ 目录

# 示例文件名：
res/ref/ref_b_happy.wav   # 角色B用开心的语气说话
res/ref/ref_b_angry.wav   # 角色B用生气的语气说话
```

**录制技巧：**
- 用对应的情绪朗读一段话
- 保持音质清晰，无背景噪音
- 时长5-10秒即可

---

### **方案3：使用占位音频（仅测试用）**

如果暂时没有参考音频，可以创建一个静音或简单音调的WAV文件作为占位：

```python
import soundfile as sf
import numpy as np

# 生成1秒的440Hz正弦波
sr = 16000
duration = 1.0
t = np.linspace(0, duration, int(sr * duration))
audio = 0.5 * np.sin(2 * np.pi * 440 * t)

# 保存为WAV
sf.write('res/ref/ref_b_normal.wav', audio, sr)
print("✅ 已生成占位音频")
```

> ⚠️ **注意**：占位音频生成的TTS效果会很差，仅用于测试流程是否正常。

---

## 🎬 实际运行示例

### **场景：角色B没有"生气"的参考音频**

```bash
python pipeline.py run-all --topic "办公室摸鱼"

# 输出：
# 🔍 检查参考音频文件...
# ⚠️  发现 1 个缺失的参考音频文件:
#    ❌ /home/simmy/code/sddh/res/ref/ref_b_angry.wav
# 
# 【Stage 2】生成音频和动作配置...
# 
#   处理 D002: [B] 你后面是谁？
# ⚠️  警告：参考音频文件不存在: .../ref_b_angry.wav
#    🔄 尝试降级到'正常'情绪...
#    ✅ 成功降级到'正常'情绪
# 
#   ✅ 音频生成成功
```

**结果：**
- ✅ 角色B有声音（使用了"正常"情绪的音色）
- ⚠️ 情感表现可能不够强烈（因为用的是正常语气）
- 💡 建议后续录制专门的"生气"参考音频

---

## ❓ 常见问题

### Q1: 为什么角色B完全没有声音？

**可能原因：**
1. 角色B的所有参考音频文件都不存在
2. TTS服务器未启动
3. 网络连接问题

**排查步骤：**
```bash
# 1. 检查文件是否存在
ls -lh res/ref/ref_b_*.wav

# 2. 检查TTS服务器
curl http://127.0.0.1:9880/

# 3. 查看完整错误日志
python pipeline.py stage2 2>&1 | tee debug.log
```

---

### Q2: 如何让系统忽略缺失的音频继续运行？

系统已经实现了这个功能！只要角色的"正常"情绪参考音频存在，其他情绪缺失时会自动降级。

---

### Q3: 能否批量生成缺失的参考音频？

目前不支持自动生成，需要手动录制。但你可以：
1. 先复用"正常"音频让流程跑通
2. 后续逐步替换为专用音频

---

### Q4: 如何验证生成的音频是否有效？

系统会自动验证：
```python
# 在 generate_tts() 函数中
audio_data, sr = sf.read(str(output_file))
if len(audio_data) == 0:
    print(f"   ⚠️  警告：生成的音频文件为空")
    return None
```

如果发现问题，会立即提示并跳过该句。

---

## 💡 最佳实践

1. **首次使用前检查**
   ```bash
   python pipeline.py stage2  # 会显示所有缺失的文件
   ```

2. **优先保证"正常"情绪可用**
   - 这是最后的降级保障
   - 其他情绪可以后续补充

3. **关注警告日志**
   - 黄色警告表示已降级，但有声音
   - 红色错误表示完全失败，需要修复

4. **逐步优化**
   - 第一阶段：确保流程能跑通（复用normal音频）
   - 第二阶段：为常用情绪录制专用音频
   - 第三阶段：为所有情绪录制专用音频

---

## 📊 总结

| 情况 | 行为 | 结果 |
|------|------|------|
| 情绪配置缺失 | 降级到"正常" | ✅ 有声音 |
| 参考音频文件缺失 | 降级到"正常" | ✅ 有声音 |
| "正常"音频也缺失 | 报错并跳过 | ❌ 无声音 |
| TTS API失败 | 记录错误 | ❌ 无声音 |

**核心理念：宁可情感平淡，也不能无声！** 🎤✨
