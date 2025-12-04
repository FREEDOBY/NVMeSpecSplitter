"""표 내용 추출 테스트"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import fitz

def test_table_content(pdf_path: str, page_num: int = 0):
    """특정 페이지에서 표 내용 추출"""
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    print(f"=== 페이지 {page_num + 1} 표 내용 ===")

    tables = list(page.find_tables(strategy="text"))
    print(f"감지된 표: {len(tables)}개\n")

    for i, table in enumerate(tables):
        print(f"--- 표 {i+1} ---")
        print(f"위치: {table.bbox}")
        print(f"크기: {table.row_count} 행 x {table.col_count} 열")

        data = table.extract()
        if data:
            print("\n내용:")
            for row_idx, row in enumerate(data[:10]):  # 처음 10행만
                print(f"  [{row_idx}] {row}")
            if len(data) > 10:
                print(f"  ... (총 {len(data)}행)")
        print()

    doc.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python test_table_content.py <PDF경로> [페이지번호]")
    else:
        pdf_path = sys.argv[1]
        page_num = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 0
        test_table_content(pdf_path, page_num)
