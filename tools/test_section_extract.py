"""섹션 추출 테스트"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.pdf_reader import PDFReader
from core.md_converter import MarkdownConverter

def test_section_extract(pdf_path: str, section_title: str):
    """특정 섹션 추출 테스트"""
    with PDFReader(pdf_path) as reader:
        sections = reader.get_sections()

        # 섹션 찾기
        target = None
        for section in sections:
            if section_title.lower() in section.title.lower():
                target = section
                break

        if not target:
            print(f"섹션 '{section_title}'을 찾을 수 없습니다.")
            print("\n사용 가능한 섹션:")
            for s in sections[:20]:
                print(f"  [{s.level}] {s.title}")
            return

        print(f"=== 섹션: {target.title} ===")
        print(f"페이지: {target.start_page + 1} ~ {target.end_page + 1}")
        print(f"Y좌표: {target.start_y} ~ {target.end_y}")

        # 텍스트 추출
        text = reader.extract_section_text(target)
        print(f"\n[텍스트] ({len(text)} 문자)")
        print(text[:500] + "..." if len(text) > 500 else text)

        # 표 추출
        tables = reader.extract_section_tables(target)
        print(f"\n[표] {len(tables)}개 감지")

        converter = MarkdownConverter()
        for i, table in enumerate(tables):
            print(f"\n--- 표 {i+1} ---")
            md_table = converter.table_to_markdown(table)
            # 처음 10줄만 출력
            lines = md_table.split('\n')
            for line in lines[:12]:
                print(line)
            if len(lines) > 12:
                print(f"... ({len(lines)}줄)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python test_section_extract.py <PDF경로> <섹션제목>")
        print("예: python test_section_extract.py spec.pdf \"5 Admin Command Set\"")
    else:
        test_section_extract(sys.argv[1], sys.argv[2])
