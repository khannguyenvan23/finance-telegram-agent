from dotenv import load_dotenv
from openai import OpenAI
import json
import csv
from datetime import datetime
from pathlib import Path
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
import gspread
load_dotenv()
client = OpenAI()

CSV_FILE = Path("transactions.csv")
REPORT_FILE = Path("financial_report.txt")
GOOGLE_CREDENTIALS_FILE = "google-service-account.json"
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Quan ly tai chinh")
GOOGLE_WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "Giao dịch")


def get_google_worksheet():
    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if credentials_json:
        credentials_info = json.loads(credentials_json)
        sheets_client = gspread.service_account_from_dict(credentials_info)
    else:
        sheets_client = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)

    spreadsheet = sheets_client.open(GOOGLE_SHEET_NAME)
    return spreadsheet.worksheet(GOOGLE_WORKSHEET_NAME)
# def test_google_sheet_write():
#     worksheet = get_google_worksheet()
#     worksheet.append_row([
#         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#         "expense",
#         "test cafe",
#         10000,
#         "Ăn uống",
#         "test",
#     ])
#     print("Đã ghi test vào Google Sheets.")
def ensure_csv_file():
    if CSV_FILE.exists():
        return

    with CSV_FILE.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow([
            "time",
            "loai",
            "noi_dung",
            "so_tien",
            "danh_muc",
            "ghi_chu",
        ])
def reset_google_sheet():
    worksheet = get_google_worksheet()
    worksheet.clear()
    worksheet.append_row([
        "time",
        "loai",
        "noi_dung",
        "so_tien",
        "danh_muc",
        "ghi_chu",
    ])
def save_transaction(data):
    worksheet = get_google_worksheet()

    worksheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data["loai"],
        data["noi_dung"],
        data["so_tien"],
        data["danh_muc"],
        data.get("ghi_chu", ""),
    ])
def load_transactions():
    worksheet = get_google_worksheet()
    rows = worksheet.get_all_records()

    transactions = []

    for row in rows:
        amount = row.get("so_tien", 0)

        transactions.append({
            "time": row.get("time", ""),
            "loai": row.get("loai", ""),
            "noi_dung": row.get("noi_dung", ""),
            "so_tien": int(float(amount or 0)),
            "danh_muc": row.get("danh_muc", ""),
            "ghi_chu": row.get("ghi_chu", ""),
        })

    return transactions
def get_total_expense():
    transactions = load_transactions()
    total = 0

    for transaction in transactions:
        if transaction["loai"] == "expense":
            total += transaction["so_tien"]

    return total     
def get_total_income():
    transactions = load_transactions()
    total = 0

    for transaction in transactions:
        if transaction["loai"] == "income":
            total += transaction["so_tien"]

    return total
def get_financial_summary():
    total_income = get_total_income()
    total_expense = get_total_expense()
    balance = total_income - total_expense

    return (
        "Tổng kết tài chính:\n"
        f"- Tổng thu: {format_vnd(total_income)}\n"
        f"- Tổng chi: {format_vnd(total_expense)}\n"
        f"- Số dư: {format_vnd(balance)}"
    )
def get_category_summary(category):
    transactions = load_transactions()
    total = 0

    for transaction in transactions:
        same_category = normalize_text(transaction["danh_muc"]) == normalize_text(category)
        is_expense = transaction["loai"] == "expense"

        if same_category and is_expense:
            total += transaction["so_tien"]

    return (
        f"Danh mục {category}:\n"
        f"- Tổng chi: {format_vnd(total)}"
    )
def get_recent_transactions(limit=5):
    transactions = load_transactions()

    if not transactions:
        return "Chưa có giao dịch nào."

    recent_transactions = transactions[-limit:]

    lines = []

    for transaction in recent_transactions:
        icon = "Chi" if transaction["loai"] == "expense" else "Thu"

        line = (
            f'{icon}: {transaction["noi_dung"]} - '
            f'{format_vnd(transaction["so_tien"])} - '
            f'{transaction["danh_muc"]}'
        )

        if transaction.get("ghi_chu"):
            line += f' - ghi chú: {transaction["ghi_chu"]}'

        lines.append(line)

    return "5 giao dịch gần nhất:\n" + "\n".join(lines)
