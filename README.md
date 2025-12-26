# 🧠 ReflectBench

**A Reflection-Oriented Benchmark Built on AndroidWorld**

> A benchmark for evaluating agent robustness under imperfect instructions, environment inconsistencies, and human-like errors.

------

## 📌 项目简介

基于大模型的移动端智能体在 **AndroidWorld** 等基准上取得了显著进展。然而，现有评测任务大多假设：

- 用户指令是 **完美的**
- 初始环境是 **干净且一致的**
- 执行过程中 **不会出现人类常见错误**

这与真实世界中的人机交互存在明显差距。

**本项目提出一个“反思导向”的 AndroidWorld 扩展 Benchmark**，通过在**不改变任务目标本身**的前提下，引入**系统性、可控的任务扰动**，评测 Agent 在以下情形下的能力：

- 面对 **错误输入**
- 面对 **环境初始化异常**
- 面对 **误导信息与相似干扰**
- 是否具备 **发现问题 → 停止 → 修正策略** 的能力

------

## 🎯 设计目标

本 Benchmark 的核心目标包括：

1. **保持任务目标不变**

   > 扰动的是 **执行路径**，不是 **任务本身**

2. **扰动可解释、可复现**

   - 每个任务变体只引入 **单一反思维度**
   - 不组合扰动，避免因果混淆

3. **对主流 Agent 具有区分度**

   - 基础任务：Mobile-Agent-V3 ≈ 60% 成功率
   - 扰动后任务：显著拉开差距

4. **最小侵入式改造 AndroidWorld**

   - 复用原始 Task / Validator / Env
   - 扰动集中在 `initialize_task` 或 action 层

------

## 🧩 扰动类型定义

当前版本 **不组合扰动**，每个任务只包含一种反思维度：

### 1️⃣ Typing Error

模拟真实用户常见输入错误：

- 少打一个字符
- 多打一个空格
- 相似字符替换（l / 1 / I）

📌 重点考察：

> Agent 是否能意识到「输入结果不符合语义预期」

------

### 2️⃣ Non-existent Target

任务开始前，**目标对象已被删除或从未存在**：

- 文件不存在
- 笔记不存在
- 目标文件夹不存在

📌 重点考察：

> Agent 是否会盲目执行，还是先检查前置条件

------

### 3️⃣ Similar / Misleading Information

环境中存在多个**高度相似但非目标对象**：

- 相似联系人名
- 相似文件名
- 相似文件夹

📌 重点考察：

> Agent 是否具备精确匹配与信息溯源能力

------

## 📱 任务来源与覆盖 App

当前任务全部来源于 **AndroidWorld 原生任务**，覆盖以下高频 App 场景：

| App                  | 场景类型                      |
| -------------------- | ----------------------------- |
| Simple SMS Messenger | 信息发送 / 回复 / 转发        |
| Markor               | 笔记创建 / 删除 / 移动 / 编辑 |
| Files                | 文件删除 / 移动               |
| Retro Music          | 播放列表管理                  |
| Audio Recorder       | 录音与文件命名                |

------

## 🧪 任务清单（Task List）

### 📩 SMS（Simple SMS Messenger）

#### `SimpleSmsSendReceivedAddress`

| 变体                | 扰动类型   | 描述                         |
| ------------------- | ---------- | ---------------------------- |
| WithSimilarContact  | 相似干扰   | 存在多个名字极度相似的联系人 |
| WithNotExistContact | 目标不存在 | 目标联系人不存在             |
| WithTypingError     | 打字错误   | 转发内容存在拼写错误         |

------

### 🎙 Audio Recorder

#### `AudioRecorderRecordAudioWithFileName`

| 变体            | 扰动类型 | 描述               |
| --------------- | -------- | ------------------ |
| WithTypingError | 打字错误 | 录音文件名输入错误 |

------

### 📝 Markor（Markdown Notes）

#### `MarkorMoveNote`

| 变体                          | 扰动类型   | 描述                         |
| ----------------------------- | ---------- | ---------------------------- |
| WithNotExistDestinationFolder | 目标不存在 | 目标文件夹在任务开始前被删除 |
| WithSimilarFolders            | 相似干扰   | 存在多个相似文件夹           |

------

#### `MarkorCreateFolder`

| 变体            | 扰动类型 | 描述                     |
| --------------- | -------- | ------------------------ |
| WithTypingError | 打字错误 | 创建文件夹时名称输入错误 |

------

#### `MarkorDeleteNote`

| 变体             | 扰动类型   | 描述                   |
| ---------------- | ---------- | ---------------------- |
| WithNotExistNote | 目标不存在 | 目标笔记已被提前删除   |
| WithSimilarNote  | 相似干扰   | 多个相似笔记混淆 Agent |

------

#### `MarkorCreateNote`

| 变体                | 扰动类型 | 描述             |
| ------------------- | -------- | ---------------- |
| WithFileTypingError | 打字错误 | 文件名输入错误   |
| WithTextTypingError | 打字错误 | 笔记正文内容错误 |

------

#### `MarkorChangeNoteContent`

| 变体             | 扰动类型   | 描述             |
| ---------------- | ---------- | ---------------- |
| WithSimilarNote  | 相似干扰   | 多个相似笔记     |
| WithTypingError  | 打字错误   | 编辑内容输入错误 |
| WithNotExistNote | 目标不存在 | 笔记不存在       |

------

### 📂 Files

#### `FilesDeleteFile`

| 变体             | 扰动类型   | 描述         |
| ---------------- | ---------- | ------------ |
| WithSimilarFiles | 相似干扰   | 多个诱饵文件 |
| WithNotExistFile | 目标不存在 | 文件不存在   |

------

#### `FilesMoveFile`

| 变体             | 扰动类型   | 描述         |
| ---------------- | ---------- | ------------ |
| WithSimilarFiles | 相似干扰   | 多个相似文件 |
| WithNotExistFile | 目标不存在 | 文件不存在   |

------

### 🎵 Retro Music

#### `RetroCreatePlaylist`

| 变体               | 扰动类型 | 描述                       |
| ------------------ | -------- | -------------------------- |
| WithTypingError    | 打字错误 | 歌单名拼写错误             |
| WithSomeWrongSongs | 误导信息 | 已存在部分但错误的歌单内容 |

------

## 🧠 What We Measure

本 Benchmark **关心任务是否完成**的同时，重点分析：

- 是否 **发现异常**
- 是否 **重复错误行为**
- 是否 **调整策略**
- 是否 **主动修正输入或路径**

可用于分析：

- ReAct / Reflexion / Tool-Calling Agent
- Mobile-Agent-V3 / GUI-Owl / AppAgent 等

------

## 🚀 Usage

```
# 示例
python run_ma3.py \
  --suite_family=andriod_world \
  --agent_name=mobile_agent_v3 \
  --task SimpleSmsSendReceivedAddressWithTypingError
```

支持：

- 单任务 / 批量任务
- 与原 AndroidWorld 评测脚本兼容

------

## 🔮 Future Work

- ⏳ 组合扰动
- 📊 错误类型级别的成功率分析
- 🤖 扩展其他扰动类型


------

