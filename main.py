if __name__ == '__main__':

    from rag import RAGPipeline
    from note_generator import NoteGenerator

    rag = RAGPipeline()
    vs = rag.load_vectorstore('./vectorstore')
    all_data = vs.get()

    from langchain_core.documents import Document
    docs = [Document(page_content=c, metadata=m) for c, m in zip(all_data['documents'], all_data['metadatas'])]

    print(f'总 chunks: {len(docs)}')

    generator = NoteGenerator()
    result = generator.generate(docs)

    print('=== 章节笔记 ===')
    for ch, note in result['chapter_notes'].items():
        print(f'{ch}: {note}')

    print()
    print('=== 整体框架 ===')
    print(result['outline'])
