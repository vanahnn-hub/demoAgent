# HỆ THỐNG AI AGENT ĐÁNH GIÁ HIỆU QUẢ CHƯƠNG TRÌNH BÁN HÀNG (CÔNG TY GIA HÒA)

## 1. Bối cảnh & Bài toán Doanh nghiệp
Công ty **Gia Hòa** kinh doanh đồ dùng gia đình qua kênh cửa hàng và trực tuyến. Trong tháng, công ty triển khai **4 chương trình bán hàng** (`CT01`, `CT02`, `CT03`, `CT04`) với cơ chế ưu đãi khác nhau:
- **Vấn đề thực tế:**
  1. Một đơn hàng có thể tiếp xúc với nhiều chương trình (ví dụ: áp dụng đồng thời Flash Sale và Voucher), nhưng báo cáo của từng chương trình lại nhận 100% doanh thu của đơn đó (**trùng lặp doanh thu / double-counting**).
  2. **Hàng trả sau chương trình** thường bị bỏ sót, không trừ khỏi doanh thu và không hoàn nhập giá vốn.
  3. **Chi phí chung** (Marketing, vận hành) được phân bổ không nhất quán.
- **Mục tiêu của AI Agent:** Tự động tiếp nhận mọi cấu trúc tệp dữ liệu, tự động làm sạch & phân loại, chia đúng doanh thu cho đơn dùng nhiều mã, đối soát hàng hoàn, phân bổ chi phí nhất quán, tính toán tiền lãi thực tế & tỷ suất sinh lời (ROI) và đưa ra đề xuất hành động rõ ràng (**Nên tiếp tục & mở rộng**, **Nên điều chỉnh lại mức ưu đãi**, hoặc **Nên dừng để tiết kiệm ngân sách**).

---

## 2. Quy trình Dẫn dắt 5 Bước Tuần Tự (Step-by-Step Wizard)

Hệ thống được thiết kế theo quy trình 5 bước độc lập, giao diện tối giản với ngôn ngữ đời thường, dễ hiểu cho người làm kinh doanh:

| Bước | Tên Bước | Trọng tâm hiển thị & Xử lý |
| :--- | :--- | :--- |
| **Bước 1** | **Tải dữ liệu bán hàng** | Hỗ trợ nạp **1 tệp Excel/CSV gộp chung** hoặc nhiều tệp rời, dán liên kết Google Sheets. Tự động đọc hiểu ngữ nghĩa cột (*Fuzzy Alias Mapping*), không ép buộc 5 bảng cố định. |
| **Bước 2** | **AI tự sắp xếp & làm sạch** | Tự động xóa dòng rỗng, khử ký tự tiền tệ bẩn, chuẩn hóa ngày tháng. **Ma trận Auto-Healing & Capping:** Tự động sửa dữ liệu bẩn, gộp dòng trùng lặp 100%, giới hạn hoàn trả $\le$ 100% đơn gốc, và hiển thị thẻ tóm tắt minh bạch kèm nút xem các dòng đã tự sửa. |
| **Bước 3** | **Chia đúng doanh thu & lãi** | Tách đơn tự nhiên vs đơn ưu đãi, chia đúng doanh thu cho đơn nhiều mã theo 4 phương pháp, đối soát hàng hoàn & hoàn nhập giá vốn kho, phân bổ chi phí chung và tính P&L tiền lãi thực tế. |
| **Bước 4** | **Xem trước & Góp ý** | **Cơ chế Feedback 2 nhánh trực tiếp:** <br/>• **Chưa ưng ý (Cần sửa lại):** Gõ góp ý bằng tiếng Việt hoặc bấm nút điều chỉnh nhanh (chia đều doanh thu, bớt giảm giá CT02, cắt chi phí CT04...) để AI tính toán lại ngay. <br/>• **Đã ưng ý (Đồng ý):** Xác nhận phê duyệt và chuyển sang bước tiếp theo. |
| **Bước 5** | **Kết quả & Đề xuất** | Bảng P&L chính thức 4 chương trình, phân loại 3 màu trực quan (🟢 Tiếp tục, 🟡 Điều chỉnh, 🔴 Dừng), biểu đồ động trực quan, xuất file Excel tiếng Việt chi tiết và in báo cáo chuẩn PDF. |

---

## 3. Ngôn ngữ Thân thiện & Trải nghiệm Người dùng (Plain-Language UX)

- **Bảng màu giao diện:** Tông màu **Pastel Blue & Cream** hiện đại, thanh lịch (`#E0F1FC`, `#A6D0F0`, `#BBE4F6`, `#92C3E1`, `#FBF8E7`) kết hợp chữ xanh than đậm (`#0F2942`), tạo cảm giác nhẹ nhàng, chuyên nghiệp.
- **Thẻ nổi 3D bồng bềnh (`animate-floating`):** Giao diện mở đầu tối giản, sang trọng, hiển thị thẻ báo cáo nổi thời gian thực.
- **Xóa bỏ thuật ngữ kỹ thuật khó hiểu:** Mọi chỉ số đều dùng từ ngữ thuần Việt:
  - *Schema $\rightarrow$ Tự động nhận diện & kiểm tra bảng*
  - *Multi-touch Attribution $\rightarrow$ Chia đúng doanh thu cho đơn dùng nhiều mã*
  - *Gross Revenue / Net Sales $\rightarrow$ Tổng tiền bán ban đầu / Doanh thu thực nhận*
  - *COGS $\rightarrow$ Giá vốn nhập hàng*
  - *Contribution Margin $\rightarrow$ Tiền lãi thực tế sau khi trừ hết chi phí*
  - *ROI $\rightarrow$ Tỷ suất sinh lời (Bỏ 1 đồng vốn thu về bao nhiêu đồng lãi)*

---

## 4. Tích hợp Trợ lý Trò chuyện AI (Gemini Live)
- Đã tích hợp khóa API Vertex AI / Gemini vào hệ thống:
  - Tự động nạp ngữ cảnh kinh doanh P&L hiện tại vào prompt.
  - Trợ lý AI trả lời súc tích, bằng tiếng Việt đời thường, giải thích cặn kẽ vì sao CT01 nên mở rộng và vì sao CT02 bị lỗ.

---

## 5. Hướng dẫn Khởi chạy Hệ thống

Web server đã được cài đặt và đang chạy tại localhost:

```bash
# Chạy máy chủ WEBrick trên macOS/Linux (Port 8080)
/usr/bin/ruby --disable-gems server.rb 8080
```

Truy cập trình duyệt tại: **http://localhost:8080**
