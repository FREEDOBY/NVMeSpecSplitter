"""표 상세 추출 테스트"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import fitz

def test_table_detailed(pdf_path: str, page_num: int = 0):
    """특정 페이지에서 표 상세 추출"""
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    print(f"=== 페이지 {page_num + 1} 표 상세 분석 ===")
    print(f"페이지 크기: {page.rect.width} x {page.rect.height}")

    # 기본 전략
    print("\n[1] 기본 전략 (lines):")
    tables1 = list(page.find_tables())
    print(f"  감지: {len(tables1)}개")
    for t in tables1:
        print(f"    - {t.row_count}x{t.col_count} at {t.bbox}")

    # 텍스트 전략
    print("\n[2] 텍스트 전략:")
    tables2 = list(page.find_tables(strategy="text"))
    print(f"  감지: {len(tables2)}개")
    for t in tables2:
        print(f"    - {t.row_count}x{t.col_count} at {t.bbox}")

    # 가장 좋은 표 선택
    if tables1:
        print("\n[기본 전략 표 내용]")
        data = tables1[0].extract()
        for i, row in enumerate(data[:15]):
            # 빈 셀 제거하고 출력
            cleaned = [c for c in row if c and c.strip()]
            if cleaned:
                print(f"  [{i}] {cleaned}")
    elif tables2:
        print("\n[텍스트 전략 표 내용]")
        data = tables2[0].extract()
        for i, row in enumerate(data[:15]):
            cleaned = [c for c in row if c and c.strip()]
            if cleaned:
                print(f"  [{i}] {cleaned}")

    # 표 pandas로 변환 시도
    print("\n\n[3] pandas DataFrame 변환:]")
    try:
        if tables1:
            df = tables1[0].to_pandas()
            print(df.head(10).to_string())
        elif tables2:
            df = tables2[0].to_pandas()
            print(df.head(10).to_string())
    except Exception as e:
        print(f"  오류: {e}")

    doc.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python test_table_detailed.py <PDF경로> [페이지번호]")
    else:
        pdf_path = sys.argv[1]
        page_num = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 0
        test_table_detailed(pdf_path, page_num)