def export_report():
    summary = get_financial_summary()
    recent = get_recent_transactions()

    content = (
        "BÁO CÁO TÀI CHÍNH\n"
        "=================\n\n"
        f"{summary}\n\n"
        f"{recent}\n"
    )

    REPORT_FILE.write_text(content, encoding="utf-8-sig")

    return f"Đã xuất báo cáo ra file: {REPORT_FILE}"
def format_vnd(amount):
    return f"{amount:,}".replace(",", ".") + " VND"
def normalize_text(text):
    return text.strip().lower()
def clean_json_text(text):
    text = text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "", 1).strip()

    if text.startswith("```"):
        text = text.replace("```", "", 1).strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text
def parse_message(message):
    prompt = f"""
Bạn là agent quản lí tài chính cá nhân.

Hãy phân tích tin nhắn người dùng và trả về JSON hợp lệ.

Tin nhắn:
{message}

Quy tắc:
- Nếu tin nhắn có số tiền và là khoản chi/thu, intent = "add_transaction"
- Nếu là khoản chi, loai = "expense"
- Nếu là khoản thu, loai = "income"
- "k" nghĩa là nhân 1000, ví dụ 10k = 10000
- "tr" hoặc "triệu" nghĩa là nhân 1000000
- Số tiền phải là number
- Danh mục chỉ được chọn trong:
  Ăn uống, Di chuyển, Mua sắm, Hóa đơn, Giải trí, Sức khỏe, Thu nhập, Khác
- Nếu thiếu số tiền, intent = "unknown"
- Chỉ trả JSON, không giải thích
- Nếu tin nhắn có số tiền và là khoản chi/thu, intent = "add_transaction"
Format:
{{
  "intent": "",
  "loai": "",
  "noi_dung": "",
  "so_tien": 0,
  "danh_muc": "",
  "ghi_chu": "",
  "reply": ""
}}
"""

    response = client.responses.create(
    model="gpt-4.1-mini",
    input=prompt,
    )

    raw_text = clean_json_text(response.output_text)

    if not raw_text:
        return {
            "intent": "unknown",
            "loai": "",
            "noi_dung": "",
            "so_tien": 0,
            "danh_muc": "",
            "ghi_chu": "",
            "reply": "AI không trả về dữ liệu. Bạn thử nhập lại nhé.",
        }

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        print("DEBUG RAW:", raw_text)

        return {
            "intent": "unknown",
            "loai": "",
            "noi_dung": "",
            "so_tien": 0,
            "danh_muc": "",
            "ghi_chu": "",
            "reply": "AI trả về sai định dạng. Bạn thử nhập lại nhé.",
        }
def handle_user_message(message):
    message = message.strip()
    command = message.lower().strip()

    if command in ["tổng chi", "tong chi", "tổng chi tiêu", "tong chi tieu"]:
        total = get_total_expense()
        return f"Tổng chi hiện tại là {format_vnd(total)}"

    if command in ["tổng thu", "tong thu", "tổng thu nhập", "tong thu nhap"]:
        total = get_total_income()
        return f"Tổng thu hiện tại là {format_vnd(total)}"

    if command in ["tổng kết", "tong ket", "báo cáo", "bao cao"]:
        return get_financial_summary()

    if command.startswith("danh mục "):
        category = message.replace("danh mục ", "", 1).strip()
        return get_category_summary(category)

    if command in ["lịch sử", "lich su", "lịch sử giao dịch", "lich su giao dich"]:
        return get_recent_transactions()

    if command in ["xuất báo cáo", "xuat bao cao", "export report"]:
        return export_report()

    data = parse_message(message)
    intent = data.get("intent", "").strip().lower()

    if intent == "add_transaction":
        save_transaction(data)
        return data.get("reply") or f"Đã lưu {data['noi_dung']} {format_vnd(data['so_tien'])}"

    return data.get("reply", "Mình chưa hiểu hoặc bạn thiếu số tiền.")
