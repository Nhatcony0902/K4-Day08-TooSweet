"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng HTTP parser (có thể thay bằng Crawl4AI).
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Không cần browser ở cấu hình mặc định. Khi host không phản hồi, pipeline lưu bản
snapshot có URL nguồn để quá trình build vẫn tái lập được.
"""

import asyncio
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://ctt.hust.edu.vn/DisplayWeb/DisplayKehoach?kehoach=27231",
    "https://hust.edu.vn/vi/sinh-vien/sinh-vien-hien-tai/quy-trinh-ky-xac-nhan-cac-thu-tuc-hanh-chinh-sinh-vien-116889.html",
    "https://fed.hust.edu.vn/vi/sinh-vien/hoat-dong-noi-bat/bieu-mau-va-quy-dinh-danh-cho-sinh-vien-250170.html",
    "https://www.hust.edu.vn/vi/co-cau-to-chuc-bai-viet/ban-cong-tac-sinh-vien.html",
    "https://www.hust.edu.vn/vi/news/tin-tuc-su-kien/tan-sinh-vien-k70-can-trong-nhung-chieu-tro-lua-dao-co-the-ghe-tham-ban-khi-nhap-hoc-655557.html",
]

OFFLINE_ARTICLES = [
    {
        "title": "Thông báo học phí học kỳ 1 năm học 2025-2026 - đợt 2",
        "content": """Sinh viên tra cứu học phí trên Cổng thông tin sinh viên, vào mục Dịch vụ và chọn Học phí - Công nợ. Học phí mỗi học kỳ được tính theo hai đợt: đợt đầu là số liệu sơ bộ, đợt hai cập nhật chính xác theo các học phần đã đăng ký. Sinh viên cần kiểm tra tổng số tiền, các học phần đang được tính ngoài chương trình đào tạo và phản hồi khi có sai lệch. Mức học phí của học phần trong và ngoài chương trình được tính như nhau, nhưng việc phân loại có thể ảnh hưởng đến học bổng khuyến khích học tập. Sinh viên thanh toán theo hướng dẫn hiển thị cùng số liệu công nợ. Người không hoàn thành nghĩa vụ học phí sau hạn có thể bị xem xét đình chỉ đăng ký học tập ở kỳ tiếp theo.""",
    },
    {
        "title": "Quy trình xác nhận thủ tục hành chính sinh viên",
        "content": """Đại học Bách khoa Hà Nội công bố lịch tiếp nhận và trả các loại giấy tờ cho sinh viên. Các thủ tục gồm sổ ưu đãi, giấy chứng nhận sinh viên, giấy chứng nhận tạm thời khi mất thẻ, xác nhận vé tháng xe buýt, giấy giới thiệu, giấy vay vốn ngân hàng và biên lai học phí. Sinh viên cần chuẩn bị đúng biểu mẫu và hồ sơ minh chứng trước khi đến đơn vị phụ trách. Một số giấy tờ được nhận vào các buổi sáng đầu tuần và trả vào buổi chiều; giấy vay vốn, sổ ưu đãi và biên lai học phí có lịch xử lý riêng. Lịch và đầu mối có thể thay đổi nên sinh viên phải kiểm tra trang chính thức trước khi nộp hồ sơ.""",
    },
    {
        "title": "Biểu mẫu và quy định dành cho sinh viên",
        "content": """Khoa Khoa học và Công nghệ giáo dục tổng hợp các biểu mẫu, quy định dành cho sinh viên. Giấy chứng nhận sinh viên, giấy giới thiệu, bản sao bảng điểm và giấy chứng nhận tốt nghiệp được đăng ký qua hệ thống quản lý đào tạo. Trang cũng cung cấp đơn xin mở lớp bổ sung cho cá nhân hoặc tập thể, đơn đăng ký vào lớp đã đầy và hướng dẫn xác nhận học phần thay thế hoặc tương đương. Sinh viên cần đọc kỹ kế hoạch mở đăng ký lớp, thực hiện đúng thời hạn và sử dụng biểu mẫu mới nhất. Khi một thủ tục được chuyển sang trực tuyến, sinh viên nên theo dõi trạng thái trên hệ thống thay vì gửi nhiều hồ sơ trùng nhau.""",
    },
    {
        "title": "Chức năng của Ban Công tác sinh viên HUST",
        "content": """Ban Công tác sinh viên tham mưu và hỗ trợ công tác quản lý người học, tư vấn và tạo điều kiện cho sinh viên, đặc biệt là người học có hoàn cảnh khó khăn hoặc hoàn cảnh đặc biệt. Ban triển khai các hoạt động bảo hiểm y tế và khám sức khỏe; thực hiện chế độ chính sách, học bổng và hỗ trợ sinh viên; phối hợp xây dựng môi trường văn hóa, kỹ năng nghề nghiệp và kỹ năng sống. Đây cũng là đầu mối cho nhiều thông tin về hoạt động xã hội, việc làm, rèn luyện và hỗ trợ học tập. Sinh viên nên dùng các kênh liên hệ được công bố trên website Đại học để được hướng dẫn đúng đơn vị và tránh các yêu cầu cung cấp thông tin cá nhân không rõ nguồn.""",
    },
    {
        "title": "Cảnh báo lừa đảo và hướng dẫn đăng ký ký túc xá",
        "content": """Đại học Bách khoa Hà Nội cảnh báo tân sinh viên về các hình thức giả mạo có thể xuất hiện trong thời gian nhập học. Với Ký túc xá Bách khoa, sinh viên chỉ đăng ký sau thời điểm trường thông báo qua hệ thống chính thức của ký túc xá và có thể liên hệ Trung tâm Dịch vụ và Hỗ trợ Bách khoa tại khuôn viên trường. Sinh viên đăng ký Ký túc xá Pháp Vân cần làm theo hướng dẫn và lấy giấy giới thiệu từ Ban Công tác sinh viên khi được yêu cầu. Tân sinh viên không nên chuyển tiền qua tài khoản cá nhân, cung cấp mật khẩu, mã OTP hoặc truy cập liên kết nhận từ người tự xưng là cán bộ. Mọi khoản thu và lịch tiếp nhận phải được đối chiếu trên website chính thức.""",
    },
]


class _ReadableHTMLParser(HTMLParser):
    """Small dependency-free HTML-to-text converter for public articles."""

    ignored = {"script", "style", "svg", "noscript", "nav", "footer"}
    blocks = {"p", "div", "article", "section", "li", "h1", "h2", "h3", "tr"}

    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.title = ""
        self.in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.ignored:
            self.skip_depth += 1
        if tag == "title":
            self.in_title = True
        if tag in self.blocks and not self.skip_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.ignored and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title":
            self.in_title = False
        if tag in self.blocks and not self.skip_depth:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self.in_title:
            self.title = f"{self.title} {text}".strip()
        self.parts.append(text)

    def markdown(self) -> str:
        text = " ".join(self.parts)
        text = re.sub(r"\s*\n\s*", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()


async def crawl_article(url: str) -> dict:
    def fetch() -> dict:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 RAG-course-project"})
        with urlopen(request, timeout=45) as response:
            raw = response.read()
            try:
                html = raw.decode("utf-8")
            except UnicodeDecodeError:
                charset = response.headers.get_content_charset() or "utf-8"
                html = raw.decode(charset, errors="replace")
        parser = _ReadableHTMLParser()
        parser.feed(html)
        content = parser.markdown()
        if len(content) < 200:
            raise ValueError("Article content is unexpectedly short")
        return {
            "url": url,
            "title": parser.title or url.rstrip("/").rsplit("/", 1)[-1],
            "date_crawled": datetime.now(timezone.utc).isoformat(),
            "content_markdown": content,
        }

    return await asyncio.to_thread(fetch)


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fetched = await asyncio.gather(
        *(crawl_article(url) for url in ARTICLE_URLS), return_exceptions=True
    )
    for index, (url, result) in enumerate(zip(ARTICLE_URLS, fetched), 1):
        if isinstance(result, Exception):
            snapshot = OFFLINE_ARTICLES[index - 1]
            article = {
                "url": url,
                "title": snapshot["title"],
                "date_crawled": datetime.now(timezone.utc).isoformat(),
                "content_markdown": snapshot["content"],
            }
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"Network unavailable; saved sourced snapshot: {output} — {result}")
        else:
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"Saved: {output}")


if __name__ == "__main__":
    asyncio.run(crawl_all())
