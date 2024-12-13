import sqlite3
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# SQLite 데이터베이스 초기화
db_path = "lecture_data.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 강의 테이블에 고유 키 설정
cursor.execute("""
CREATE TABLE IF NOT EXISTS lectures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department TEXT,
    grade TEXT,
    day_night TEXT,
    credit TEXT,
    professor TEXT,
    course_name TEXT,
    section TEXT,
    course_type TEXT,
    lecture_type TEXT,
    lecture_time TEXT,
    hours TEXT,
    UNIQUE(course_name, section, lecture_time) -- 고유 제약 조건 추가
)
""")

# 강의 데이터 업데이트 최적화
def fetch_lecture_data_selenium():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://sugang.hknu.ac.kr/planLecture")

    # 첫 번째 조회 버튼 클릭
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "btnRefresh")))
    driver.find_element(By.CLASS_NAME, "btnRefresh").click()

    # 페이지 로드 대기
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table/tbody/tr')))

    # 테이블 데이터 가져오기
    rows = driver.find_elements(By.XPATH, '//table/tbody/tr')
    new_data_count = 0

    for row in rows:
        try:
            # 행 데이터 추출
            data = [
                row.find_element(By.XPATH, f'./td[{i}]').text for i in range(1, 12)
            ]

            # 기존 데이터 확인 (중복 여부 체크)
            cursor.execute("""
            SELECT COUNT(*) FROM lectures 
            WHERE course_name = ? AND section = ? AND lecture_time = ?
            """, (data[5], data[6], data[9]))
            if cursor.fetchone()[0] == 0:
                # 새로운 데이터 삽입
                cursor.execute("""
                INSERT INTO lectures (
                    department, grade, day_night, credit, professor,
                    course_name, section, course_type, lecture_type,
                    lecture_time, hours
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
                new_data_count += 1
        except Exception as e:
            print(f"오류 발생: {e}")

    conn.commit()  # 변경 사항을 데이터베이스에 커밋
    driver.quit()

# 강의 추천 함수
async def recommend_lectures(update, context):
    keyboard = [
        [
            InlineKeyboardButton("1. 학년별 추천", callback_data='1'),
            InlineKeyboardButton("2. 전공별 추천", callback_data='2'),
        ],
        [
            InlineKeyboardButton("3. 강의 유형별 추천", callback_data='3'),
            InlineKeyboardButton("4. 강의 시간별 추천", callback_data='4'),
        ],
        [
            InlineKeyboardButton("5. 학점별 추천", callback_data='5'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Use await here to properly await the asynchronous operation
    await update.message.reply_text("추천 강의 조건을 선택하세요:", reply_markup=reply_markup)

# 버튼 클릭 처리
async def button(update, context):
    query = update.callback_query
    choice = query.data

    if choice == '1':
        await query.edit_message_text(text="학년을 입력하세요 (예: 1학년):")
        context.user_data['choice'] = '1'
    elif choice == '2':
        await query.edit_message_text(text="전공을 입력하세요 (예: 컴퓨터공학과):")
        context.user_data['choice'] = '2'
    elif choice == '3':
        await query.edit_message_text(text="강의 유형을 입력하세요 (예: 이론):")
        context.user_data['choice'] = '3'
    elif choice == '4':
        await query.edit_message_text(text="강의 시간을 입력하세요 (예: 월, 화, 수, 목, 금):")
        context.user_data['choice'] = '4'
    elif choice == '5':
        await query.edit_message_text(text="학점을 입력하세요 (예: 3):")
        context.user_data['choice'] = '5'

# 강의 검색 결과를 출력하는 함수
async def handle_message(update, context):
    user_input = update.message.text
    choice = context.user_data.get('choice')

    # 여기에 각 조건에 맞는 SQL 쿼리를 실행하는 코드 삽입
    if choice == '1':
        query = "SELECT * FROM lectures WHERE grade LIKE ?"
        cursor.execute(query, (f"%{user_input}%",))
    elif choice == '2':
        query = "SELECT * FROM lectures WHERE department LIKE ?"
        cursor.execute(query, (f"%{user_input}%",))
    elif choice == '3':
        query = "SELECT * FROM lectures WHERE lecture_type LIKE ?"
        cursor.execute(query, (f"%{user_input}%",))
    elif choice == '4':
        query = "SELECT * FROM lectures WHERE lecture_time LIKE ?"
        cursor.execute(query, (f"%{user_input}%",))
    elif choice == '5':
        try:
            credit_input = int(user_input)  # 학점 입력을 정수로 변환
            query = "SELECT * FROM lectures WHERE CAST(credit AS INTEGER) = ?"
            cursor.execute(query, (credit_input,))
        except ValueError:
            await update.message.reply_text("학점을 숫자로 입력해주세요.")
            return
    else:
        await update.message.reply_text("잘못된 입력입니다.")
        return

    results = cursor.fetchall()

    # 결과가 있는지 확인
    if not results:
        await update.message.reply_text("조건에 맞는 강의가 없습니다.")
        return

    # 대표 강의 5개 출력
    reply_message = "\n추천 강의 TOP 5:\n"
    for i, row in enumerate(results[:5], 1):
        reply_message += f"{i}. {row[6]} (담당 교수: {row[5]}, 학점: {row[4]}, 강의 시간: {row[10]})\n"

    # 나머지 강의 CSV 저장
    if len(results) > 5:
        file_path = "remaining_lectures.csv"
        with open(file_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Department", "Grade", "Day/Night", "Credit", "Professor",
                             "Course Name", "Section", "Course Type", "Lecture Type",
                             "Lecture Time", "Hours"])
            writer.writerows(results[5:])

        # Telegram 파일 업로드
        with open(file_path, "rb") as csv_file:
            await update.message.reply_document(document=csv_file, filename="remaining_lectures.csv")

        reply_message += f"\n추천 강의 이외의 데이터는 CSV 파일로 저장되어 첨부되었습니다. 다른 추천 강의 조건 목록을 보려면 /recommend를 입력하세요"

    await update.message.reply_text(reply_message)

# 텔레그램 봇 설정
async def start(update, context):
    await update.message.reply_text("안녕하세요! 강의 추천 봇입니다. /recommend 명령어를 입력하여 추천을 시작하세요.")

async def recommend(update, context):
    await recommend_lectures(update, context)

# 메인 함수
def main():
    # 텔레그램 봇 토큰
    bot_token = ""

    application = Application.builder().token(bot_token).build()

    # 핸들러 설정
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("recommend", recommend))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 봇 시작
    application.run_polling()

if __name__ == "__main__":
    try:
        print("강의 데이터를 수집 중입니다...")
        fetch_lecture_data_selenium()
        print("강의 데이터 수집 완료!")
        main()
    finally:
        conn.close()
