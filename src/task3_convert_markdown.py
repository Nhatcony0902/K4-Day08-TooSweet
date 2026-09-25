"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX khi extra conversion đã cài.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cấu hình offline dùng source snapshot; cài `.[conversion]` để convert tài liệu gốc.
"""

import json
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs() -> None:
    try:
        from markitdown import MarkItDown
    except ImportError:
        MarkItDown = None
    from .task1_collect_legal_docs import OFFLINE_SNAPSHOTS

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = legal_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    converter = MarkItDown() if MarkItDown else None
    for path in sorted(legal_dir.iterdir()):
        if path.suffix.lower() not in {".pdf", ".doc", ".docx"}:
            continue
        info = manifest.get(path.name, {})
        title = info.get("title", path.stem.replace("_", " ").title())
        body = (
            converter.convert(str(path)).text_content.strip()
            if converter
            else OFFLINE_SNAPSHOTS.get(path.name, "").strip()
        )
        if len(body) < 200:
            raise ValueError(f"Conversion produced insufficient content: {path}")
        header = (
            f"---\ntitle: {title}\nsource: {path.name}\n"
            f"url: {info.get('url', '')}\ndoc_type: legal\n---\n\n"
        )
        destination = output_dir / f"{path.stem}.md"
        destination.write_text(header + body + "\n", encoding="utf-8")
        print(f"Saved: {destination}")


def convert_news_articles() -> None:
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    required = {"url", "title", "date_crawled", "content_markdown"}
    for path in sorted(news_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not required <= data.keys():
            raise ValueError(f"Missing news metadata: {path}")
        content = str(data["content_markdown"]).strip()
        if len(content) < 200:
            raise ValueError(f"Article content is too short: {path}")
        safe_title = str(data["title"]).replace("\n", " ").strip()
        header = (
            f"---\ntitle: {safe_title}\nsource: {path.name}\n"
            f"url: {data['url']}\ndoc_type: news\n"
            f"date_crawled: {data['date_crawled']}\n---\n\n"
        )
        destination = output_dir / f"{path.stem}.md"
        destination.write_text(header + content + "\n", encoding="utf-8")
        print(f"Saved: {destination}")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
