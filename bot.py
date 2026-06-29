import os
import re
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Flask 웹 서버 (Render 서비스 유지를 위함)
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 데이터 저장소
user_data = {}
target_date = "출결"

async def collect_and_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global target_date
    text = update.message.text
    
    if "결과" in text:
        await show_result(update, context)
        return

    # 날짜 자동 감지 및 변환
    date_match = re.search(r'\[(\d+/\d+\(\S\))', text)
    if date_match: target_date = date_match.group(1).replace("주일", "수요")

    lines = text.split('\n')
    for line in lines:
        if ':' not in line: continue
        try:
            # 이름/직책 분리
            parts = line.split(':', 1)
            name_role = parts[0].replace('-', '').strip().split()
            name = name_role[0]
            role = name_role[1] if len(name_role) > 1 else ""
            
            # 정보 처리
            info = parts[1].strip()
            
            # 카테고리 분류 및 형식 통일
            if '인시센' in info:
                cat, details = 'indiv', info.split('(')[1].replace(')', '')
                formatted_info = f"{role}/{name}/{details}"
            elif '현장' in info:
                cat, details = 'on_site', info.split('(')[1].replace(')', '')
                formatted_info = f"{role}/{name}/{details}"
            elif '중진' in info:
                cat, details = 'central', info.split('(')[1].replace(')', '').replace('/', '/')
                formatted_info = f"{role}/{name}/{details}"
            elif '줌' in info:
                cat, details = 'local', info.split('(')[1].replace(')', '').replace('/', '/')
                formatted_info = f"{role}/{name}/{details}"
            else: continue
            
            user_data[name] = {'cat': cat, 'content': formatted_info}
        except: continue

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_data:
        await update.message.reply_text("📥 데이터가 없습니다.")
        return

    secs = {'on_site': [], 'central': [], 'local': [], 'indiv': []}
    for d in user_data.values():
        secs[d['cat']].append(d['content'])

    res = f"{target_date} 수요예배 출결\n\n문화부 총 {len(user_data)}명\n\n"
    res += f"1. 현장 참석 : {len(secs['on_site'])}명\n" + "\n".join(secs['on_site']) + "\n\n"
    res += f"2. 중진 줌 참석 : {len(secs['central'])}명\n" + "\n".join(secs['central']) + "\n\n"
    res += f"3. 각 부서 줌 참석 : {len(secs['local'])}명\n" + "\n".join(secs['local']) + "\n\n"
    res += f"4. 인시센 개별예배 : {len(secs['indiv'])}명\n" + "\n".join(secs['indiv'])
    
    await update.message.reply_text(res)
    user_data.clear()

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    app_bot = Application.builder().token(TOKEN).build()
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_and_check))
    app_bot.run_polling(drop_pending_updates=True)