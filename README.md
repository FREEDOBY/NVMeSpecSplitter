# NVMe Spec Splitter

PDF 문서를 북마크 기반으로 섹션별 마크다운 파일로 분절하는 도구입니다.

## 기능

- PDF 북마크(목차) 기반 섹션 자동 감지
- Y좌표 기반 정밀 텍스트 추출 (같은 페이지 내 여러 섹션 정확히 분리)
- 표 자동 추출 및 마크다운 변환
- 빈 열 자동 제거로 깔끔한 표 출력
- GUI 인터페이스 제공

## 설치

```bash
pip install -r requirements.txt
```

## 사용법

```bash
python main.py
```

1. PDF 파일 선택
2. 변환할 섹션 선택 (전체 선택/해제 가능)
3. 출력 폴더 지정
4. "변환 시작" 클릭

## 요구사항

- Python 3.10+
- PyMuPDF >= 1.23.0

## 라이선스

MIT License
