# WeRead 笔记 RAG 系统 - Demo 总结

## 一、项目概述

本项目实现了一个完整的 **WeRead 读书笔记 RAG + 笔记生成系统**，从 WeRead 获取数据开始，到生成结构化的读书笔记结束。

---

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    WeRead 书籍数据                           │
│                   (weread_api.py)                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 generate_highlights.py                      │
│              (生成 md 格式的划线笔记)                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        rag.py                                │
│              (分块 + 向量化 + 存储)                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   note_generator.py                          │
│               (检索 + 生成读书笔记)                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      输出：md 笔记                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、文件结构

```
WeRead_Note/
├── weread_api.py           # WeRead API - 获取书籍数据
├── generate_highlights.py  # 生成划线笔记 md 文件
├── rag.py                  # 分块 + 向量化 + 存储
├── note_generator.py       # 笔记生成
├── vectorstore/            # Chroma 向量数据库
└── output/
    ├── 巴比伦最富有的人.md         # 原始划线笔记
    └── 巴比伦最富有的人_笔记.md   # 生成的读书笔记
```

---

## 四、各模块详解

### 1. weread_api.py - WeRead 数据获取

**功能：** 通过微信读书的 API 获取用户书籍信息和划线内容

**核心类：** `WeReadAPI`

**主要方法：**

| 方法 | 功能 |
|------|------|
| `get_bookshelf()` | 获取用户书架列表 |
| `get_book_info(book_id)` | 获取书籍基本信息（书名、作者等） |
| `get_notes(book_id)` | 获取书籍的所有笔记和划线 |
| `get_chapters(book_id)` | 获取书籍章节信息 |

**API 端点：**

- `https://weread.qq.com/web/bookshelf` - 获取书架
- `https://weread.qq.com/web/book/info/{book_id}` - 书籍信息
- `https://weread.qq.com/web/book/notes/{book_id}` - 笔记和划线
- `https://weread.qq.com/web/book/chapters/{book_id}` - 章节信息

**返回数据：**
- 书籍信息：书名、作者、出版社、封面 URL 等
- 划线内容：文本、页码、创建时间、颜色等
- 笔记内容：用户添加的笔记文字

---

### 2. generate_highlights.py - 生成划线笔记

**功能：** 将 WeRead API 获取的数据转换为 md 格式的笔记文件

**核心函数：** `generate_markdown(book_id, book_info, notes, output_path)`

**输出格式：**

```markdown
# 书名

## 📚 划线
> 划线内容1
> 划线内容2
> 划线内容3

## 📝 笔记
- 📝 笔记内容1
- 📝 笔记内容2
```

**处理逻辑：**
1. 从 API 获取书籍信息和划线数据
2. 按章节分组
3. 转换为 md 格式（`>` 表示划线，`- 📝` 表示笔记）
4. 保存到 `output/` 目录

---

### 3. rag.py - 分块 & 向量化 & 存储

**功能：** 将 md 文件分块，向量化后存入向量数据库

#### 3.1 TextChunker 类

**参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| chunk_size | 200 | 每个 chunk 的最大字符数 |
| chunk_overlap | 30 | chunk 之间的重叠字符数 |

**分块策略：**
- 使用 `RecursiveCharacterTextSplitter`
- 优先按 `\n> `（划线分隔符）切分
- 次优先按 `\n`、`。`、`！`、`？` 切分

**metadata 字段：**
```python
{
    "book_id": "书籍ID",
    "book_title": "书名",
    "chapter": "章节名",
    "chunk_index": 0,
    "section_type": "划线" 或 "笔记"
}
```

#### 3.2 RAGPipeline 类

**功能：** 构建向量数据库

**方法：**
| 方法 | 功能 |
|------|------|
| `build_vectorstore(docs, persist_dir)` | 分块 → 向量 → 存 Chroma |
| `load_vectorstore(persist_dir)` | 加载已有向量库 |
| `search(query, k)` | 相似度搜索 |

