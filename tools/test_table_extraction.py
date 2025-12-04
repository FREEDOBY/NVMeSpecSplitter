"""표 추출 테스트 스크립트"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import fitz

def test_table_extraction(pdf_path: str, page_num: int = 0):
    """특정 페이지에서 표 추출 테스트"""
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    print(f"=== 페이지 {page_num + 1} 표 추출 테스트 ===")
    print(f"페이지 크기: {page.rect.width} x {page.rect.height}")

    # 방법 1: find_tables() 기본
    table_finder = page.find_tables()
    tables = list(table_finder)
    print(f"\n[방법 1] find_tables() 기본: {len(tables)}개 표 감지")

    for i, table in enumerate(tables):
        print(f"\n  표 {i+1}:")
        print(f"    위치: {table.bbox}")
        print(f"    행/열: {table.row_count} x {table.col_count}")
        data = table.extract()
        if data:
            print(f"    첫 행: {data[0][:3] if len(data[0]) >= 3 else data[0]}...")

    # 방법 2: find_tables() 전략 변경
    try:
        tables2 = list(page.find_tables(strategy="lines"))
        print(f"\n[방법 2] find_tables(strategy='lines'): {len(tables2)}개 표 감지")
    except Exception as e:
        print(f"\n[방법 2] 오류: {e}")

    try:
        tables3 = list(page.find_tables(strategy="text"))
        print(f"\n[방법 3] find_tables(strategy='text'): {len(tables3)}개 표 감지")
    except Exception as e:
        print(f"\n[방법 3] 오류: {e}")

    # 방법 4: 텍스트 블록 분석
    print(f"\n[방법 4] 텍스트 블록 분석:")
    blocks = page.get_text("dict")["blocks"]
    table_like_blocks = []

    for block in blocks:
        if block.get("type") == 0:  # 텍스트 블록
            lines = block.get("lines", [])
            if len(lines) >= 3:  # 여러 줄
                # 탭이나 많은 공백으로 구분된 데이터 확인
                for line in lines[:2]:
                    spans = line.get("spans", [])
                    if len(spans) >= 3:  # 여러 span이 있으면 표일 가능성
                        table_like_blocks.append(block)
                        break

    print(f"  표 유사 블록: {len(table_like_blocks)}개")

    doc.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python test_table_extraction.py <PDF경로> [페이지번호]")
        print("예: python test_table_extraction.py spec.pdf 141")
    else:
        pdf_path = sys.argv[1]
        page_num = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 0
        test_table_extraction(pdf_path, page_num)
