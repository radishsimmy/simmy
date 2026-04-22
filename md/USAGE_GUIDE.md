# 沙雕动画工业化流程 - 使用指南

## 🚀 快速开始

### 第一步：准备环境

```bash
# 1. 确保已安装依赖
pip install soundfile numpy opencv-python requests

# 2. 启动TTS服务器（在新终端运行）
python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml

# 3. 确认FFmpeg已安装
ffmpeg -version
```

---

### 第二步：准备素材

按照 `MATERIALS_GUIDE.md` 的说明准备必需素材：

**最小化素材清单：**
```
res/
├── bg/office.png              # 背景图
├── characters/A/base.png      # 角色A身体
├── characters/A/mouth/close.png
├── characters/A/mouth/open.png
├── characters/A/eye/open.png
├── characters/A/eye/close.png
├── characters/B/...           # 角色B（同上）
└── ref/ref_a_normal.wav       # TTS参考音频
    └── ref_b_normal.wav
```

**提示：** 如果暂时没有素材，可以先用纯色矩形代替，测试流程是否正常。

---

### 第三步：运行流程

#### **方式1：一键全自动（推荐新手）**

```bash
python pipeline.py run-all --topic "办公室摸鱼"
```

流程会自动：
1. ✅ 创建目录结构
2. ✅ 生成示例剧本
3. ⏸️ **暂停等待你编辑剧本**（按回车继续）
4. ✅ 生成所有音频
5. ✅ 生成动作配置
6. ✅ 渲染所有帧
7. ✅ 合成视频

---

#### **方式2：分步执行（推荐进阶用户）**

```bash
# Step 1: 初始化目录
python pipeline.py init

# Step 2: 生成剧本
python pipeline.py stage1 --topic "办公室摸鱼"

# ✋ 手动编辑剧本
vim stages/01_script/script.json
# 或
notepad stages/01_script/script.json

# Step 3: 生成音频和动作
python pipeline.py stage2

# Step 4: 渲染帧
python pipeline.py stage3

# Step 5: 合成视频
python pipeline.py stage4

# 查看结果
vlc output.mp4
```

---

## 🔄 修改与迭代

### **场景1：修改某句台词文本**

```bash
# 1. 编辑剧本
vim stages/01_script/script.json
# 修改 D002 的 text 字段

# 2. 重新生成该句（自动更新音频、时间轴、动作）
python pipeline.py regenerate-line --line D002

# ✅ 完成！output.mp4 已更新
```

---

### **场景2：调整某句的动作**

```bash
# 1. 编辑时间轴文件
vim stages/02_audio/timeline.json
# 找到 D002 的 actions 数组，修改或添加动作

# 2. 重新渲染该句的帧
python pipeline.py stage3 --line D002

# 3. 重新合成视频
python pipeline.py stage4
```

---

### **场景3：更换背景图**

```bash
# 1. 替换背景图
cp my_new_bg.png res/bg/office.png

# 2. 重新渲染所有帧
python pipeline.py stage3

# 3. 重新合成视频
python pipeline.py stage4
```

---

### **场景4：调整角色位置**

编辑 `pipeline.py` 中的角色位置参数：

```python
# 在 render_frames() 函数中
A_X, A_Y = int(W * 0.25), int(H * 0.65)  # 修改这里的比例
B_X, B_Y = int(W * 0.75), int(H * 0.65)
```

然后重新渲染：
```bash
python pipeline.py stage3
python pipeline.py stage4
```

---

## 📊 输出文件说明

```
project/
├── stages/
│   ├── 01_script/
│   │   └── script.json              # 剧本（可编辑）
│   ├── 02_audio/
│   │   ├── audio_files/             # 单句音频
│   │   ├── merged_audio.wav         # 合并音频
│   │   └── timeline.json            # 时间轴+动作（可编辑）
│   └── 03_frames/
│       └── frames/                  # 帧序列（PNG）
└── output.mp4                       # 最终视频 ⭐
```

---

## 🛠️ 常用命令速查

| 命令 | 作用 |
|------|------|
| `python pipeline.py init` | 初始化目录 |
| `python pipeline.py stage1 --topic "XXX"` | 生成剧本 |
| `python pipeline.py stage2` | 生成音频+动作 |
| `python pipeline.py stage3` | 渲染所有帧 |
| `python pipeline.py stage3 --line D001 D002` | 只渲染指定行 |
| `python pipeline.py stage4` | 合成视频 |
| `python pipeline.py regenerate-line --line D002` | 重新生成单句并重做后续步骤 |
| `python pipeline.py run-all --topic "XXX"` | 一键全流程 |

---

## ❓ 常见问题

### Q1: TTS服务器连接失败
```bash
# 检查服务器是否运行
curl http://127.0.0.1:9880/

# 如果没有响应，启动服务器
python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

### Q2: 找不到背景图或角色图
- 检查 `res/` 目录下是否有对应的文件
- 确保文件名完全匹配（区分大小写）
- 运行 `python pipeline.py init` 自动创建目录结构

### Q3: 视频合成失败
```bash
# 检查FFmpeg是否安装
ffmpeg -version

# 检查帧文件是否存在
ls stages/03_frames/frames/frame_*.png

# 检查音频文件是否存在
ls stages/02_audio/merged_audio.wav
```

### Q4: 角色口型不同步
编辑 `pipeline.py` 中的 `MOUTH_THRESHOLD` 参数：
```python
MOUTH_THRESHOLD = 0.15  # 降低这个值让小声也能触发动画
```

### Q5: 角色五官位置不对
编辑 `draw_character()` 函数中的比例参数：
```python
eye_y = int(bh * 0.58)     # 调整眼睛垂直位置
mouth_y = int(bh * 0.75)   # 调整嘴巴垂直位置
eye_offset_x = -12         # 调整眼睛水平间距
mouth_offset_x = -20       # 调整嘴巴水平位置
```

---

## 🎯 最佳实践

1. **先小后大**：先用3-5句台词测试流程，确认无误后再制作长视频
2. **版本管理**：每次重大修改前备份 `output.mp4`
3. **素材复用**：建立自己的素材库，新项目直接复制
4. **增量迭代**：发现问题只重新渲染受影响的部分，节省时间
5. **日志记录**：遇到问题时查看控制台输出，定位错误原因

---

## 📞 需要帮助？

如果遇到问题：
1. 检查控制台错误信息
2. 确认所有依赖已安装
3. 确认素材文件格式正确
4. 查看本文档的"常见问题"部分

祝创作愉快！🎬✨
