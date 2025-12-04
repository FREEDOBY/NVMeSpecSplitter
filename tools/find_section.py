"""섹션 찾기 스크립트"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import fitz

def find_section(pdf_path: str, keyword: str):
    """키워드로 섹션/페이지 찾기"""
    doc = fitz.open(pdf_path)

    # TOC에서 검색
    toc = doc.get_toc()
    print(f"=== '{keyword}' 검색 결과 ===\n")

    print("[북마크에서 검색]")
    for level, title, page in toc:
        if keyword.lower() in title.lower():
            indent = "  " * (level - 1)
            print(f"{indent}[p.{page}] {title}")

    # 텍스트에서 검색
    print(f"\n[본문에서 검색 (처음 5개)]")
    count = 0
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if keyword.lower() in text.lower():
            # 해당 줄 찾기
            for line in text.split('\n'):
                if keyword.lower() in line.lower():
                    print(f"  [p.{page_num + 1}] {line[:80]}...")
                    count += 1
                    if count >= 5:
                        break
            if count >= 5:
                break

    doc.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python find_section.py <PDF경로> <검색어>")
    else:
        find_section(sys.argv[1], sys.argv[2])