**Embedding 配置：**
- 模型：`DashScopeEmbeddings`
- 模型名：`text-embedding-v3`（qwen）
- 向量库：`Chroma`

---

### 4. note_generator.py - 笔记生成

**功能：** 基于检索到的内容生成结构化读书笔记

**核心类：** `NoteGenerator`

**模型配置：**
- 模型：`ChatTongyi` (qwen3-max)

#### 两阶段生成流程

**Stage 1: 生成章节笔记**
```
输入：某章节的所有 chunks
处理：调用 LLM 生成 50-150 字总结
输出：{"章节名": "总结内容", ...}
```

**Stage 2: 生成整体框架**
```
输入：所有章节笔记
处理：合并章节总结，调用 LLM 生成整体框架
输出：200-400 字的整体框架
```

**方法：**
| 方法 | 功能 |
|------|------|
| `generate_chapter_notes(documents)` | 按章节生成笔记 |
| `generate_outline(chapter_notes)` | 生成整体框架 |
| `generate(documents)` | 主入口，返回章节笔记+整体框架 |
| `save_to_markdown(result, path, title)` | 保存为 md 文件 |

---

## 五、使用流程

### Step 1: 获取 WeRead 数据

```python
from weread_api import WeReadAPI

api = WeReadAPI()
book_id = "12345678"

# 获取书籍信息
book_info = api.get_book_info(book_id)

# 获取笔记和划线
notes = api.get_notes(book_id)
```

### Step 2: 生成 md 文件

```python
from generate_highlights import generate_markdown

generate_markdown(book_id, book_info, notes, "./output/书名.md")
```

### Step 3: 分块 + 向量化（一次性）

```python
from rag import TextChunker, RAGPipeline

# 分块
chunker = TextChunker(chunk_size=200, chunk_overlap=30)
docs = chunker.chunk_md("./output/书名.md", book_id="书名")

# 向量化 + 存储
rag = RAGPipeline()
vectorstore = rag.build_vectorstore(docs, persist_dir="./vectorstore")
```

### Step 4: 生成笔记（每次查询）

```python
from note_generator import NoteGenerator
from rag import RAGPipeline
from langchain_core.documents import Document

# 加载向量库
rag = RAGPipeline()
vs = rag.load_vectorstore("./vectorstore")

# 获取所有 chunks
all_data = vs.get()
docs = [Document(page_content=c, metadata=m) 
        for c, m in zip(all_data['documents'], all_data['metadatas'])]

# 生成笔记
generator = NoteGenerator()
result = generator.generate(docs)

# 保存为 md
generator.save_to_markdown(result, "./output/书名_笔记.md", "书名")
```

---

## 六、API 配置

| 组件 | 模型 | 来源 |
|------|------|------|
| Embedding | text-embedding-v3 | DashScope (qwen) |
| LLM | qwen3-max | DashScope (qwen) |
| 向量库 | - | Chroma |

---

## 七、核心参数汇总

| 模块 | 参数 | 值 |
|------|------|-----|
| 分块 | chunk_size | 200 |
| 分块 | chunk_overlap | 30 |
| 向量库 | persist_dir | ./vectorstore |
| 检索 | top_k | 5（默认） |
| 章节笔记 | 字数 | 50-150 字 |
| 整体框架 | 字数 | 200-400 字 |

---

## 八、Demo 测试结果

测试书籍：《巴比伦最富有的人》

- ✅ 成功从 WeRead 获取数据
- ✅ 生成 md 格式划线笔记
- ✅ 分块：多个 chunks（每条划线一个）
- ✅ 向量化：存储到 Chroma
- ✅ 检索：成功返回相关内容
- ✅ 生成笔记：章节笔记 + 整体框架
- ✅ 输出：md 格式读书笔记





## 九、待优化项目 

####  1、划线内容从API读取以后直接向量化，不必先存为md文档再向量化
####  2、agent
####  3、基于全书内容总结

---

*End of Demo Summary*

# WeRead_Note
