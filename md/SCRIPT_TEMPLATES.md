# 剧本管理策略

## 📋 核心原则

**剧本应该是预先准备好的，而不是每次运行时自动生成。**

---

## 🔄 工作流程

### **情况1：已有剧本文件（最常见）**

```bash
# 直接运行
python pipeline.py run-all

# 系统行为：
# ✅ 检测到 stages/01_script/script.json 已存在
# ✅ 直接加载现有剧本
# ✅ 继续后续流程（生成音频、渲染、合成）
```

**适用场景：**
- 你已经手动编辑好了剧本
- 你想重新生成视频（不修改剧本）
- 你从其他地方复制了剧本文件

---

### **情况2：没有剧本文件（首次使用）**

```bash
# 方式A：指定主题（会尝试匹配模板）
python pipeline.py run-all --topic "足球"

# 方式B：不指定主题（随机选择模板）
python pipeline.py run-all
```

**系统行为：**
1. ⚠️ 检测到 `script.json` 不存在
2. 🎯 根据主题关键词匹配模板（如果提供了topic）
3. 🎲 如果没有匹配或没提供topic，随机选择一个模板
4. ✅ 使用选中的模板初始化 `script.json`
5. ⏸️ 提示用户检查新生成的剧本
6. 👤 用户确认后继续流程

---

## 📝 预定义模板库

系统内置了5个模板：

| 模板名称 | 关键词 | 场景 |
|---------|--------|------|
| `default` | 无匹配时 | 日常对话 |
| `football` | 足球、球赛 | 讨论比赛 |
| `office` | 办公室、摸鱼 | 职场幽默 |
| `food` | 吃饭、午餐 | 美食话题 |
| `exam` | 考试、学习 | 校园生活 |

---

## 🎯 使用示例

### **示例1：使用现有剧本**

```bash
# 1. 手动创建或编辑剧本
vim stages/01_script/script.json

# 2. 运行流程（不会修改剧本）
python pipeline.py run-all
```

---

### **示例2：首次使用，指定主题**

```bash
python pipeline.py run-all --topic "讨论足球"

# 输出：
# ⚠️  未找到 script.json，使用模板初始化...
# 🎯 根据主题 '讨论足球' 选择模板: football
# ✅ 已使用模板 'football' 初始化剧本
#    共 5 句台词
#
# ⚠️  检测到这是新生成的剧本，请检查内容是否符合预期
#    是否继续？(y/n，默认y): y
```

---

### **示例3：首次使用，随机模板**

```bash
python pipeline.py run-all

# 输出：
# ⚠️  未找到 script.json，使用模板初始化...
# 🎲 随机选择模板: office
# ✅ 已使用模板 'office' 初始化剧本
#    共 5 句台词
```

---

### **示例4：不满意模板，重新选择**

```bash
# 第一次运行（随机到不满意的模板）
python pipeline.py run-all

# 按 n 取消
# ❌ 已取消。请编辑剧本后重新运行。

# 手动编辑剧本
vim stages/01_script/script.json

# 或者删除后重新运行（会随机新模板）
rm stages/01_script/script.json
python pipeline.py run-all
```

---

## ✏️ 手动编辑剧本

任何时候都可以直接编辑剧本文件：

```bash
# 编辑剧本
vim stages/01_script/script.json

# 或者用其他编辑器
code stages/01_script/script.json
notepad stages/01_script/script.json  # Windows
```

**编辑后重新生成视频：**
```bash
# 只需重新运行后续步骤
python pipeline.py stage2
python pipeline.py stage3
python pipeline.py stage4

# 或者一键重做
python pipeline.py regenerate-line --line D001  # 只重做某一句
```

---

## 💡 最佳实践

### **推荐工作流程**

```
1. 首次使用：
   python pipeline.py run-all --topic "足球"
   ↓
2. 检查生成的剧本，不满意就编辑
   vim stages/01_script/script.json
   ↓
3. 满意后继续（按 y）
   ↓
4. 等待视频生成完成
   ↓
5. 查看 output.mp4
   ↓
6. 如需修改，编辑剧本或动作配置
   ↓
7. 重新运行相关步骤
```

---

### **快速迭代技巧**

```bash
# 修改了剧本中的一句台词
vim stages/01_script/script.json

# 只重新生成该句（自动完成所有步骤）
python pipeline.py regenerate-line --line D002

# 查看新版本
vlc output.mp4
```

---

## 🔧 添加自定义模板

编辑 `pipeline.py` 中的 `generate_script_templates()` 函数：

```python
def generate_script_templates():
    """预定义的剧本模板库"""
    return {
        # ... 现有模板 ...
        
        "my_template": {
            "title": "我的自定义剧本",
            "dialogs": [
                {"id": "D001", "role": "A", "text": "第一句", "emotion": "开心"},
                {"id": "D002", "role": "B", "text": "第二句", "emotion": "正常"}
            ]
        }
    }
```

然后在 `generate_script()` 函数的 `template_map` 中添加关键词映射：

```python
template_map = {
    # ... 现有映射 ...
    "我的关键词": "my_template"
}
```

---

## ❓ 常见问题

### Q1: 我想完全自定义剧本，不想用模板怎么办？

```bash
# 直接创建剧本文件
cat > stages/01_script/script.json << EOF
{
  "title": "我的故事",
  "dialogs": [
    {"id": "D001", "role": "A", "text": "自定义内容", "emotion": "正常"}
  ]
}
EOF

# 然后运行
python pipeline.py run-all
```

---

### Q2: 模板生成的剧本不满意怎么办？

```bash
# 方案1：直接编辑
vim stages/01_script/script.json

# 方案2：删除后重新运行（会随机新模板）
rm stages/01_script/script.json
python pipeline.py run-all

# 方案3：指定不同主题
python pipeline.py run-all --topic "考试"
```

---

### Q3: 如何查看当前使用的剧本？

```bash
cat stages/01_script/script.json
```

---

### Q4: 可以在运行中途修改剧本吗？

可以，但需要重新运行后续步骤：

```bash
# 假设在 Stage 2 完成后想修改剧本
vim stages/01_script/script.json

# 重新从 Stage 2 开始
python pipeline.py stage2
python pipeline.py stage3
python pipeline.py stage4
```

---

## 📊 总结

| 场景 | 操作 | 结果 |
|------|------|------|
| 已有剧本 | `run-all` | 直接使用现有剧本 |
| 无剧本+有topic | `run-all --topic "X"` | 尝试匹配模板 |
| 无剧本+无topic | `run-all` | 随机选择模板 |
| 不满意模板 | 编辑或删除后重试 | 自定义或换模板 |

**核心理念：剧本由你掌控，模板只是辅助初始化的工具。** 🎬✨
