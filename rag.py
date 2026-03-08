#!/usr/bin/env python3
"""
RAG 模块：文本分块、向量化、存储
使用阿里云百炼 Qwen embedding 模型
"""

import os
import re
from typing import List
from langchain_core.documents import Document
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter



class TextChunker:
    """文本分块器 - 按章节切分划线内容"""
    
    def __init__(self, chunk_size: int = 200, chunk_overlap: int = 30):
        """
        初始化分块器
        
        Args:
            chunk_size: 每个 chunk 的最大字符数
            chunk_overlap: chunk 之间的重叠字符数
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n> ", "\n", "。", "！", "？", " "]  # 优先按划线分隔
        )
    
    def chunk_md(self, md_path: str, book_id: str = None) -> List[Document]:
        """
        读取 md 文件，按固定大小分块
        
        Args:
            md_path: md 文件路径
            book_id: 书籍唯一标识（可选，默认用文件名）
        
        Returns:
            Document 列表
        """
        # 自动生成 book_id（如果没提供）
        if not book_id:
            book_id = os.path.basename(md_path).replace('.md', '')
        
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取书名
        book_title = ""
        if content.startswith('# '):
            book_title = content.split('\n')[0][2:].strip()
        
        # 用分隔符 "\n> " 把划线内容分开，这样每条划线会单独成块
        # 先把 > 替换成特殊的分隔符标记
        content_for_split = content.replace('\n> ', '\n__HIGHLIGHT__ ')
        
        # 用 RecursiveCharacterTextSplitter 分块
        texts = self.splitter.split_text(content_for_split)
        
        documents = []
        for i, text in enumerate(texts):
            # 判断是划线还是笔记
            section_type = "划线"
            if "📝 笔记" in text:
                section_type = "笔记"
            
            # 清理文本，恢复原始格式
            clean_text = text.replace('__HIGHLIGHT__ ', '> ')
            
            # 提取章节名（判断属于划线还是笔记区域）
            if section_type == "笔记":
                chapter = "笔记"
            else:
                # 从内容中尝试提取章节名
                chapter = "划线"
                # 尝试匹配 "第X章"
                import re
                match = re.search(r'(第[一二三四五六七八九十]+章[^，。]*)', clean_text)
                if match:
                    chapter = match.group(1)
            
            documents.append(Document(
                page_content=clean_text.strip(),
                metadata={
                    "book_id": book_id,
                    "book_title": book_title,
                    "chapter": chapter,
                    "chunk_index": i,
                    "section_type": section_type
                }
            ))
        
        return documents


class RAGPipeline:
    """RAG 管道：向量化 + 存储 + 检索"""
    
    def __init__(self, model_name: str = "text-embedding-v3"):
        """
        初始化 RAG 管道
        
        Args:
            model_name: embedding 模型名称（默认 qwen 的 text-embedding-v3）
        """
        self.embeddings = DashScopeEmbeddings(
            model=model_name
        )
        self.vectorstore = None
    
    def build_vectorstore(self, documents: List[Document], persist_dir: str = None):
        """
        将文档向量化并存储到向量数据库
        
        Args:
            documents: Document 列表
            persist_dir: 持久化目录（可选）
        """
        if not documents:
            raise ValueError("没有文档需要向量化")
        
        if persist_dir:
            # 持久化到磁盘
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=persist_dir
            )
        else:
            # 内存中
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
        
        return self.vectorstore
    
    def load_vectorstore(self, persist_dir: str):
        """
        加载已存在的向量数据库
        
        Args:
            persist_dir: 持久化目录
        """
        self.vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=self.embeddings
        )
        
        return self.vectorstore
    
    def retrieve(self, query: str, k: int = 3, book_id: str = None) -> List[Document]:
        """
        检索相似文档
        
        Args:
            query: 查询文本
            k: 返回数量
            book_id: 可选，按书籍筛选
        
        Returns:
            相关的 Document 列表
        """
        if not self.vectorstore:
            raise ValueError("向量数据库未初始化")
        
        # 筛选条件
        filter_dict = {"book_id": book_id} if book_id else None
        
        docs = self.vectorstore.similarity_search(query, k=k, filter=filter_dict)
        
        return docs


# 测试
if __name__ == "__main__":
    # ========== 1. 分块 ==========
    chunker = TextChunker(chunk_size=200, chunk_overlap=30)
    docs = chunker.chunk_md("./output/巴比伦最富有的人.md", book_id="babylon_richest")
    
    print(f"分块数量: {len(docs)}")
    for i, doc in enumerate(docs):
        print(f"\n--- Chunk {i+1} ---")
        print(f"metadata{doc.metadata}\n")
        print(f"内容预览: {doc.page_content[:]}...")
    
    if not docs:
        print("错误：没有分块成功！")
        exit(1)
    
    # 2. 向量化 + 存储
    print("\n\n正在向量化...")
    rag = RAGPipeline()
    vectorstore = rag.build_vectorstore(docs, persist_dir="./vectorstore")
    
    print("✓ 向量数据库已创建")
    
    # 3. 检索测试
    print("\n检索测试: 这本书讲了什么？")
    results = rag.retrieve("这本书讲了什么？", k=2)
    
    for i, doc in enumerate(results):
        print(f"\n--- 结果 {i+1} ---")
        print(doc.page_content[:200])