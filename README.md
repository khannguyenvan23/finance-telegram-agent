# Finance Telegram Agent

Bot Telegram quản lí tài chính cá nhân bằng Python. Bot đọc tin nhắn tự nhiên, dùng OpenAI để phân tích giao dịch, lưu dữ liệu vào Google Sheets và trả lời các lệnh báo cáo.

## Tính Năng

- Ghi khoản chi hoặc khoản thu từ tin nhắn tự nhiên, ví dụ `cafe 10k`, `lương freelance 3tr`.
- Lưu dữ liệu vào Google Sheets.
- Xem tổng chi, tổng thu, tổng kết và lịch sử giao dịch.
- Lọc chi tiêu theo danh mục.
- Xuất báo cáo ra file `financial_report.txt`.
- Trả lời câu hỏi dựa trên tài liệu nội bộ bằng RAG qua cú pháp `hỏi: ...`.
- Chặn input/output không hợp lệ bằng guardrails.
- Yêu cầu xác nhận với giao dịch lớn bằng human-in-the-loop.
- Ghi log hoạt động vào `bot.log`.

## Cài Đặt

Mở PowerShell trong thư mục project:

```powershell
cd C:\Users\Admins\Documents\khan
```

Cài thư viện:

```powershell
pip install -r requirements.txt
```

## Cấu Hình Biến Môi Trường

Tạo file `.env` từ file mẫu:

```powershell
copy .env.example .env
```

Mở file `.env` và điền key thật:

```env
OPENAI_API_KEY=your_openai_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GOOGLE_SHEET_NAME=Quan ly tai chinh
GOOGLE_WORKSHEET_NAME=Giao dịch
```

Không đưa file `.env` lên GitHub.

## Cấu Hình Google Sheets

Đặt file Google service account JSON trong thư mục project và đổi tên thành:

```text
google-service-account.json
```

Khi deploy lên cloud, không upload file JSON. Thay vào đó, copy toàn bộ nội dung file JSON thành một dòng và lưu vào biến môi trường:

```env
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
```

Trong Google Sheet, tạo hàng tiêu đề đầu tiên:

```text
time | loai | noi_dung | so_tien | danh_muc | ghi_chu
```

Mở file `google-service-account.json`, tìm trường:

```json
"client_email": "..."
```

Copy email đó, mở Google Sheet, bấm **Chia sẻ** và cấp quyền **Editor** cho email service account.

## Chạy Bot

Chạy lệnh:

```powershell
python finance_agent.py
```

Nếu chạy đúng, terminal sẽ báo bot đang chạy. Sau đó mở Telegram và nhắn tin cho bot.

Trên Windows, có thể chạy nhanh bằng file:

```text
run_bot.bat
```

## Deploy 24/7

Bot này chạy dạng worker/background process bằng polling Telegram. Start command:

```text
python finance_agent.py
```

Nếu nền tảng deploy hỗ trợ `Procfile`, project đã có:

```text
worker: python finance_agent.py
```

Khi deploy, cần thêm các biến môi trường:

```text
OPENAI_API_KEY
TELEGRAM_BOT_TOKEN
GOOGLE_SHEET_NAME
GOOGLE_WORKSHEET_NAME
GOOGLE_SERVICE_ACCOUNT_JSON
```

Không đưa `.env` hoặc `google-service-account.json` lên server qua Git.

## Ví Dụ Tin Nhắn

```text
cafe 10k
grab 70k
lương freelance 3tr
mua áo 250k ghi chú sale
hỏi: làm sao xem lịch sử?
hỏi: lỗi SpreadsheetNotFound sửa sao?
```

## Lệnh Telegram

```text
/start   - xem hướng dẫn
/help    - xem hướng dẫn
/tongchi - xem tổng chi
/tongthu - xem tổng thu
/tongket - xem tổng kết tài chính
/lichsu  - xem lịch sử giao dịch gần nhất
/baocao  - xuất báo cáo
```

Bot cũng hỗ trợ một số lệnh dạng văn bản:

```text
tổng chi
tổng thu
tổng kết
lịch sử
danh mục Ăn uống
xuất báo cáo
xóa dữ liệu
```

## RAG Nội Bộ

Bot dùng file `knowledge.txt` làm tài liệu nội bộ. Khi người dùng nhắn:

```text
hỏi: làm sao xem lịch sử?
```

Bot sẽ:

```text
1. Tạo embedding cho câu hỏi
2. Tìm đoạn liên quan trong knowledge.txt
3. Đưa đoạn đó cho LLM
4. Trả lời dựa trên tài liệu
```

Ví dụ nội dung trong `knowledge.txt`:

```text
Bot hỗ trợ lệnh /lichsu để xem lịch sử giao dịch gần nhất.
Lỗi SpreadsheetNotFound thường do chưa chia sẻ Google Sheet cho service account.
```

## Guardrails Và Human-in-the-loop

Bot có input guardrails:

```text
- Chặn tin nhắn trống
- Chặn tin nhắn quá dài
- Chặn số tiền âm
- Chặn prompt injection cơ bản
```

Bot có output guardrails trước khi lưu giao dịch:

```text
- Kiểm tra intent
- Kiểm tra loại giao dịch expense/income
- Kiểm tra số tiền lớn hơn 0
- Chặn số tiền quá lớn
- Kiểm tra danh mục hợp lệ
```

Với giao dịch lớn từ `500.000 VND`, bot sẽ không lưu ngay mà hỏi xác nhận:

```text
Trả lời YES để lưu hoặc NO để hủy.
```

## Logging

Bot ghi log vào:

```text
bot.log
```

Log gồm:

```text
- Tin nhắn người dùng
- Số lần gọi OpenAI
- Giao dịch đã lưu
- Câu trả lời của bot
- Thời gian xử lý
- Lỗi nếu có
```

Không commit `bot.log` lên GitHub vì log có thể chứa dữ liệu cá nhân.

## Lỗi Thường Gặp

`Missing credentials`

- Kiểm tra file `.env` đã có `OPENAI_API_KEY`.
- Kiểm tra code đã gọi `load_dotenv()`.

`Thiếu TELEGRAM_BOT_TOKEN`

- Kiểm tra file `.env` đã có `TELEGRAM_BOT_TOKEN`.

`FileNotFoundError: google-service-account.json`

- Đặt file JSON đúng thư mục project.
- Tên file phải đúng là `google-service-account.json`.

`SpreadsheetNotFound`

- Chia sẻ Google Sheet cho email `client_email` trong file JSON.
- Kiểm tra tên Google Sheet trong code.

`WorksheetNotFound`

- Kiểm tra tên tab sheet trong code, ví dụ `Giao dịch`.

`Google Drive API has not been used or is disabled`

- Bật Google Drive API trong Google Cloud Console.
- Bật cả Google Sheets API và Google Drive API.

## Bảo Mật

Không commit các file nhạy cảm:

```text
.env
google-service-account.json
```

Hai file này đã được thêm vào `.gitignore`.

## Cấu Trúc Dữ Liệu

Mỗi giao dịch gồm:

```text
time      - thời gian ghi giao dịch
loai      - expense hoặc income
noi_dung  - nội dung giao dịch
so_tien   - số tiền VND
danh_muc  - danh mục
ghi_chu   - ghi chú nếu có
```

Danh mục thường dùng:

```text
Ăn uống
Di chuyển
Mua sắm
Hóa đơn
Giải trí
Sức khỏe
Thu nhập
Khác
```
