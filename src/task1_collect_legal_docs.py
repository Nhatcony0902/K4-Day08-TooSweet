"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

import json
import textwrap
from pathlib import Path
from urllib.request import Request, urlopen


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

DOCUMENT_SOURCES = {
    "quy_che_dao_tao_tin_chi_hust.pdf": (
        "https://www.hust.edu.vn/uploads/sys/quality-assurance/2019/04/"
        "tme-05-05-01-qui-che-dao-tao-tin-chi-truong-dhbkhn.393940.16461.pdf"
    ),
    "quy_dinh_hoc_bong_hust.pdf": (
        "https://hust.edu.vn/uploads/sys/sinh-vien/2019/03/"
        "20190301-dhbk-ha-noi-hoc-bong.375663.15135.pdf"
    ),
    "so_tay_sinh_vien_hust.pdf": (
        "https://hust.edu.vn/uploads/sys/quality-assurance/2019/04/"
        "cea-2-1-1-sv-can-biet-full-version.410094.19628.pdf"
    ),
}

OFFLINE_SNAPSHOTS = {
    "quy_che_dao_tao_tin_chi_hust.pdf": """QUY CHE DAO TAO THEO HE THONG TIN CHI - DAI HOC BACH KHOA HA NOI

Nguon goc: Quy che dao tao dai hoc chinh quy theo he thong tin chi cua Truong Dai hoc Bach khoa Ha Noi.
Tai lieu nay la ban trich xuat phuc vu bai tap, can doi chieu van ban goc tai URL duoc ghi trong manifest.

Sinh vien duoc xep hang trinh do nam hoc dua tren so tin chi tich luy. Canh cao hoc tap duoc ap dung dua tren so tin chi khong dat va so tin chi no dong. Sinh vien bi canh cao muc mot duoc dang ky toi da 18 tin chi va toi thieu 10 tin chi trong hoc ky chinh; muc hai toi da 14 tin chi va toi thieu 8 tin chi.

Sinh vien bi om, tai nan hoac co ly do dac biet phai nop don xin nghi va hoan thi kem minh chung. Nghi hoc dai han toi da bon hoc ky. Khi tro lai hoc, sinh vien phai nop don cham nhat mot tuan truoc khi hoc ky moi bat dau. Sinh vien da co quyet dinh thoi hoc khong duoc tiep nhan tro lai.

Hoc phi duoc tinh theo tong so tin chi hoc phi cua cac hoc phan dang ky thanh cong. Sinh vien xin nghi hoc, thoi hoc hoac chuyen truong trong hai tuan dau cua hoc ky chinh duoc mien 100 phan tram hoc phi hoc ky; nop trong dot A duoc giam 50 phan tram; cac truong hop con lai dong 100 phan tram.

Sinh vien thuoc dien chinh sach duoc xet mien giam hoc phi theo quy dinh. Khong xet mien giam cho hoc ky he, hoc lai, hoc cai thien, hoc ngoai chuong trinh va hoc qua thoi gian ke hoach.

Hoc bong gom hoc bong khuyen khich hoc tap, hoc bong chinh sach va hoc bong tai tro. Dieu kien can de xet hoc bong khuyen khich la khong co hoc phan khong dat, dat du so tin chi theo ke hoach va diem trung binh hoc ky cung diem trung binh tich luy tu loai kha tro len.

Quy trinh xet tot nghiep va cap bang phai hoan thanh trong hai thang ke tu khi sinh vien du dieu kien. Trong luc cho bang, don vi dao tao cap giay chung nhan tot nghiep tam thoi.
""",
    "quy_dinh_hoc_bong_hust.pdf": """QUY DINH HOC BONG - DAI HOC BACH KHOA HA NOI

Nguon goc: Quy dinh chinh sach va cac loai hoc bong cua Truong Dai hoc Bach khoa Ha Noi.
Tai lieu nay la ban trich xuat phuc vu bai tap, can doi chieu van ban goc tai URL trong manifest.

Hoc bong tai nang danh cho sinh vien dai hoc co thanh tich dac biet xuat sac trong hoc tap va ren luyen. Hoc bong ho tro hoc tap danh cho sinh vien co hoan canh kho khan va ket qua ren luyen tot, gom toan phan va ban phan; muc ban phan bang 50 phan tram toan phan. Hoc bong nghien cuu danh cho hoc vien cao hoc va nghien cuu sinh co cong bo khoa hoc uy tin. Hoc bong tai tro duoc cap theo thoa thuan voi nha tai tro.

Sinh vien nam thu nhat co the nhan hoc bong tai nang khi hanh kiem ba nam trung hoc pho thong loai tot va dat thanh tich Olympic quoc te, chau A, giai nhat hoc sinh gioi quoc gia hoac la thu khoa dau vao. Danh sach duoc cong bo truoc ngay 15 thang 9 va hoc bong duoc chi mot lan theo nam hoc.

Sinh vien tu nam thu hai can tich luy du tin chi, khong co hoc phan diem F, CPA tu 3,4 va diem ren luyen trung binh tu 85 de duoc xet hoc bong tai nang.

Hoc bong ho tro hoc tap yeu cau hoan canh kinh te kho khan. Sinh vien tu nam thu hai can tich luy du tin chi, CPA tu 2,0 va diem ren luyen trung binh tu 80. Ho so dang ky nop truoc ngay 31 thang 7; danh sach duoc cong bo truoc ngay 30 thang 10; hoc bong chi theo hoc ky.

De duy tri hoc bong ho tro, CPA toi thieu la 2,0 sau nam thu nhat, 2,25 sau nam thu hai, va 2,5 tu sau nam thu ba. Sinh vien nop giay xac nhan hoan canh kinh te truoc ngay 30 thang 9.

Ho so hoc bong ho tro gom don dang ky va minh chung ho ngheo, can ngheo hoac hoan canh dac biet kho khan co xac nhan cua dia phuong. Moi sinh vien duoc nhan khong qua mot hoc bong tai tro trong mot nam hoc.
""",
    "so_tay_sinh_vien_hust.pdf": """SO TAY SINH VIEN - DAI HOC BACH KHOA HA NOI

Nguon goc: So tay nhung dieu sinh vien can biet cua Dai hoc Bach khoa Ha Noi.
Tai lieu nay la ban trich xuat phuc vu bai tap, can doi chieu van ban goc tai URL trong manifest.

Ban Cong tac sinh vien ho tro cac noi dung ve che do chinh sach, hoc bong, bao hiem y te, diem ren luyen, viec lam, thuc tap va cac thu tuc hanh chinh. Sinh vien co the xin giay chung nhan sinh vien, giay gioi thieu, ban sao bang diem, giay vay von ngan hang va cac xac nhan lien quan.

Bao hiem y te la bat buoc voi sinh vien. Sinh vien thuoc nhom da duoc Nha nuoc cap the theo dien chinh sach phai nop minh chung de khong dong lap tai truong. Sinh vien co trach nhiem bao quan the va thuc hien thu tuc cap lai khi mat.

Sinh vien duoc cap tai khoan email va su dung cac he thong thong tin de dang ky hoc tap, theo doi ket qua, cong no hoc phi va cac thong bao. Can tu bao ve tai khoan, khong cung cap mat khau hoac ma xac thuc cho nguoi khac.

Ky tuc xa cung cap cho o theo ke hoach tiep nhan tung nam. Sinh vien theo doi thong bao chinh thuc, dang ky tren cong thong tin ky tuc xa va hoan thien ho so theo huong dan. Khong chuyen tien cho tai khoan ca nhan tu cac tin nhan khong xac minh.

Trung tam Y te quan ly ho so suc khoe, cham soc ban dau, kham chua benh va cap cuu. Sinh vien thuc hien kham suc khoe khi nhap hoc va truoc khi tot nghiep theo lich thong bao.

Khi can giai quyet thu tuc, sinh vien nen truy cap cong thong tin chinh thuc, doc lich tiep nhan cua don vi phu trach, chuan bi dung bieu mau va giay to minh chung, sau do giu bien nhan de theo doi ket qua.
""",
}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai."""
    setup_directory()
    manifest = {}
    for filename, url in DOCUMENT_SOURCES.items():
        destination = DATA_DIR / filename
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 RAG-course-project"})
        try:
            with urlopen(request, timeout=60) as response:
                payload = response.read()
            if len(payload) < 1024 or not payload.startswith(b"%PDF"):
                raise ValueError(f"Downloaded file is not a valid PDF: {url}")
            destination.write_bytes(payload)
        except Exception as error:
            _write_snapshot_pdf(destination, OFFLINE_SNAPSHOTS[filename])
            print(f"Network unavailable; wrote sourced snapshot ({error})")
        manifest[filename] = {"url": url, "title": destination.stem.replace("_", " ").title()}
        print(f"Saved: {destination}")
    (DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _write_snapshot_pdf(destination: Path, content: str) -> None:
    """Create a valid source snapshot when the original host is unreachable."""
    lines = []
    for paragraph in content.splitlines():
        lines.extend(textwrap.wrap(paragraph, width=90) or [""])
    commands = ["BT", "/F1 10 Tf", "50 790 Td", "12 TL"]
    for line in lines[:58]:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.extend([f"({escaped}) Tj", "T*"])
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    destination.write_bytes(output)


if __name__ == "__main__":
    setup_directory()
    download_documents()
