#!/usr/bin/env python3
"""
NoteGenerator: 生成读书笔记
- 先按章节生成笔记
- 再生成整体框架
"""

import os
from typing import List, Dict

from langchain_core.documents import Document
from langchain_community.chat_models import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from rag import RAGPipeline



class NoteGenerator:
    """基于检索内容生成读书笔记"""
    
    def __init__(self, model_name: str = "qwen3-max"):
        """
        初始化笔记生成器
        
        Args:
            model_name: LLM 模型名称
        """
        self.llm = ChatTongyi(model_name=model_name)
    
    def _generate_single_chapter_note(self, chapter_name: str, contents: List[str]) -> str:
        """生成单个章节的笔记
        
        Args:
            chapter_name: 章节名称
            contents: 该章节下的所有内容
        
        Returns:
            章节笔记内容
        """
        context = "\n\n".join(contents)
        
        prompt = ChatPromptTemplate.from_template("""
                    请根据以下划线内容，为章节「{chapter_name}」生成一段总结笔记。

                    划线内容：
                    {context}

                    要求：
                    1. 总结该章节的核心内容
                    2. 用中文输出
                    3. 简洁有条理
                    4. 50-150字左右

        """)
        
        chain = prompt | self.llm
        result = chain.invoke({
            "chapter_name": chapter_name,
            "context": context
        })
        
        return result.content
    
    def generate_chapter_notes(self, documents: List[Document]) -> Dict[str, str]:
        """按章节生成笔记
        
        Args:
            documents: 检索到的文档列表
        
        Returns:
            章节名 -> 笔记内容 的字典
        """
        # 1. 按章节分组
        chapter_contents: Dict[str, List[str]] = {}
        
        for doc in documents:
            chapter = doc.metadata.get("chapter", "未知章节")
            if chapter not in chapter_contents:
                chapter_contents[chapter] = []
            chapter_contents[chapter].append(doc.page_content)
        
        # 2. 每个章节生成总结
        chapter_notes = {}
        for chapter, contents in chapter_contents.items():
            if contents:  # 跳过空内容
                note = self._generate_single_chapter_note(chapter, contents)
                chapter_notes[chapter] = note
        
        return chapter_notes
    
    def generate_outline(self, chapter_notes: Dict[str, str]) -> str:
        """根据章节笔记生成整体框架
        
        Args:
            chapter_notes: 章节名 -> 笔记内容 的字典
        
        Returns:
            整体框架内容
        """
        # 合并所有章节笔记
        context = "\n\n".join([
            f"【{chapter}】\n{note}"
            for chapter, note in chapter_notes.items()
        ])
        
        prompt = ChatPromptTemplate.from_template("""
                    请根据以下各章节的总结笔记，生成这本书的整体框架。

                    各章节总结：
                    {context}

                    要求：
                    1. 梳理书本的整体结构和逻辑
                    2. 总结核心主题和观点
                    3. 用中文输出
                    4. 结构清晰，使用markdown格式
                    5. 200-400字左右

                    整体框架：
    """)
        
        chain = prompt | self.llm
        result = chain.invoke({"context": context})
        
        return result.content
    
    def generate(self, documents: List[Document]) -> Dict[str, any]:
        """主入口：生成章节笔记 + 整体框架
        
        Args:
            documents: 检索到的文档列表
        
        Returns:
            {
                "chapter_notes": {"章节名": "笔记内容", ...},
                "outline": "整体框架内容"
            }
        """
        # 1. 生成章节笔记
        chapter_notes = self.generate_chapter_notes(documents)
        
        # 2. 生成整体框架
        outline = self.generate_outline(chapter_notes)
        
        return {
            "chapter_notes": chapter_notes,
            "outline": outline
        }
    
    def save_to_markdown(self, result: Dict, output_path: str, book_title: str = "读书笔记"):
        """将生成的笔记保存为 md 文档
        
        Args:
            result: generate() 返回的结果
            output_path: 输出文件路径
            book_title: 书籍标题
        """
        md_content = f"# {book_title} - 读书笔记\n\n"
        
        # 整体框架
        md_content += "## 整体框架\n\n"
        md_content += result["outline"] + "\n\n"
        
        # 章节笔记
        md_content += "---\n\n"
        md_content += "## 章节笔记\n\n"
        
        for chapter, note in result["chapter_notes"].items():
            md_content += f"### {chapter}\n\n"
            md_content += note + "\n\n"
        
        # 写入文件
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"笔记已保存到: {output_path}")
    

if __name__ == '__main__':
    rag = RAGPipeline()
    vs = rag.load_vectorstore('./vectorstore')
    all_data = vs.get()

    docs = [Document(page_content=c, metadata=m) for c, m in zip(all_data['documents'], all_data['metadatas'])]

    generator = NoteGenerator()
    result = generator.generate(docs)

    # 保存为 md
    generator.save_to_markdown(result, './output/巴比伦最富有的人_笔记.md', '巴比伦最富有的人')


