# 常见问题与解决方案

## ❌ 错误：KeyError: '生气'

### 问题描述
运行 `python pipeline.py run-all` 时出现以下错误：
```
KeyError: '生气'
```

### 原因
角色配置（`ROLE_CONFIG`）中，某个角色（如角色B）没有定义该情绪（如"生气"）的参考音频和提示文本。

### 解决方案

#### 方案1：为角色添加情绪配置（推荐）

编辑 `pipeline.py` 中的 `ROLE_CONFIG`，为角色添加缺失的情绪配置：

```python
"B": {
    "base_speed_factor": 1.2,
    "正常": {
        "ref_audio": str(RES_DIR / "ref" / "ref_b_normal.wav"),
        "prompt_text": "..."
    },
    "开心": {  # 添加这个
        "ref_audio": str(RES_DIR / "ref" / "ref_b_happy.wav"),
        "prompt_text": "太好了！今天真是美好的一天！"
    },
    "生气": {  # 添加这个
        "ref_audio": str(RES_DIR / "ref" / "ref_b_angry.wav"),
        "prompt_text": "你怎么能这样！我真的很失望！"
    }
}
```

**如果没有对应的参考音频**，可以暂时复用已有的音频：
```python
"生气": {
    "ref_audio": str(RES_DIR / "ref" / "ref_b_normal.wav"),  # 暂时使用normal
    "prompt_text": "你怎么能这样！我真的很失望！"
}
```

---

#### 方案2：修改剧本中的情绪

编辑 `stages/01_script/script.json`，将未配置的情绪改为已配置的情绪：

```json
{
  "id": "D002",
  "role": "B",
  "text": "你后面是谁？",
  "emotion": "正常"  // 改为"正常"或其他已配置的情绪
}
```

---

### 已修复

✅ 代码已更新，添加了智能回退机制：
- 如果角色没有指定情绪，会自动使用"正常"情绪
- 会显示警告信息，但不会中断流程

✅ 角色B已添加"开心"和"生气"情绪配置（暂时复用normal音频）

---

## ❌ 错误：TTS服务器连接失败

### 问题描述
```
❌ 错误：无法连接到TTS服务器 (http://127.0.0.1:9880/tts)
```

### 解决方案

1. **确认TTS服务器已启动**
   ```bash
   # 在新终端运行
   python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
   ```

2. **检查服务器是否正常运行**
   ```bash
   curl http://127.0.0.1:9880/
   ```

3. **确认端口未被占用**
   ```bash
   lsof -i :9880
   ```

---

## ❌ 错误：找不到参考音频文件

### 问题描述
```
❌ TTS生成失败: [Errno 2] No such file or directory: 'res/ref/ref_a_normal.wav'
```

### 解决方案

1. **准备参考音频**
   - 录制自己的声音或使用现有音频
   - 格式：WAV，16bit，16kHz或更高
   - 时长：5-10秒

2. **放置到正确位置**
   ```
   res/ref/
   ├── ref_a_normal.wav
   ├── ref_a_happy.wav
   ├── ref_a_angry.wav
   └── ref_b_normal.wav
   ```

3. **临时测试**
   如果暂时没有参考音频，可以先运行占位素材生成器：
   ```bash
   python generate_placeholders.py
   ```
   但这只会生成图片占位符，音频仍需手动准备。

---

## ❌ 错误：FFmpeg未找到

### 问题描述
```
❌ 视频合成失败
ffmpeg: command not found
```

### 解决方案

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
1. 从 https://ffmpeg.org/download.html 下载
2. 解压并添加到系统PATH

---

## ⚠️ 警告：角色口型不同步

### 问题描述
角色嘴巴动作与音频不匹配，或者完全不张嘴。

### 解决方案

编辑 `pipeline.py` 中的 `MOUTH_THRESHOLD` 参数：

```python
# 在 render_frames() 函数中
MOUTH_THRESHOLD = 0.15  # 默认值
```

- **如果角色音量偏低导致不张嘴**：降低阈值（如 0.10）
- **如果频繁误触发**：提高阈值（如 0.25）

---

## ⚠️ 警告：角色五官位置不对

### 问题描述
角色的眼睛或嘴巴位置偏移，不在正确的位置。

### 解决方案

编辑 `pipeline.py` 中 `draw_character()` 函数的参数：

```python
# 垂直位置（Y坐标）
eye_y = int(bh * 0.58)     # 眼睛位置（0.0-1.0的比例）
mouth_y = int(bh * 0.75)   # 嘴巴位置（0.0-1.0的比例）

# 水平位置（X坐标偏移）
eye_offset_x = -12         # 眼睛左右偏移（负数向左，正数向右）
mouth_offset_x = -20       # 嘴巴左右偏移

# 眼睛间距
eye_dx = int(bw * 0.15)    # 眼睛距离中心的距离
```

调整这些值直到五官位置正确。

---

## 💡 最佳实践

### 1. 先用小样本测试
正式制作前，先用2-3句台词测试整个流程：

```json
{
  "title": "测试",
  "dialogs": [
    {"id": "D001", "role": "A", "text": "第一句", "emotion": "正常"},
    {"id": "D002", "role": "B", "text": "第二句", "emotion": "正常"}
  ]
}
```

### 2. 逐步添加情绪
先确保"正常"情绪工作正常，再添加其他情绪：

```python
# 第一步：只配置"正常"
"A": {
    "正常": {...}
}

# 第二步：测试通过后添加其他情绪
"A": {
    "正常": {...},
    "开心": {...},
    "生气": {...}
}
```

### 3. 备份重要文件
每次重大修改前备份：
```bash
cp output.mp4 output_backup.mp4
cp stages/02_audio/timeline.json timeline_backup.json
```

### 4. 查看日志
遇到问题时仔细查看控制台输出，通常会指出具体问题所在。

---

## 📞 还有其他问题？

如果以上方案都无法解决你的问题：

1. 检查所有依赖是否已安装
2. 确认素材文件格式正确
3. 查看完整的错误堆栈信息
4. 尝试用最小配置重新运行

祝创作顺利！🎬
