# 沙雕动画素材准备指南

## 📁 目录结构

```
res/
├── bg/                          # 背景图
│   └── office.png               # 办公室背景（1280x720）
│
├── characters/                  # 角色素材
│   ├── A/                       # 角色A
│   │   ├── base.png             # 基础身体图（透明PNG，建议400x600）
│   │   ├── mouth/               # 嘴巴动作
│   │   │   ├── close.png        # 闭嘴
│   │   │   ├── open.png         # 张嘴
│   │   │   ├── smile.png        # 微笑（可选）
│   │   │   └── shocked.png      # 震惊嘴（可选）
│   │   └── eye/                 # 眼睛动作
│   │       ├── open.png         # 睁眼
│   │       └── close.png        # 闭眼
│   │
│   └── B/                       # 角色B（同上结构）
│       ├── base.png
│       ├── mouth/
│       │   ├── close.png
│       │   └── open.png
│       └── eye/
│           ├── open.png
│           └── close.png
│
├── effects/                     # 特效素材（可选）
│   ├── sparkle.png              # 闪光特效
│   ├── flash_white.png          # 白屏闪
│   ├── question_marks.png       # 问号特效
│   ├── sweat_drop.png           # 汗滴
│   ├── anger_mark.png           # 愤怒符号
│   └── shock_lines.png          # 震惊线
│
├── sfx/                         # 音效文件（可选）
│   ├── whoosh.mp3               # 呼啸声
│   ├── ding.mp3                 # 叮声
│   └── boom.mp3                 # 爆炸声
│
└── ref/                         # TTS参考音频（必需）
    ├── ref_a_normal.wav         # 角色A正常语气
    ├── ref_a_happy.wav          # 角色A开心语气
    ├── ref_a_angry.wav          # 角色A生气语气
    ├── ref_b_normal.wav         # 角色B正常语气
    └── ...
```

---

## 🎨 素材制作指南

### 1️⃣ **背景图 (bg/)**

**要求：**
- 格式：PNG 或 JPG
- 分辨率：1280x720（16:9）
- 风格：卡通、简洁

**获取方式：**
- 🌐 免费素材网站：Unsplash、Pexels、Pixabay
- 🤖 AI生成：Midjourney、Stable Diffusion（提示词："cartoon office background, simple style"）
- ✏️ 自己画：用 PowerPoint/Canva 绘制简单场景

**示例：**
```
office.png - 办公室背景（桌椅、电脑）
classroom.png - 教室背景
street.png - 街道背景
```

---

### 2️⃣ **角色素材 (characters/)**

#### **base.png - 基础身体图**

**要求：**
- 格式：PNG（透明背景）
- 尺寸：约 400x600 像素
- 内容：角色的完整身体（不含嘴巴和眼睛的细节，因为会动态替换）
- 风格：火柴人、简笔画、卡通人物均可

**制作方法：**
1. 用画图工具绘制一个站立的人物
2. 嘴巴位置留空或画成一条线
3. 眼睛位置画成简单的点或线
4. 导出为透明PNG

**AI生成提示词：**
```
"simple cartoon character, stick figure style, transparent background, front view, no facial features"
```

---

#### **mouth/ - 嘴巴动作**

**需要制作的图片：**
- `close.png` - 闭嘴（一条横线或微笑曲线）
- `open.png` - 张嘴（椭圆形或D形）
- `smile.png` - 微笑（向上弯曲的弧线，可选）
- `shocked.png` - 震惊嘴（大O形，可选）

**要求：**
- 格式：PNG（透明背景）
- 尺寸：约 80x40 像素
- 位置：与 base.png 中嘴巴位置对齐

**制作技巧：**
- 在 Photoshop/GIMP 中打开 base.png
- 放大嘴巴区域
- 分别绘制不同口型
- 单独保存每个口型为 PNG

---

#### **eye/ - 眼睛动作**

**需要制作的图片：**
- `open.png` - 睁眼（两个圆点或椭圆）
- `close.png` - 闭眼（两条短线或弧线）
- `surprised.png` - 惊讶眼（大圆圈，可选）

