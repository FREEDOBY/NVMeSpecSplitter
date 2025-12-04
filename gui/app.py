"""PDF to Markdown Splitter GUI"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
from typing import Optional

from core.pdf_reader import PDFReader, Section, MergedSection, get_max_level, merge_sections_by_level
from core.md_converter import MarkdownConverter


class PDFSplitterApp:
    """PDF 분절 GUI 애플리케이션"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PDF to Markdown Splitter")
        self.root.geometry("700x650")
        self.root.resizable(True, True)

        self.pdf_path: Optional[str] = None
        self.sections: list[Section] = []
        self.section_vars: list[tk.BooleanVar] = []
        self.max_level: int = 0
        self.split_level_var: tk.StringVar = tk.StringVar(value="모든 레벨")

        self._setup_ui()

    def _setup_ui(self):
        """UI 구성"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # PDF 파일 선택
        file_frame = ttk.LabelFrame(main_frame, text="PDF 파일", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10))

        self.file_entry = ttk.Entry(file_frame)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        browse_btn = ttk.Button(file_frame, text="찾아보기", command=self._browse_pdf)
        browse_btn.pack(side=tk.RIGHT)

        # 섹션 목록
        section_frame = ttk.LabelFrame(main_frame, text="감지된 섹션", padding="5")
        section_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 스크롤바가 있는 캔버스
        canvas_frame = ttk.Frame(section_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)

        self.sections_inner = ttk.Frame(self.canvas)
        self.sections_inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.sections_inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 마우스 휠 스크롤
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # 전체 선택/해제 버튼
        btn_frame = ttk.Frame(section_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        select_all_btn = ttk.Button(btn_frame, text="전체 선택", command=self._select_all)
        select_all_btn.pack(side=tk.LEFT, padx=(0, 5))

        deselect_all_btn = ttk.Button(btn_frame, text="전체 해제", command=self._deselect_all)
        deselect_all_btn.pack(side=tk.LEFT)

        # 분리 레벨 선택
        level_frame = ttk.LabelFrame(main_frame, text="분리 레벨", padding="5")
        level_frame.pack(fill=tk.X, pady=(0, 10))

        level_label = ttk.Label(level_frame, text="파일 분리 기준 레벨:")
        level_label.pack(side=tk.LEFT, padx=(0, 5))

        self.level_combo = ttk.Combobox(
            level_frame,
            textvariable=self.split_level_var,
            state="readonly",
            width=15
        )
        self.level_combo['values'] = ["모든 레벨"]
        self.level_combo.pack(side=tk.LEFT)

        level_help = ttk.Label(
            level_frame,
            text="(선택한 레벨까지만 개별 파일로 분리)",
            foreground="gray"
        )
        level_help.pack(side=tk.LEFT, padx=(10, 0))

        # 출력 폴더
        output_frame = ttk.LabelFrame(main_frame, text="출력 폴더", padding="5")
        output_frame.pack(fill=tk.X, pady=(0, 10))

        self.output_entry = ttk.Entry(output_frame)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        output_btn = ttk.Button(output_frame, text="찾아보기", command=self._browse_output)
        output_btn.pack(side=tk.RIGHT)

        # 진행률
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X)

        # 변환 버튼
        self.convert_btn = ttk.Button(
            main_frame,
            text="변환 시작",
            command=self._start_conversion
        )
        self.convert_btn.pack(pady=(0, 10))

        # 상태 표시
        self.status_var = tk.StringVar(value="PDF 파일을 선택하세요")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack()

    def _on_mousewheel(self, event):
        """마우스 휠 스크롤 처리"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _browse_pdf(self):
        """PDF 파일 선택"""
        filepath = filedialog.askopenfilename(
            title="PDF 파일 선택",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filepath:
            self.pdf_path = filepath
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filepath)
            self._load_sections()

            # 출력 폴더 자동 설정
            if not self.output_entry.get():
                output_dir = Path(filepath).parent / "output"
                self.output_entry.delete(0, tk.END)
                self.output_entry.insert(0, str(output_dir))

    def _browse_output(self):
        """출력 폴더 선택"""
        dirpath = filedialog.askdirectory(title="출력 폴더 선택")
        if dirpath:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, dirpath)

    def _load_sections(self):
        """PDF에서 섹션 목록 로드"""
        if not self.pdf_path:
            return

        # 기존 섹션 체크박스 제거
        for widget in self.sections_inner.winfo_children():
            widget.destroy()
        self.section_vars.clear()

        try:
            with PDFReader(self.pdf_path) as reader:
                self.sections = reader.get_sections()

                for section in self.sections:
                    var = tk.BooleanVar(value=True)
                    self.section_vars.append(var)

                    # 들여쓰기 적용
                    indent = "    " * (section.level - 1)
                    text = f"{indent}{section.title} (p.{section.start_page + 1}-{section.end_page + 1})"

                    cb = ttk.Checkbutton(
                        self.sections_inner,
                        text=text,
                        variable=var
                    )
                    cb.pack(anchor=tk.W)

                # 최대 레벨 감지 및 콤보박스 업데이트
                self.max_level = get_max_level(self.sections)
                level_options = ["모든 레벨"] + [f"레벨 {i}" for i in range(1, self.max_level + 1)]
                self.level_combo['values'] = level_options
                self.split_level_var.set("모든 레벨")

            self.status_var.set(f"{len(self.sections)}개 섹션 감지됨 (최대 레벨: {self.max_level})")

        except Exception as e:
            messagebox.showerror("오류", f"PDF 로드 실패:\n{e}")
            self.status_var.set("PDF 로드 실패")

    def _select_all(self):
        """모든 섹션 선택"""
        for var in self.section_vars:
            var.set(True)

    def _deselect_all(self):
        """모든 섹션 선택 해제"""
        for var in self.section_vars:
            var.set(False)

    def _get_split_level(self) -> Optional[int]:
        """선택된 분리 레벨 반환"""
        level_str = self.split_level_var.get()
        if level_str == "모든 레벨":
            return None
        # "레벨 N" 형식에서 N 추출
        return int(level_str.split()[-1])

    def _start_conversion(self):
        """변환 시작"""
        if not self.pdf_path:
            messagebox.showwarning("경고", "PDF 파일을 선택하세요")
            return

        output_dir = self.output_entry.get()
        if not output_dir:
            messagebox.showwarning("경고", "출력 폴더를 선택하세요")
            return

        selected = [
            (i, section)
            for i, (section, var) in enumerate(zip(self.sections, self.section_vars))
            if var.get()
        ]

        if not selected:
            messagebox.showwarning("경고", "최소 하나의 섹션을 선택하세요")
            return

        # 출력 폴더 생성
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 분리 레벨 가져오기
        split_level = self._get_split_level()

        # 선택된 섹션들만 필터링
        selected_sections = [section for _, section in selected]

        # 섹션 병합
        merged_sections = merge_sections_by_level(selected_sections, split_level)

        # UI 비활성화
        self.convert_btn.configure(state='disabled')
        self.progress['value'] = 0
        # 프로그레스: 추출 단계 + 저장 단계
        total_steps = len(selected_sections) + len(merged_sections)
        self.progress['maximum'] = total_steps

        # 백그라운드 스레드에서 변환 실행
        thread = threading.Thread(
            target=self._do_conversion_merged,
            args=(merged_sections, selected_sections, output_path)
        )
        thread.start()

    def _do_conversion(self, selected: list[tuple[int, Section]], output_path: Path):
        """변환 실행 (백그라운드 스레드) - 레거시"""
        try:
            converter = MarkdownConverter()

            with PDFReader(self.pdf_path) as reader:
                for idx, (original_idx, section) in enumerate(selected, 1):
                    self.root.after(0, lambda s=section: self.status_var.set(
                        f"변환 중: {s.title}"
                    ))

                    # 텍스트와 표 추출 (Y좌표 기반 정확한 추출)
                    text = reader.extract_section_text(section)
                    tables = reader.extract_section_tables(section)

                    # 마크다운으로 저장
                    converter.save_section(output_path, section, text, tables, idx)

                    # 진행률 업데이트
                    self.root.after(0, lambda v=idx: self._update_progress(v))

            self.root.after(0, lambda: self._conversion_complete(output_path))

        except Exception as e:
            self.root.after(0, lambda: self._conversion_error(str(e)))

    def _do_conversion_merged(self, merged_sections: list, selected_sections: list[Section], output_path: Path):
        """병합된 섹션 변환 실행 (백그라운드 스레드)"""
        try:
            converter = MarkdownConverter()
            total_extract = len(selected_sections)
            total_save = len(merged_sections)
            print(f"[DEBUG] 변환 시작: {total_extract}개 섹션 추출, {total_save}개 파일 저장 예정")

            with PDFReader(self.pdf_path) as reader:
                # 1단계: 모든 선택된 섹션의 콘텐츠를 추출
                section_contents = {}

                for idx, section in enumerate(selected_sections, 1):
                    # 상태 업데이트
                    self.root.after(0, lambda s=section.title, i=idx, t=total_extract:
                        self.status_var.set(f"추출 중 ({i}/{t}): {s}"))
                    print(f"[DEBUG] 추출 중 ({idx}/{total_extract}): {section.title}")

                    text = reader.extract_section_text(section)
                    tables = reader.extract_section_tables(section)
                    section_contents[section.title] = (text, tables)

                    # 프로그레스 업데이트
                    self.root.after(0, lambda v=idx: self._update_progress(v))

                print(f"[DEBUG] 추출 완료, 저장 시작...")

                # 2단계: 병합된 섹션별로 저장
                for idx, merged in enumerate(merged_sections, 1):
                    # 상태 업데이트
                    self.root.after(0, lambda s=merged.parent.title, i=idx, t=total_save:
                        self.status_var.set(f"저장 중 ({i}/{t}): {s}"))
                    print(f"[DEBUG] 저장 중 ({idx}/{total_save}): {merged.parent.title}")

                    converter.save_merged_section(output_path, merged, section_contents, idx)

                    # 프로그레스 업데이트 (추출 수 + 현재 저장 인덱스)
                    self.root.after(0, lambda v=total_extract + idx: self._update_progress(v))

            print(f"[DEBUG] 변환 완료!")
            self.root.after(0, lambda: self._conversion_complete(output_path))

        except Exception as e:
            print(f"[DEBUG] 오류 발생: {e}")
            self.root.after(0, lambda: self._conversion_error(str(e)))

    def _update_progress(self, value: int):
        """진행률 업데이트"""
        self.progress['value'] = value

    def _conversion_complete(self, output_path: Path):
        """변환 완료"""
        self.convert_btn.configure(state='normal')
        self.status_var.set("변환 완료!")
        messagebox.showinfo("완료", f"변환이 완료되었습니다.\n\n출력 폴더:\n{output_path}")

    def _conversion_error(self, error: str):
        """변환 오류"""
        self.convert_btn.configure(state='normal')
        self.status_var.set("변환 실패")
        messagebox.showerror("오류", f"변환 실패:\n{error}")


def run():
    """애플리케이션 실행"""
    root = tk.Tk()
    app = PDFSplitterApp(root)
    root.mainloop()
