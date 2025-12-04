"""PDF 읽기 및 섹션 파싱 모듈"""
import fitz  # PyMuPDF
from dataclasses import dataclass
from typing import Optional


@dataclass
class Section:
    """PDF 섹션 정보"""
    title: str
    level: int
    start_page: int
    end_page: int
    start_y: float = 0.0  # 시작 페이지 내 Y좌표
    end_y: float = float('inf')  # 끝 페이지 내 Y좌표

    def __str__(self):
        indent = "  " * (self.level - 1)
        return f"{indent}{self.title} (p.{self.start_page + 1}-{self.end_page + 1})"


class PDFReader:
    """PDF 파일 읽기 및 섹션 추출"""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc: Optional[fitz.Document] = None

    def open(self):
        """PDF 파일 열기"""
        self.doc = fitz.open(self.pdf_path)

    def close(self):
        """PDF 파일 닫기"""
        if self.doc:
            self.doc.close()
            self.doc = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def page_count(self) -> int:
        """전체 페이지 수"""
        return self.doc.page_count if self.doc else 0

    def _get_toc_with_position(self) -> list:
        """북마크 목록을 Y좌표 정보와 함께 반환"""
        if not self.doc:
            return []

        # get_toc(simple=False)는 상세 정보 포함
        # [[level, title, page, dest], ...] 형태
        toc = self.doc.get_toc(simple=False)

        result = []
        for item in toc:
            level = item[0]
            title = item[1]
            page = item[2] - 1  # 0-indexed

            # dest 정보에서 Y좌표 추출
            y_pos = 0.0
            if len(item) > 3 and item[3]:
                dest = item[3]
                # dest가 dict인 경우 (링크 대상 정보)
                if isinstance(dest, dict) and 'to' in dest:
                    to = dest['to']
                    if to and len(to) >= 2:
                        y_pos = to.y if hasattr(to, 'y') else (to[1] if len(to) > 1 else 0.0)
                # dest가 fitz.Point인 경우
                elif hasattr(dest, 'y'):
                    y_pos = dest.y

            result.append({
                'level': level,
                'title': title,
                'page': page,
                'y': y_pos
            })

        return result

    def get_sections(self) -> list[Section]:
        """PDF 북마크에서 섹션 목록 추출"""
        if not self.doc:
            return []

        toc = self._get_toc_with_position()

        if not toc:
            # 북마크가 없으면 전체를 하나의 섹션으로
            return [Section(
                title="전체 문서",
                level=1,
                start_page=0,
                end_page=self.page_count - 1,
                start_y=0.0,
                end_y=float('inf')
            )]

        sections = []
        for i, item in enumerate(toc):
            level = item['level']
            title = item['title']
            start_page = item['page']
            start_y = item['y']

            # 끝 위치 계산: 다음 섹션 시작 위치 또는 문서 끝
            if i + 1 < len(toc):
                next_item = toc[i + 1]
                next_page = next_item['page']
                next_y = next_item['y']

                if next_page == start_page:
                    # 같은 페이지 내에서 끝남
                    end_page = start_page
                    end_y = next_y
                else:
                    # 다른 페이지에서 끝남
                    end_page = next_page
                    end_y = next_y
            else:
                end_page = self.page_count - 1
                end_y = float('inf')

            sections.append(Section(
                title=title.strip(),
                level=level,
                start_page=start_page,
                end_page=end_page,
                start_y=start_y,
                end_y=end_y
            ))

        return sections

    def extract_text(self, start_page: int, end_page: int,
                     start_y: float = 0.0, end_y: float = float('inf')) -> str:
        """지정된 페이지/좌표 범위의 텍스트 추출"""
        if not self.doc:
            return ""

        text_parts = []
        for page_num in range(start_page, end_page + 1):
            if 0 <= page_num < self.page_count:
                page = self.doc[page_num]
                page_height = page.rect.height

                # 클리핑 영역 계산
                if page_num == start_page and page_num == end_page:
                    # 시작과 끝이 같은 페이지
                    clip_top = start_y
                    clip_bottom = end_y if end_y != float('inf') else page_height
                elif page_num == start_page:
                    # 시작 페이지: start_y부터 페이지 끝까지
                    clip_top = start_y
                    clip_bottom = page_height
                elif page_num == end_page:
                    # 끝 페이지: 페이지 시작부터 end_y까지
                    clip_top = 0
                    clip_bottom = end_y if end_y != float('inf') else page_height
                else:
                    # 중간 페이지: 전체
                    clip_top = 0
                    clip_bottom = page_height

                # 클리핑 영역으로 텍스트 추출
                clip_rect = fitz.Rect(0, clip_top, page.rect.width, clip_bottom)
                text = page.get_text(clip=clip_rect)
                if text.strip():
                    text_parts.append(text)

        return "\n".join(text_parts)

    def extract_section_text(self, section: Section) -> str:
        """섹션의 텍스트 추출"""
        return self.extract_text(
            section.start_page,
            section.end_page,
            section.start_y,
            section.end_y
        )

    def extract_tables(self, start_page: int, end_page: int,
                       start_y: float = 0.0, end_y: float = float('inf')) -> list[list[list[str]]]:
        """지정된 페이지/좌표 범위의 표 추출"""
        if not self.doc:
            return []

        all_tables = []
        for page_num in range(start_page, end_page + 1):
            if 0 <= page_num < self.page_count:
                page = self.doc[page_num]
                page_height = page.rect.height
                tables = page.find_tables()

                for table in tables:
                    # 표의 위치 확인
                    table_rect = table.bbox
                    table_top = table_rect[1]  # y0
                    table_bottom = table_rect[3]  # y1

                    # 현재 페이지에서의 유효 범위 계산
                    if page_num == start_page and page_num == end_page:
                        valid_top = start_y
                        valid_bottom = end_y if end_y != float('inf') else page_height
                    elif page_num == start_page:
                        valid_top = start_y
                        valid_bottom = page_height
                    elif page_num == end_page:
                        valid_top = 0
                        valid_bottom = end_y if end_y != float('inf') else page_height
                    else:
                        valid_top = 0
                        valid_bottom = page_height

                    # 표가 유효 범위 내에 있는지 확인
                    if table_top >= valid_top and table_bottom <= valid_bottom:
                        table_data = table.extract()
                        if table_data:
                            all_tables.append(table_data)

        return all_tables

    def extract_section_tables(self, section: Section) -> list[list[list[str]]]:
        """섹션의 표 추출"""
        return self.extract_tables(
            section.start_page,
            section.end_page,
            section.start_y,
            section.end_y
        )
