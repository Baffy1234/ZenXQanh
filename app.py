# callback_server.py - Deploy lên Render.com
# Nhận callback từ thesieure.com/shopbanthe.com + gửi thông báo Telegram

from flask import Flask, request, jsonify
import requests
import json
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# ==================== CẤU HÌNH ====================
BOT_TOKEN = "8849892826:AAFONG9lU4K39U2-OWCV0EyAFgHq0HZvB4E"
ADMIN_ID = "8588555065"

# ==================== DATABASE ====================
def init_db():
    conn = sqlite3.connect("cards.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            user_id INTEGER,
            username TEXT,
            card_type TEXT,
            card_value INTEGER,
            card_code TEXT,
            card_serial TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            processed_at TEXT,
            note TEXT,
            amount_received INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def db_query(query, params=()):
    conn = sqlite3.connect("cards.db")
    c = conn.cursor()
    c.execute(query, params)
    result = c.fetchall()
    conn.close()
    return result

def db_execute(query, params=()):
    conn = sqlite3.connect("cards.db")
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

# ==================== GỬI TIN NHẮN TELEGRAM ====================
def send_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Lỗi gửi tin: {e}")

# ==================== NHẬN CALLBACK ====================
@app.route("/callback", methods=["GET", "POST"])
def callback():
    """Nhận callback từ thesieure.com/shopbanthe.com"""
    
    if request.method == "POST":
        data = request.get_json()
        if not data:
            data = request.form.to_dict()
    else:
        data = request.args.to_dict()
    
    print(f"[CALLBACK] Dữ liệu: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    order_id = data.get("order_id") or data.get("trans_id") or data.get("id") or ""
    status = data.get("status") or data.get("result") or ""
    message = data.get("message") or data.get("msg") or ""
    amount = int(data.get("amount") or data.get("value") or 0)
    card_type = data.get("type") or data.get("card_type") or ""
    card_value = int(data.get("card_value") or data.get("amount") or 0)
    
    # Nếu không có order_id, tìm qua card_code/ serial
    if not order_id:
        code = data.get("code") or data.get("card_code") or ""
        serial = data.get("serial") or data.get("card_serial") or ""
        if code and serial:
            result = db_query("SELECT order_id FROM cards WHERE card_code = ? AND card_serial = ?", (code, serial))
            if result:
                order_id = result[0][0]
    
    if not order_id:
        send_telegram(ADMIN_ID, f"⚠️ Callback không có order_id: {data}")
        return jsonify({"status": "error", "message": "Missing order_id"}), 400
    
    # Cập nhật database
    db_execute("""
        UPDATE cards 
        SET status = ?, processed_at = ?, note = ?, amount_received = ?
        WHERE order_id = ?
    """, (status, datetime.now().isoformat(), message, amount, order_id))
    
    # Lấy thông tin user
    card_info = db_query("SELECT user_id, card_type, card_value FROM cards WHERE order_id = ?", (order_id,))
    
    if card_info and status in ["success", "1", "ok", "true"]:
        user_id = card_info[0][0]
        card_type = card_info[0][1]
        card_value = card_info[0][2]
        
        received_amount = amount if amount > 0 else int(card_value * 0.8)
        
        # Cộng tiền vào user
        db_execute("""
            INSERT INTO balances (user_id, balance, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?, updated_at = ?
        """, (user_id, received_amount, datetime.now().isoformat(), received_amount, datetime.now().isoformat()))
        
        # Lấy số dư mới
        bal = db_query("SELECT balance FROM balances WHERE user_id = ?", (user_id,))
        new_balance = bal[0][0] if bal else 0
        
        # Gửi thông báo cho user
        user_msg = f"""
✅ <b>NẠP THẺ THÀNH CÔNG!</b>

🎮 <b>Loại:</b> {card_type.upper()}
💵 <b>Mệnh giá:</b> {card_value:,}đ
💰 <b>Nhận được:</b> {received_amount:,}đ
📌 <b>Số dư mới:</b> {new_balance:,}đ

Cảm ơn bạn đã sử dụng dịch vụ! ❤️
"""
        send_telegram(user_id, user_msg)
        
        # Gửi thông báo cho admin
        admin_msg = f"""
✅ <b>THẺ ĐƯỢC DUYỆT</b>

🆔 <b>Mã đơn:</b> {order_id}
👤 <b>User:</b> {user_id}
📱 <b>Loại:</b> {card_type.upper()}
💵 <b>Mệnh giá:</b> {card_value:,}đ
💰 <b>User nhận:</b> {received_amount:,}đ
📌 <b>Số dư mới:</b> {new_balance:,}đ
"""
        send_telegram(ADMIN_ID, admin_msg)
        
    elif card_info:
        user_id = card_info[0][0]
        card_type = card_info[0][1]
        card_value = card_info[0][2]
        
        user_msg = f"""
❌ <b>NẠP THẺ THẤT BẠI!</b>

🎮 <b>Loại:</b> {card_type.upper()}
💵 <b>Mệnh giá:</b> {card_value:,}đ
📌 <b>Lý do:</b> {message}

Vui lòng kiểm tra lại thẻ hoặc liên hệ admin!
"""
        send_telegram(user_id, user_msg)
        
        admin_msg = f"""
❌ <b>THẺ THẤT BẠI</b>
🆔 {order_id} | User: {user_id} | {card_type.upper()} {card_value:,}đ
📌 Lý do: {message}
"""
        send_telegram(ADMIN_ID, admin_msg)
    
    return jsonify({"status": "success"}), 200

# ==================== TRANG CHỦ ====================
@app.route("/")
def index():
    return "✅ Callback server đang chạy! Callback URL: /callback"

# ==================== CHẠY ====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)