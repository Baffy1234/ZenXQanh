# app.py - Callback server cho thesieure.com / shopbanthe.com
# Deploy lên Render.com

from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)

# ==================== CẤU HÌNH ====================
BOT_TOKEN = "8849892826:AAFONG9lU4K39U2-OWCV0EyAFgHq0HZvB4E"
ADMIN_ID = "8588555065"

# ==================== GỬI TIN NHẮN TELEGRAM ====================
def send_telegram(chat_id, message):
    """Gửi tin nhắn qua Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Lỗi gửi tin: {e}")

# ==================== NHẬN CALLBACK ====================
@app.route("/callback", methods=["GET", "POST"])
def callback():
    """Nhận callback từ thesieure.com / shopbanthe.com"""
    
    # Lấy dữ liệu từ request
    if request.method == "POST":
        data = request.get_json()
        if not data:
            data = request.form.to_dict()
    else:
        data = request.args.to_dict()
    
    print(f"[CALLBACK] Dữ liệu: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    # Trích xuất thông tin
    order_id = data.get("order_id") or data.get("trans_id") or data.get("id") or ""
    status = data.get("status") or data.get("result") or ""
    message = data.get("message") or data.get("msg") or ""
    amount = int(data.get("amount") or data.get("value") or 0)
    card_type = data.get("type") or data.get("card_type") or ""
    card_value = int(data.get("card_value") or data.get("amount") or 0)
    card_code = data.get("code") or data.get("card_code") or ""
    card_serial = data.get("serial") or data.get("card_serial") or ""
    user_id = data.get("user_id") or ""
    
    # Nếu không có order_id, dùng thông tin thẻ
    if not order_id:
        order_id = f"{user_id}_{int(datetime.now().timestamp())}"
    
    # Kiểm tra trạng thái thẻ
    if status in ["success", "1", "ok", "true", "done"]:
        # Thẻ thành công
        received_amount = amount if amount > 0 else int(card_value * 0.8)
        
        # Gửi thông báo cho user (nếu có user_id)
        if user_id:
            user_msg = f"""
✅ <b>NẠP THẺ THÀNH CÔNG!</b>

🎮 <b>Loại:</b> {card_type.upper()}
💵 <b>Mệnh giá:</b> {card_value:,}đ
💰 <b>Nhận được:</b> {received_amount:,}đ
📌 <b>Mã đơn:</b> {order_id}

Cảm ơn bạn đã sử dụng dịch vụ! ❤️
"""
            send_telegram(user_id, user_msg)
        
        # Gửi thông báo cho admin
        admin_msg = f"""
✅ <b>THẺ ĐƯỢC DUYỆT</b>

🆔 <b>Mã đơn:</b> {order_id}
👤 <b>User ID:</b> {user_id or 'Không có'}
📱 <b>Loại:</b> {card_type.upper()}
💵 <b>Mệnh giá:</b> {card_value:,}đ
💰 <b>User nhận:</b> {received_amount:,}đ
📌 <b>Trạng thái:</b> {status}
"""
        send_telegram(ADMIN_ID, admin_msg)
        
    else:
        # Thẻ thất bại
        if user_id:
            user_msg = f"""
❌ <b>NẠP THẺ THẤT BẠI!</b>

🎮 <b>Loại:</b> {card_type.upper()}
💵 <b>Mệnh giá:</b> {card_value:,}đ
📌 <b>Lý do:</b> {message or 'Không xác định'}

Vui lòng kiểm tra lại thẻ hoặc liên hệ admin!
"""
            send_telegram(user_id, user_msg)
        
        admin_msg = f"""
❌ <b>THẺ THẤT BẠI</b>

🆔 <b>Mã đơn:</b> {order_id}
👤 <b>User ID:</b> {user_id or 'Không có'}
📱 <b>Loại:</b> {card_type.upper()}
💵 <b>Mệnh giá:</b> {card_value:,}đ
📌 <b>Lý do:</b> {message or 'Không xác định'}
"""
        send_telegram(ADMIN_ID, admin_msg)
    
    # Trả về OK cho API
    return jsonify({"status": "success", "code": 200}), 200

# ==================== TRANG CHỦ ====================
@app.route("/")
def index():
    return """
    <html>
    <head><title>Callback Server</title></head>
    <body style="background:#0a0a0a;color:#00ff00;font-family:monospace;text-align:center;padding:50px;">
        <h1>✅ CALLBACK SERVER ĐANG CHẠY</h1>
        <p>🔗 Callback URL: <code>/callback</code></p>
        <p>📌 Trạng thái: <span style="color:#00ff00;">Online</span></p>
        <p>🤖 Bot: QanhBotVip</p>
        <hr>
        <p style="color:#666;font-size:12px;">Được tạo bởi QanhDZ</p>
    </body>
    </html>
    """

# ==================== CHECK SỨC KHỎE ====================
@app.route("/ping")
def ping():
    """Endpoint kiểm tra server còn sống"""
    return jsonify({
        "status": "ok",
        "time": datetime.now().isoformat(),
        "service": "callback-server"
    })

# ==================== KIỂM TRA TOKEN ====================
@app.route("/test_telegram")
def test_telegram():
    """Test gửi tin nhắn Telegram"""
    try:
        send_telegram(ADMIN_ID, "🔄 Test callback server đang chạy!")
        return jsonify({"status": "ok", "message": "Đã gửi tin nhắn test"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ==================== CHẠY ====================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Callback server đang chạy trên cổng {port}")
    app.run(host="0.0.0.0", port=port, debug=False)