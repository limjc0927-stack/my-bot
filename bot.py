import os
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TELEGRAM_TOKEN")
user_data = {}
target_date = "출결" # 기본값

async def collect_and_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global target_date
    text = update.message.text
    
    # 1. 날짜 자동 감지 (첫 줄에서 [5/24(일) ...] 형태 추출)
    date_match = re.search(r'\[(\d+/\d+\(\S\))', text)
    if date_match: target_date = date_match.group(1)
    
    if text.strip() == "결과":
        await show_result(update, context)
        return

    lines = text.split('\n')
    for line in lines:
        if ':' not in line: continue
        try:
            parts = line.split(':', 1)
            name = parts[0].strip().split()[0]
            info = parts[1].strip()
            if len(name) < 2: continue 

            cat, plc = "", ""
            # 분류 로직
            if '인시센' in info or '개별' in info or '사유출석' in info:
                cat = 'indiv'
                plc = re.search(r'\((.*?)\)', info).group(1) if re.search(r'\((.*?)\)', info) else "개별"
            elif any(k in info for k in ['현장', '대면', '지교회', '라움', '모임방']):
                cat = 'on_site'
                m = re.search(r'\((.*?)\)', info)
                plc = m.group(1) if m else info.replace('현장','').replace('대면','').strip()
            elif '중진' in info:
                cat = 'central'
                plc = '사무실' if '사무실' in info else '외부'
            elif '줌' in info:
                cat = 'local'
                m = re.search(r'\((.*?)\)', info)
                plc = m.group(1) if m else info.replace('줌','').strip()

            if cat: user_data[name] = {'cat': cat, 'plc': plc}
        except: continue

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_data:
        await update.message.reply_text("📥 데이터가 없습니다.")
        return

    secs = {'on_site': {}, 'central': {}, 'local': [], 'indiv': []}
    for name, d in user_data.items():
        if d['cat'] == 'on_site': secs['on_site'].setdefault(d['plc'], []).append(name)
        elif d['cat'] == 'central': secs['central'].setdefault(d['plc'], []).append(name)
        elif d['cat'] == 'local': secs['local'].append(f"{name} : {d['plc']}")
        elif d['cat'] == 'indiv': secs['indiv'].append(f"{name} : {d['plc']}")

    c1 = sum(len(v) for v in secs['on_site'].values())
    c2 = sum(len(v) for v in secs['central'].values())
    c3 = len(secs['local'])
    c4 = len(secs['indiv'])
    
    res = f"{target_date} 수요예배 출결\n\n문화부 총 {c1+c2+c3+c4}명\n\n"
    res += f"1. 현장 참석 : {c1}명\n" + "".join([f"- {', '.join(n)} : {p}\n" for p, n in secs['on_site'].items()])
    res += f"\n2. 중진 줌 참석 : {c2}명\n" + "".join([f"- {', '.join(n)} : {p}\n" for p, n in secs['central'].items()])
    res += f"\n3. 각 부서 줌 참석 : {c3}명\n" + "".join([f"- {item}\n" for item in secs['local']])
    res += f"\n4. 인시센 개별예배 : {c4}명\n" + "".join([f"- {item}\n" for item in secs['indiv']])
    
    await update.message.reply_text(res)
    user_data.clear()

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_and_check))
    app.run_polling()

if __name__ == '__main__':
    main()