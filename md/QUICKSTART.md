# 沙雕动画工业化流程 - 项目总结

## 📦 已实现的功能

### ✅ 核心功能

1. **完整的Pipeline框架** ([pipeline.py](file:///home/simmy/code/sddh/pipeline.py))
   - Stage 1: 剧本生成（支持AI生成占位）
   - Stage 2: TTS音频生成 + 动作配置自动生成
   - Stage 3: 帧序列渲染（支持增量渲染）
   - Stage 4: FFmpeg视频合成
   - 单句重新生成命令（`regenerate-line`）

2. **统一的数据结构**
   - `timeline.json` 合并了时间轴和动作配置
   - 包含完整的元数据、音频信息、动作列表、帧范围

3. **自动化目录管理**
   - `ensure_dirs()` 自动创建所有必需目录
   - 无需手动创建文件夹

4. **增量更新支持**
   - `--line` 参数指定只渲染特定行
   - `regenerate-line` 命令一键重做单句

5. **角色音量均衡**
   - 基于角色的音量增益配置
   - 防止爆音的clipping处理

6. **双层语速控制**
   - 角色基础语速 × 情绪语速
   - 灵活调整说话节奏

---

## 📁 文件清单

### 核心代码
- ✅ [pipeline.py](file:///home/simmy/code/sddh/pipeline.py) - 主控制脚本（557行）
- ✅ [generate_placeholders.py](file:///home/simmy/code/sddh/generate_placeholders.py) - 占位素材生成器

### 文档
- ✅ [README_PIPELINE.md](file:///home/simmy/code/sddh/README_PIPELINE.md) - 项目总览
- ✅ [MATERIALS_GUIDE.md](file:///home/simmy/code/sddh/MATERIALS_GUIDE.md) - 素材准备完全指南（超详细）
- ✅ [USAGE_GUIDE.md](file:///home/simmy/code/sddh/USAGE_GUIDE.md) - 使用手册和常见问题
- ✅ [QUICKSTART.md](file:///home/simmy/code/sddh/QUICKSTART.md) - 本文件（快速开始）

### 示例数据
- ✅ [stages/01_script/script.json](file:///home/simmy/code/sddh/stages/01_script/script.json) - 示例剧本

### 工具脚本
- ✅ [start.sh](file:///home/simmy/code/sddh/start.sh) - 快速启动脚本

---

## 🎯 下一步操作

### 1️⃣ 生成占位素材（测试用）

```bash
python generate_placeholders.py
```

这会创建彩色的矩形占位图，用于测试流程是否正常。

---

### 2️⃣ 准备真实素材

按照 [MATERIALS_GUIDE.md](file:///home/simmy/code/sddh/MATERIALS_GUIDE.md) 的说明准备：

**必需素材：**
```
res/
├── bg/office.png              # 背景图（1280x720）
├── characters/A/base.png      # 角色A身体
├── characters/A/mouth/close.png
├── characters/A/mouth/open.png
├── characters/A/eye/open.png
├── characters/A/eye/close.png
├── characters/B/...           # 角色B（同上）
└── ref/ref_a_normal.wav       # TTS参考音频
    └── ref_b_normal.wav
```

**提示：** 
- 可以先用占位素材测试流程
- 确认流程正常后再替换为真实素材

---

### 3️⃣ 启动TTS服务器

```bash
# 在新终端运行
python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

---

### 4️⃣ 运行完整流程

#### **方式A：一键全自动（推荐）**

```bash
python pipeline.py run-all --topic "办公室摸鱼"
```

流程会：
1. 生成示例剧本
2. **暂停让你编辑剧本**（按回车继续）
3. 生成所有音频和动作
4. 渲染所有帧
5. 合成视频

#### **方式B：分步执行**

```bash
# Step 1: 初始化
python pipeline.py init

# Step 2: 生成剧本
python pipeline.py stage1 --topic "办公室摸鱼"

# ✋ 编辑剧本
vim stages/01_script/script.json

# Step 3: 生成音频+动作
python pipeline.py stage2

# Step 4: 渲染帧
python pipeline.py stage3

# Step 5: 合成视频
python pipeline.py stage4

# 查看结果
vlc output.mp4
```

---

## 🔄 修改与迭代示例

### 修改第2句台词

```bash
# 1. 编辑剧本
vim stages/01_script/script.json
# 修改 D002 的 text 字段

# 2. 一键重新生成（自动更新音频、动作、帧、视频）
python pipeline.py regenerate-line --line D002
```

### 调整动作

```bash
# 1. 编辑时间轴
vim stages/02_audio/timeline.json
# 找到 D002 的 actions 数组进行修改

# 2. 重新渲染并合成
python pipeline.py stage3 --line D002
python pipeline.py stage4
```

---

## 📊 输出文件

```
project/
├── stages/
│   ├── 01_script/
│   │   └── script.json              # 剧本（可编辑）⭐
│   ├── 02_audio/
│   │   ├── audio_files/             # 单句音频
│   │   ├── merged_audio.wav         # 合并音频
│   │   └── timeline.json            # 时间轴+动作（可编辑）⭐
│   └── 03_frames/
│       └── frames/                  # 帧序列（PNG）
└── output.mp4                       # 最终视频 ⭐⭐⭐
```

---

## 💡 关键设计亮点

1. **极简架构**
   - 没有复杂的checksum追踪
   - 没有状态机管理
   - 覆盖式更新，简单直观

2. **单一数据源**
   - `timeline.json` 包含所有信息
   - 避免多文件同步问题

3. **最小人工干预**
   - 只在2个节点需要审核
   - 中间环节全自动

4. **灵活的增量更新**
   - 可以单独重生成某一句
   - 节省大量时间

---

## ❓ 常见问题

### Q: 如何更换背景？
```bash
cp my_bg.png res/bg/office.png
python pipeline.py stage3
python pipeline.py stage4
```

### Q: 角色口型不同步？
编辑 `pipeline.py` 中的 `MOUTH_THRESHOLD` 参数（默认0.15）

### Q: 角色位置不对？
编辑 `render_frames()` 函数中的 `A_X, A_Y, B_X, B_Y` 参数

### Q: TTS连接失败？
确保已启动TTS服务器：
```bash
python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

---

## 📖 相关文档

- 📘 [README_PIPELINE.md](file:///home/simmy/code/sddh/README_PIPELINE.md) - 项目总览
- 📗 [MATERIALS_GUIDE.md](file:///home/simmy/code/sddh/MATERIALS_GUIDE.md) - 素材准备指南（必读）
- 📙 [USAGE_GUIDE.md](file:///home/simmy/code/sddh/USAGE_GUIDE.md) - 详细使用手册

---

## 🎬 开始创作吧！

```bash
# 快速测试（使用占位素材）
python generate_placeholders.py
python pipeline.py run-all --topic "测试视频"

# 准备好真实素材后
python pipeline.py run-all --topic "我的第一个沙雕动画"
```

祝创作愉快！✨