**要求：**
- 格式：PNG（透明背景）
- 尺寸：单眼约 30x30 像素
- 注意：代码会自动绘制左右两只眼睛，所以只需提供单眼图片

**制作技巧：**
- 只画一只眼睛
- 代码会在左右两侧各绘制一次
- 通过调整 `eye_offset_x` 参数控制间距

---

### 3️⃣ **特效素材 (effects/) - 可选**

**常见特效：**
- `sparkle.png` - 闪光星星（黄色小星星）
- `flash_white.png` - 白屏闪烁（半透明白色矩形）
- `question_marks.png` - 问号（多个？符号）
- `sweat_drop.png` - 汗滴（蓝色水滴）
- `anger_mark.png` - 愤怒符号（红色十字或井字）
- `shock_lines.png` - 震惊线（放射状线条）

**获取方式：**
- 🎮 游戏素材包（itch.io、OpenGameArt）
- 🌐 免费图标网站（Flaticon、IconFinder）
- ✏️ 自己画（简单几何图形即可）

---

### 4️⃣ **音效 (sfx/) - 可选**

**常见音效：**
- `whoosh.mp3` - 快速移动的呼啸声
- `ding.mp3` - 提示音/叮声
- `boom.mp3` - 爆炸/撞击声
- `laugh.mp3` - 笑声

**获取方式：**
- 🌐 freesound.org（免费注册下载）
- 🌐 爱给网（中文音效库）
- 🌐 ZapSplat.com

---

### 5️⃣ **TTS参考音频 (ref/) - 必需**

**要求：**
- 格式：WAV（16bit, 16kHz或更高）
- 时长：5-10秒
- 内容：清晰的语音样本

**录制方法：**
1. 用手机录音App录制自己的声音
2. 说一段代表性的话（如剧本中的台词）
3. 用 Audacity 剪辑成干净片段
4. 导出为 WAV 格式

**每个角色需要准备：**
- `ref_a_normal.wav` - 角色A正常语气
- `ref_a_happy.wav` - 角色A开心语气
- `ref_a_angry.wav` - 角色A生气语气
- `ref_b_normal.wav` - 角色B正常语气
- （根据情绪需求添加更多）

---

## 🛠️ 快速开始模板

如果你不想自己制作素材，可以使用以下简化方案：

### **极简版（只需3个文件）**

```
res/
├── bg/
│   └── office.png          # 任意1280x720图片
├── characters/
│   ├── A/
│   │   ├── base.png        # 随便画个火柴人
│   │   ├── mouth/
│   │   │   ├── close.png   # 一条横线
│   │   │   └── open.png    # 一个椭圆
│   │   └── eye/
│   │       ├── open.png    # 一个黑点
│   │       └── close.png   # 一条短线
│   └── B/
│       └── ...（复制A的文件夹，改颜色区分）
└── ref/
    ├── ref_a_normal.wav    # 录一段话
    └── ref_b_normal.wav    # 录一段话
```

**用PowerPoint 5分钟制作角色：**
1. 插入 → 形状 → 画圆形（头）、矩形（身体）、线条（四肢）
2. 组合所有形状
3. 右键 → 另存为图片 → PNG
4. 分别绘制不同口型和眼神，单独保存

---

## 📸 素材检查清单

在开始之前，确保你有：

- [ ] 至少1张背景图（1280x720）
- [ ] 2个角色的 base.png
- [ ] 每个角色的 mouth/close.png 和 mouth/open.png
- [ ] 每个角色的 eye/open.png 和 eye/close.png
- [ ] 每个角色至少1个参考音频（ref_xxx.wav）
- [ ] FFmpeg 已安装并加入环境变量

**可选但推荐：**
- [ ] 更多表情（smile、shocked等）
- [ ] 特效图片
- [ ] 音效文件

---

## 🎯 下一步

准备好素材后，运行：

```bash
# 初始化项目
python pipeline.py init

# 一键运行全流程
python pipeline.py run-all --topic "办公室摸鱼"
```

祝创作愉快！🎬