def get_help_text():
    return (
        "Bot quản lí tài chính cá nhân\n\n"
        "Ghi giao dịch:\n"
        "- cafe 10k\n"
        "- grab 70k\n"
        "- lương freelance 3tr\n\n"
        "Lệnh:\n"
        "/tongchi - xem tổng chi\n"
        "/tongthu - xem tổng thu\n"
        "/tongket - xem tổng kết\n"
        "/lichsu - xem lịch sử giao dịch\n"
        "/baocao - xuất báo cáo\n"
        "/help - xem hướng dẫn"
    )
async def telegram_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    try:
        reply = handle_user_message(user_message)
    except Exception as error:
        reply = f"Có lỗi xảy ra: {error}"

    await update.message.reply_text(reply)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_help_text())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_help_text())


async def tongchi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Tổng chi hiện tại là {format_vnd(get_total_expense())}")


async def tongthu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Tổng thu hiện tại là {format_vnd(get_total_income())}")


async def tongket_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_financial_summary())


async def lichsu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_recent_transactions())


async def baocao_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(export_report())    
def run_telegram_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        print("Thiếu TELEGRAM_BOT_TOKEN. Hãy set biến môi trường trước.")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tongchi", tongchi_command))
    app.add_handler(CommandHandler("tongthu", tongthu_command))
    app.add_handler(CommandHandler("tongket", tongket_command))
    app.add_handler(CommandHandler("lichsu", lichsu_command))
    app.add_handler(CommandHandler("baocao", baocao_command))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_message_handler)
    )

    print("Telegram bot đang chạy. Nhắn tin cho bot để test.")
    app.run_polling()    
# while True:
#     message = input("Bạn: ").strip()
    
#     if message.lower() in ["exit", "quit", "thoát"]:
#         break
#     command = message.lower().strip()
#     if command in ["tổng chi", "tong chi", "tổng chi tiêu"]:
#         total = get_total_expense()
#         print("Bot:", f"Tổng chi hiện tại là {format_vnd(total)}")
#         continue

#     if command in ["tổng thu", "tong thu", "tổng thu nhập"]:
#         total = get_total_income()
#         print("Bot:", f"Tổng thu hiện tại là {format_vnd(total)}")
#         continue
#     if command in ["tổng kết", "tong ket", "báo cáo", "bao cao"]:
#         print("Bot:", get_financial_summary())
#         continue
#     if command.startswith("danh mục "):
#         category = message.replace("danh mục ", "", 1).strip()
#         print("Bot:", get_category_summary(category))
#         continue
#     if command in ["lịch sử", "lich su", "lịch sử giao dịch", "lich su giao dich"]:
#         print("Bot:", get_recent_transactions())
#         continue
#     if command in ["xuất báo cáo", "xuat bao cao", "export report"]:
#         print("Bot:", export_report())
#         continue
#     if command in ["xóa dữ liệu", "xoa du lieu", "reset"]:
#         confirm = input("Bạn chắc muốn xóa toàn bộ dữ liệu? nhập YES để xác nhận: ")

#         if confirm == "YES":
#             reset_csv_file()
#             print("Bot: Đã xóa toàn bộ dữ liệu.")
#         else:
#             print("Bot: Đã hủy xóa dữ liệu.")

#         continue
#     data = parse_message(message)
    

#     intent = data.get("intent", "").strip().lower()

#     if intent == "add_transaction":
#         save_transaction(data)
#         reply = data.get("reply") or f"Đã lưu {data['noi_dung']} {format_vnd(data['so_tien'])}"
#         print("Bot:", reply)
#     else:
#         print("Bot: Mình chưa hiểu hoặc bạn thiếu số tiền.")

if __name__ == "__main__":
    run_telegram_bot()

