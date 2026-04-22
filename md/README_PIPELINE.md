# 沙雕动画工业化流程 🎬

一个支持**增量更新**和**最小人工干预**的沙雕动画自动生成系统。

---

## ✨ 核心特性

- 🤖 **AI辅助生成**：自动生成剧本、动作配置
- ⚡ **增量更新**：修改单句台词只需重新渲染该部分
- 🎯 **最小干预**：仅在剧本和视频生成后需要人工审核
- 📝 **手动编辑**：支持直接编辑JSON配置文件
- 🔄 **覆盖式更新**：简单直观，无需复杂的状态管理

---

## 🚀 快速开始

### 1. 准备环境

```bash
# 安装依赖
pip install soundfile numpy opencv-python requests

# 启动TTS服务器（在新终端）
python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

### 2. 准备素材

详见 [MATERIALS_GUIDE.md](MATERIALS_GUIDE.md)

**最小素材清单：**
- 背景图（1280x720）
- 2个角色的身体图和五官分图
- TTS参考音频

### 3. 运行流程

```bash
# 一键全自动
python pipeline.py run-all --topic "办公室摸鱼"

# 或分步执行
python pipeline.py init
python pipeline.py stage1 --topic "办公室摸鱼"
# 编辑 stages/01_script/script.json
python pipeline.py stage2
python pipeline.py stage3
python pipeline.py stage4
```

---

## 📋 工作流程

```
┌─────────────┐
│ Stage 1     │  生成剧本 (script.json)
│ 剧本生成     │  👤 人工审核点1
└──────┬──────┘
       ↓
┌─────────────┐
│ Stage 2     │  生成音频 + 动作配置 (timeline.json)
│ 音频+动作    │  🤖 自动完成
└──────┬──────┘
       ↓
┌─────────────┐
│ Stage 3     │  渲染帧序列 (frames/*.png)
│ 帧渲染       │  🤖 自动完成
└──────┬──────┘
       ↓
┌─────────────┐
│ Stage 4     │  合成视频 (output.mp4)
│ 视频合成     │  👤 人工审核点2
└─────────────┘
```

---

## 🔄 修改与迭代

### 修改某句台词

```bash
# 1. 编辑剧本
vim stages/01_script/script.json

# 2. 重新生成该行（自动更新音频、动作、帧、视频）
python pipeline.py regenerate-line --line D002
```

### 调整动作配置

```bash
# 1. 编辑时间轴
vim stages/02_audio/timeline.json

# 2. 重新渲染并合成
python pipeline.py stage3 --line D002
python pipeline.py stage4
```

---

## 📂 项目结构

```
sddh/
├── pipeline.py                  # 主控制脚本 ⭐
├── MATERIALS_GUIDE.md           # 素材准备指南
├── USAGE_GUIDE.md               # 详细使用手册
├── README_PIPELINE.md           # 本文件
│
├── stages/                      # 各阶段产物
│   ├── 01_script/
│   │   └── script.json          # 剧本
│   ├── 02_audio/
│   │   ├── audio_files/         # 单句音频
│   │   ├── merged_audio.wav     # 合并音频
│   │   └── timeline.json        # 时间轴+动作
│   └── 03_frames/
│       └── frames/              # 帧序列
│
├── res/                         # 素材目录
│   ├── bg/                      # 背景图
│   ├── characters/              # 角色素材
│   ├── effects/                 # 特效
│   ├── sfx/                     # 音效
│   └── ref/                     # TTS参考音频
│
└── output.mp4                   # 最终视频
```

---

## 🛠️ 常用命令

| 命令 | 说明 |
|------|------|
| `python pipeline.py init` | 初始化项目目录 |
| `python pipeline.py stage1 --topic "XXX"` | 生成剧本 |
| `python pipeline.py stage2` | 生成音频和动作 |
| `python pipeline.py stage3` | 渲染所有帧 |
| `python pipeline.py stage3 --line D001` | 只渲染指定行 |
| `python pipeline.py stage4` | 合成视频 |
| `python pipeline.py regenerate-line --line D002` | 重新生成单句并重做后续 |
| `python pipeline.py run-all --topic "XXX"` | 一键全流程 |

---

## 📖 详细文档

- [MATERIALS_GUIDE.md](MATERIALS_GUIDE.md) - 素材准备完全指南
- [USAGE_GUIDE.md](USAGE_GUIDE.md) - 详细使用手册和常见问题

---

## 💡 设计理念

1. **极简主义**：没有复杂的状态追踪，每次都是"覆盖式"更新
2. **单一数据源**：timeline.json 包含所有信息（时间轴+动作+帧范围）
3. **人工最少干预**：只在关键节点审核，中间环节全自动
4. **易于理解**：新人也能快速上手，代码结构简单清晰

---

## 🎯 下一步优化方向

- [ ] 集成AI自动生成剧本（目前使用示例模板）
- [ ] WebUI可视化编辑器
- [ ] 更多预设动作模板
- [ ] 批量处理多个项目
- [ ] 云端素材库

---

## 📝 许可证

本项目基于原有 GPT-SoVITS 项目进行扩展。

---

**祝创作愉快！** 🎬✨
