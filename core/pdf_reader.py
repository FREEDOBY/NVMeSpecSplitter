"""PDF 읽기 및 섹션 파싱 모듈"""
import fitz  # PyMuPDF
from dataclasses import dataclass, field
from typing import Optional

# 헤더/푸터 여백 상수 (pt)
HEADER_MARGIN = 50.0  # 상단 헤더 영역 제외
FOOTER_MARGIN = 50.0  # 하단 푸터 영역 제외


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


@dataclass
class MergedSection:
    """병합된 섹션 정보"""
    parent: Section
    children: list[Section] = field(default_factory=list)


def get_max_level(sections: list[Section]) -> int:
    """섹션 리스트에서 최대 레벨 반환"""
    if not sections:
        return 0
    return max(s.level for s in sections)


def merge_sections_by_level(sections: list[Section], split_level: Optional[int]) -> list[MergedSection]:
    """
    섹션을 지정된 레벨까지만 분리하고 나머지는 병합

    Args:
        sections: 전체 섹션 리스트
        split_level: 파일로 분리할 최대 레벨 (None이면 모든 레벨 개별 파일)

    Returns:
        병합된 섹션 리스트
    """
    if not sections:
        return []

    # split_level이 None이면 모든 섹션 개별 파일
    if split_level is None:
        return [MergedSection(parent=s, children=[]) for s in sections]

    result = []
    i = 0

    while i < len(sections):
        section = sections[i]

        # split_level 이하 레벨은 개별 파일로
        if section.level <= split_level:
            merged = MergedSection(parent=section, children=[])

            # 다음 섹션들 중 직접 하위이면서 split_level 초과인 것들만 children에 추가
            # 중간에 split_level 이하 섹션이 나오면 그 섹션이 새 파일이 되므로 중단
            j = i + 1
            while j < len(sections):
                next_section = sections[j]

                # 같은 레벨이거나 상위 레벨이면 중단
                if next_section.level <= section.level:
                    break

                # split_level 이하 레벨이면 새 파일이 되므로 중단
                # (이 섹션이 하위 섹션들을 가져감)
                if next_section.level <= split_level:
                    break

                # split_level 초과 레벨만 children에 추가
                merged.children.append(next_section)

                j += 1

            result.append(merged)

        i += 1

    return result


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

    def _get_table_rects(self, page, valid_top: float, valid_bottom: float) -> list:
        """페이지에서 유효 범위 내 표들의 영역(bbox) 반환"""
        table_rects = []
        tables = list(page.find_tables())
        for table in tables:
            table_rect = table.bbox
            table_top = table_rect[1]
            table_bottom = table_rect[3]
            # 표가 유효 범위 내에 있는지 확인
            if table_top >= valid_top and table_bottom <= valid_bottom:
                table_rects.append(fitz.Rect(table_rect))
        return table_rects

    def extract_text(self, start_page: int, end_page: int,
                     start_y: float = 0.0, end_y: float = float('inf'),
                     exclude_tables: bool = True) -> str:
        """지정된 페이지/좌표 범위의 텍스트 추출 (헤더/푸터 영역 및 표 영역 제외)

        Args:
            start_page: 시작 페이지 (0-indexed)
            end_page: 끝 페이지 (0-indexed)
            start_y: 시작 Y좌표
            end_y: 끝 Y좌표
            exclude_tables: True이면 표 영역의 텍스트 제외 (기본값: True)
        """
        if not self.doc:
            return ""

        text_parts = []
        for page_num in range(start_page, end_page + 1):
            if 0 <= page_num < self.page_count:
                page = self.doc[page_num]
                page_height = page.rect.height

                # 클리핑 영역 계산 (헤더/푸터 여백 적용)
                if page_num == start_page and page_num == end_page:
                    # 시작과 끝이 같은 페이지
                    clip_top = max(start_y, HEADER_MARGIN)
                    clip_bottom = min(end_y, page_height - FOOTER_MARGIN) if end_y != float('inf') else page_height - FOOTER_MARGIN
                elif page_num == start_page:
                    # 시작 페이지: start_y부터 페이지 끝까지 (푸터 제외)
                    clip_top = max(start_y, HEADER_MARGIN)
                    clip_bottom = page_height - FOOTER_MARGIN
                elif page_num == end_page:
                    # 끝 페이지: 헤더 제외하고 end_y까지
                    clip_top = HEADER_MARGIN
                    clip_bottom = min(end_y, page_height - FOOTER_MARGIN) if end_y != float('inf') else page_height - FOOTER_MARGIN
                else:
                    # 중간 페이지: 헤더/푸터 제외
                    clip_top = HEADER_MARGIN
                    clip_bottom = page_height - FOOTER_MARGIN

                # 표 영역 가져오기 (표 텍스트 제외 옵션이 켜진 경우)
                table_rects = []
                if exclude_tables:
                    table_rects = self._get_table_rects(page, clip_top, clip_bottom)

                # 텍스트 블록 단위로 추출하여 표 영역 제외
                clip_rect = fitz.Rect(0, clip_top, page.rect.width, clip_bottom)
                blocks = page.get_text("dict", clip=clip_rect)["blocks"]

                page_text_parts = []
                for block in blocks:
                    if block["type"] != 0:  # 텍스트 블록만 처리 (type 0)
                        continue

                    block_rect = fitz.Rect(block["bbox"])

                    # 표 영역과 겹치는지 확인
                    is_in_table = False
                    for table_rect in table_rects:
                        if block_rect.intersects(table_rect):
                            is_in_table = True
                            break

                    if not is_in_table:
                        # 블록 내 모든 라인의 텍스트 추출
                        for line in block.get("lines", []):
                            line_text = ""
                            for span in line.get("spans", []):
                                line_text += span.get("text", "")
                            if line_text.strip():
                                page_text_parts.append(line_text)

                if page_text_parts:
                    text_parts.append("\n".join(page_text_parts))

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
        """지정된 페이지/좌표 범위의 표 추출 (헤더/푸터 영역 제외)"""
        if not self.doc:
            return []

        all_tables = []
        for page_num in range(start_page, end_page + 1):
            if 0 <= page_num < self.page_count:
                page = self.doc[page_num]
                page_height = page.rect.height
                # 기본 전략으로 표 감지 (경계선 기반, 더 정확함)
                tables = list(page.find_tables())

                for table in tables:
                    # 표의 위치 확인
                    table_rect = table.bbox
                    table_top = table_rect[1]  # y0
                    table_bottom = table_rect[3]  # y1

                    # 현재 페이지에서의 유효 범위 계산 (헤더/푸터 여백 적용)
                    if page_num == start_page and page_num == end_page:
                        valid_top = max(start_y, HEADER_MARGIN)
                        valid_bottom = min(end_y, page_height - FOOTER_MARGIN) if end_y != float('inf') else page_height - FOOTER_MARGIN
                    elif page_num == start_page:
                        valid_top = max(start_y, HEADER_MARGIN)
                        valid_bottom = page_height - FOOTER_MARGIN
                    elif page_num == end_page:
                        valid_top = HEADER_MARGIN
                        valid_bottom = min(end_y, page_height - FOOTER_MARGIN) if end_y != float('inf') else page_height - FOOTER_MARGIN
                    else:
                        valid_top = HEADER_MARGIN
                        valid_bottom = page_height - FOOTER_MARGIN

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
