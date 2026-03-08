#!/usr/bin/env python3
"""
微信读书笔记获取工具
"""

import argparse
import json
import os
import sys
from pathlib import Path

from weread_api import WeReadAPI, WeReadParser, WeReadExporter, BookNotes, Book, load_cookies_from_file
import config


def get_all_books_notes(api: WeReadAPI, books: list[dict], limit: int = None) -> list[BookNotes]:
    """获取所有书籍的笔记"""
    results = []
    
    for i, book_info in enumerate(books):
        if limit and i >= limit:
            break
            
        book_id = book_info.get('bookId')
        title = book_info.get('title', '未知标题')
        
        print(f"\n[{i+1}] 正在处理: {title} ({book_id})")
        
        try:
            # 获取书籍详情
            detail = api.get_book_detail(book_id)
            book = WeReadParser.parse_book(detail)
            print(f"   作者: {book.author}")
            
            # 获取章节
            print("   获取章节...")
            chapters_data = api.get_chapters(book_id)
            chapters = WeReadParser.parse_chapters(chapters_data, book_id)
            
            # 获取划线
            print("   获取划线...")
            bookmarks_data = api.get_bookmarks(book_id)
            highlights = WeReadParser.parse_highlights(bookmarks_data)
            print(f"   找到 {len(highlights)} 条划线")
            
            # 获取笔记
            print("   获取笔记...")
            reviews_data = api.get_reviews(book_id, mine=1)
            reviews = WeReadParser.parse_reviews(reviews_data)
            print(f"   找到 {len(reviews)} 条笔记")
            
            notes = BookNotes(
                book=book,
                chapters=chapters,
                highlights=highlights,
                reviews=reviews,
            )
            
            results.append(notes)
            
        except Exception as e:
            print(f"   ❌ 获取失败: {e}")
            continue
    
    return results


def generate_highlights():
    """生成书籍划线笔记 markdown 文件"""
    parser = argparse.ArgumentParser(description="微信读书笔记获取工具")
    parser.add_argument('--cookie-file', type=str, default=config.COOKIE_FILE, help='Cookie 文件路径')
    parser.add_argument('--cookie', type=str, default=config.WEREAD_COOKIE, help='Cookie 字符串')
    parser.add_argument('--output', type=str, default=config.OUTPUT_DIR, help='输出目录')
    parser.add_argument('--limit', type=int, default=config.DEFAULT_LIMIT, help='限制处理的书籍数量')
    parser.add_argument('--book-id', type=str, help='只获取指定书籍的笔记')
    parser.add_argument('--list-only', action='store_true', help='只列出书籍，不下载笔记')
    
    args = parser.parse_args()
    
    # 获取 cookie (优先使用命令行参数，否则用配置文件的)
    cookies = {}
    if args.cookie:
        for part in args.cookie.split(';'):
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                cookies[key.strip()] = value.strip()
    elif args.cookie_file and args.cookie_file != config.COOKIE_FILE:
        cookies = load_cookies_from_file(args.cookie_file)
    else:
        # 使用配置文件中的默认值
        if config.WEREAD_COOKIE:
            for part in config.WEREAD_COOKIE.split(';'):
                part = part.strip()
                if '=' in part:
                    key, value = part.split('=', 1)
                    cookies[key.strip()] = value.strip()
        elif config.COOKIE_FILE:
            cookies = load_cookies_from_file(config.COOKIE_FILE)
    
    if not cookies:
        print("错误: Cookie 不能为空")
        sys.exit(1)
    
    # 初始化 API
    api = WeReadAPI(cookies)
    
    try:
        # 获取书籍列表
        print("获取书架书籍列表...")
        books = api.get_notebooks()
        print(f"共找到 {len(books)} 本书")
        
        # 列出书籍
        print("\n书籍列表:")
        print("-" * 60)
        for i, book in enumerate(books):
            note_count = book.get('noteCount', 0)
            review_count = book.get('reviewCount', 0)
            print(f"{i+1}. {book.get('title', '未知')} - {book.get('author', '未知')}")
            print(f"   划线: {note_count}, 笔记: {review_count}")
        
        if args.list_only:
            return
            
        # 获取笔记
        if args.book_id:
            # 只获取指定书籍
            books = [b for b in books if b.get('bookId') == args.book_id]
            if not books:
                print(f"未找到书籍: {args.book_id}")
                sys.exit(1)
        
        results = get_all_books_notes(api, books, args.limit)
        
        # 导出
        print("\n导出 Markdown 文件...")
        output_dir = args.output
        
        exported_files = []
        for notes in results:
            try:
                file_path = WeReadExporter.export_to_file(notes, output_dir)
                exported_files.append(file_path)
                print(f"✅ 已导出: {file_path}")
            except Exception as e:
                print(f"❌ 导出失败: {e}")
        
        print(f"\n完成! 共导出 {len(exported_files)} 个文件到 {output_dir}")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    generate_highlights()
