import os
import sqlite3
import bcrypt
import csv
from cryptography.fernet import Fernet
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, \
    CallbackQueryHandler, ConversationHandler
from bs4 import BeautifulSoup
import requests
import json
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime
import urllib3
import asyncio
import nest_asyncio
import pandas as pd
import time
from selenium.webdriver.common.keys import Keys
import re
from selenium.webdriver.chrome.options import Options

ASKING_ID, ASKING_PASSWORD = range(2)


# SQLite 데이터베이스 초기화 (사용자 데이터)
def init_user_db():
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            user_password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# 강의 데이터베이스 초기화 함수 수정
def init_lecture_db():
    conn = sqlite3.connect("lecture_data.db")
    cursor = conn.cursor()
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
        UNIQUE(course_name, section, lecture_time)
    )
    """)
    conn.commit()
    conn.close()


# 강의 데이터 수집 함수 수정
def fetch_lecture_data():
    # 데이터베이스 파일 존재 여부 확인
    if os.path.exists("lecture_data.db"):
        conn = sqlite3.connect("lecture_data.db")
        cursor = conn.cursor()

        # 데이터 존재 여부 확인
        cursor.execute("SELECT COUNT(*) FROM lectures")
        count = cursor.fetchone()[0]

        if count > 0:
            print("강의 데이터가 이미 존재합니다. 크롤링을 건너뜁니다.")
            conn.close()
            return

        conn.close()

    print("강의 데이터를 수집중입니다...")
    conn = sqlite3.connect("lecture_data.db")
    cursor = conn.cursor()

    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get("https://sugang.hknu.ac.kr/planLecture")

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "btnRefresh")))
        driver.find_element(By.CLASS_NAME, "btnRefresh").click()

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//table/tbody/tr')))

        rows = driver.find_elements(By.XPATH, '//table/tbody/tr')
        new_data_count = 0

        for row in rows:
            try:
                data = [
                    row.find_element(By.XPATH, f'./td[{i}]').text for i in range(1, 12)
                ]

                cursor.execute("""
                SELECT COUNT(*) FROM lectures 
                WHERE course_name = ? AND section = ? AND lecture_time = ?
                """, (data[5], data[6], data[9]))

                if cursor.fetchone()[0] == 0:
                    cursor.execute("""
                    INSERT INTO lectures (
                        department, grade, day_night, credit, professor,
                        course_name, section, course_type, lecture_type,
                        lecture_time, hours
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, data)
                    new_data_count += 1

            except Exception as e:
                print(f"강의 데이터 수집 오류: {e}")

        conn.commit()
        print(f"새로운 강의 데이터 {new_data_count}개가 추가되었습니다.")

    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
    finally:
        driver.quit()
        conn.close()


# 키 생성 (최초 1회)
def generate_key():
    if not os.path.exists("encryption.key"):
        key = Fernet.generate_key()
        with open("encryption.key", "wb") as key_file:
            key_file.write(key)
        print("encryption.key 파일이 생성되었습니다.")
    else:
        print("encryption.key 파일이 이미 존재합니다.")


# 키 로드
def load_key():
    if not os.path.exists("encryption.key"):
        raise FileNotFoundError("encryption.key 파일이 없습니다. 키를 생성하세요.")
    with open("encryption.key", "rb") as key_file:
        return key_file.read()


# 암호화 함수
def encrypt_data(data):
    key = load_key()
    fernet = Fernet(key)
    return fernet.encrypt(data.encode('utf-8')).decode('utf-8')


# 복호화 함수
def decrypt_data(encrypted_data):
    key = load_key()
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')


def hash_password(password):
    # bcrypt로 비밀번호를 해시화
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')  # 데이터베이스에 저장을 위해 문자열로 변환


# 데이터 저장
def save_user(telegram_id, user_id, user_password):
    encrypted_id = encrypt_data(user_id)  # ID 암호화
    encrypted_password = encrypt_data(user_password)  # 비밀번호 암호화

    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (telegram_id, user_id, user_password)
        VALUES (?, ?, ?)
    """, (telegram_id, encrypted_id, encrypted_password))
    conn.commit()
    conn.close()


# 데이터 검색
def get_user(telegram_id):
    conn = sqlite3.connect("user_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, user_password FROM users WHERE telegram_id = ?
    """, (telegram_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        encrypted_id, encrypted_password = result
        decrypted_id = decrypt_data(encrypted_id)  # ID 복호화
        decrypted_password = decrypt_data(encrypted_password)  # 비밀번호 복호화
        return decrypted_id, decrypted_password
    return None


url = "https://cesrv.hknu.ac.kr/srv/gpt"

context = ""


# GPT 초기 학습
async def gaslighting(update):
    global context

    context += "User: 너는 이제부터 HK Chatbot 이고, 이 챗봇의 이용자는 한경국립대학교 학생이야."

    payload = {
        "service": "gpt",
        "question": context,
        "hash": ""
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False)
        response.raise_for_status()
        result = response.json()
        answer = result.get('answer')
        if answer:
            return answer
        else:
            await update.message.reply_text("AI 응답을 받을 수 없습니다. 잠시 후 다시 시도해 주세요.")
    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"오류 발생: {e}")


async def send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ReplyKeyboardMarkup을 사용하는 메뉴 함수"""
    keyboard = [
        ["📋 학식정보 확인", "📢 학사공지 확인"],
        ["🎓 사용자 맞춤 강의추천", "📝 과제 및 일정 확인"],
        ["🎓 졸업인증 요건 확인", "🤖 GPT와 대화하기"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    if isinstance(update, Update):
        await update.message.reply_text(
            "📚 메뉴를 선택하세요:",
            reply_markup=reply_markup
        )
    else:  # Message 객체인 경우
        await update.reply_text(
            "📚 메뉴를 선택하세요:",
            reply_markup=reply_markup
        )


async def course_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """강의 추천 버튼 처리"""
    query = update.callback_query
    await query.answer()

    choice = query.data
    if not choice.startswith('course_'):
        return

    choice_num = choice.split('_')[1]

    if choice_num == 'back':  # 메뉴로 돌아가기
        await query.message.delete()  # 기존 메시지 삭제
        await send_menu(query.message, context)  # 메뉴 다시 표시
        return

    messages = {
        '1': "학년을 입력하세요 (예: 1학년):",
        '2': "전공을 입력하세요 (예: 컴퓨터공학과):",
        '3': "강의 유형을 입력하세요 (예: 이론):",
        '4': "강의 시간을 입력하세요 (예: 월, 화, 수, 목, 금):",
        '5': "학점을 입력하세요 (예: 3):"
    }

    keyboard = [[InlineKeyboardButton("🔙 메뉴로 돌아가기", callback_data='course_back')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=messages[choice_num],
        reply_markup=reply_markup
    )
    context.user_data['course_choice'] = choice_num


async def case_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """졸업 인증 요건 버튼 처리"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    download_dir = os.path.join(current_dir, "downloads")
    file_name = "(학부 공지용)24-2학기 교양 교과목 시간표_8.29.xlsx"
    file_path = os.path.join(download_dir, file_name)

    query = update.callback_query
    await query.answer()

    # telegram_id를 통해 사용자 정보 가져오기
    telegram_id = str(query.from_user.id)
    user_data = get_user(telegram_id)

    if not user_data:
        await query.edit_message_text(
            "먼저 ID와 비밀번호를 등록해주세요.\n"
            "/start 명령어를 사용해 등록해주세요."
        )
        return

    user_id, user_password = user_data
    choice = query.data

    if not choice.startswith('case_'):
        return

    choice_num = choice.split('_')[1]

    if choice_num == "1":  # 수강내역
        await query.edit_message_text("수강 내역을 확인 중입니다...")
        result = execute_course_history(file_path, user_id, user_password)
        await query.edit_message_text(result)

    elif choice_num == "2":  # 강의 목록 표시
        keyboard = [
            [InlineKeyboardButton("🎨 1영역 - 인문/예술", callback_data='lecture_1')],
            [InlineKeyboardButton("🌐 2영역 - 사회/과학", callback_data='lecture_2')],
            [InlineKeyboardButton("🏛️ 3영역 - 문화/역사", callback_data='lecture_3')],
            [InlineKeyboardButton("🔬 4영역 - 자연/공학", callback_data='lecture_4')],
            [InlineKeyboardButton("📚 기초문해교육", callback_data='lecture_5')],
            [InlineKeyboardButton("📐 기초과학교육", callback_data='lecture_6')],
            [InlineKeyboardButton("🔙 메뉴로 돌아가기", callback_data='case_back')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📚 강의 목록을 선택하세요:", reply_markup=reply_markup)

    elif choice_num == "3":  # 졸업 인증
        await query.edit_message_text("졸업 인증 요건 페이지로 이동합니다.\nhttps://www.hknu.ac.kr/hkcommath/2083/subview.do")

    elif choice_num == "back":  # 메뉴로 돌아가기
        await query.message.delete()
        await send_menu(query.message, context)  # 메인 메뉴로 돌아가기


async def lecture_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """졸업 인증 요건 버튼 처리"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    download_dir = os.path.join(current_dir, "downloads")
    file_name = "(학부 공지용)24-2학기 교양 교과목 시간표_8.29.xlsx"
    file_path = os.path.join(download_dir, file_name)
    query = update.callback_query
    await query.answer()

    choice = query.data
    print(f"콜백 데이터: {choice}")  # 디버깅 로그

    if not choice.startswith('lecture_'):
        return

    choice_num = choice.split('_')[1]

    if choice_num == "1":  # 1영역 필터링
        await query.edit_message_text("강의 정보를 확인 중입니다... (1영역)")
        result = filter_excel_by_keyword(file_path, "1영역")
        formatted_result = format_results_by_area("🎨 1영역 - 인문/예술", result)
        await query.edit_message_text(f"{formatted_result}")

    elif choice_num == "2":  # 2영역 필터링
        await query.edit_message_text("강의 정보를 확인 중입니다... (2영역)")
        result = filter_excel_by_keyword(file_path, "2영역")
        formatted_result = format_results_by_area("🌐 2영역 - 사회/과학", result)
        await query.edit_message_text(f"{formatted_result}")

    elif choice_num == "3":  # 3영역 필터링
        await query.edit_message_text("강의 정보를 확인 중입니다... (3영역)")
        result = filter_excel_by_keyword(file_path, "3영역")
        formatted_result = format_results_by_area("🏛️ 3영역 - 문화/역사", result)
        await query.edit_message_text(f"{formatted_result}")

    elif choice_num == "4":  # 4영역 필터링
        await query.edit_message_text("강의 정보를 확인 중입니다... (4영역)")
        result = filter_excel_by_keyword(file_path, "4영역")
        formatted_result = format_results_by_area("🔬 4영역 - 자연/공학", result)
        await query.edit_message_text(f"{formatted_result}")

    elif choice_num == "5":  # 기초문해교육 필터링
        await query.edit_message_text("강의 정보를 확인 중입니다... (기초문해교육)")
        result = filter_excel_by_keyword(file_path, "기초문해교육")
        formatted_result = format_results_by_area("📚 기초문해교육", result)
        await query.edit_message_text(f"{formatted_result}")

    elif choice_num == "6":  # 기초과학교육 필터링
        await query.edit_message_text("강의 정보를 확인 중입니다... (기초과학교육)")
        result = filter_excel_by_keyword(file_path, "기초과학교육")
        formatted_result = format_results_by_area("🔬 기초과학교육", result)
        await query.edit_message_text(f"{formatted_result}")

    elif choice_num == "back":  # 메뉴로 돌아가기
        await query.message.delete()
        await send_menu(query.message, context)  # 메인 메뉴로 돌아가기

    else:
        await query.edit_message_text("잘못된 요청입니다.")


def filter_excel_by_keyword(file_path, keyword):
    """
    엑셀 파일에서 주어진 키워드로 필터링하여 6, 18, 19번째 열의 값을 출력하는 함수

    Args:
        file_path (str): 엑셀 파일 경로
        keyword (str): 검색 키워드 (1영역, 2영역, 기초문해교육 등)

    Returns:
        list: 필터링된 결과를 담은 리스트
    """
    try:
        # 엑셀 파일 읽기
        df = pd.read_excel(file_path, header=1)  # 두 번째 행을 헤더로 사용

        # 필터링: 5번째 열에 키워드가 포함된 행만 선택
        filtered_df = df[df.iloc[:, 4].astype(str).str.contains(keyword, na=False)]

        if filtered_df.empty:
            print(f"키워드 '{keyword}'에 해당하는 데이터가 없습니다.")
            return []

        # 필요한 열(6, 18, 19번째 열) 추출
        result = filtered_df.iloc[:, [5, 17, 18]].values.tolist()

        return result

    except Exception as e:
        print(f"오류 발생: {e}")
        return []


def format_results_by_area(area_name, results):
    """
    주어진 영역 이름과 결과를 가독성 있게 포맷팅합니다.

    Args:
        area_name (str): 영역 이름.
        results (list): 필터링된 결과 리스트.

    Returns:
        str: 포맷된 결과 문자열.
    """
    if not results:
        return f"{area_name}\n━━━━━━━━━━━━━━━━━━━━━\n결과가 없습니다."

    formatted_result = f"{area_name}\n━━━━━━━━━━━━━━━━━━━━━\n"
    formatted_result += "\n".join([f"• {row[0]} ({row[1]}) {row[2]}" for row in results])
    return formatted_result




# 메시지 핸들러에 추가할 함수
async def handle_area_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자의 영역 입력 처리"""
    if context.user_data.get('waiting_for_area_input'):
        user_input = update.message.text

        # 입력 처리 로직 (여기서 '영역별 구분' 처리)
        await update.message.reply_text(f"입력하신 영역: {user_input}")

        # 대화 상태 초기화
        del context.user_data['waiting_for_area_input']


# 텔레그램 채팅창에서 "/"를 입력할 때 나타나는 명령어 목록을 정의
async def set_menu_commands(app):
    commands = [
        BotCommand("start", "계정을 등록합니다. (처음 사용자용)"),
        BotCommand("menu", "메뉴를 표시합니다."),
        BotCommand("meal", "📋 학식정보 확인"),
        BotCommand("notices", "📢 학사공지 확인"),
        BotCommand("courses", "🎓 사용자 맞춤 강의추천"),
        BotCommand("tasks", "📝 과제 및 일정 확인"),
        BotCommand("graduation", "🎓 졸업인증 요건 확인"),
        BotCommand("gpt", "🤖 GPT와 대화하기"),
    ]
    # 명령어 설정
    await app.bot.set_my_commands(commands)


# /courses 명령어 처리
async def courses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1. 학년별 추천", callback_data='course_1'),
         InlineKeyboardButton("2. 전공별 추천", callback_data='course_2')],
        [InlineKeyboardButton("3. 강의 유형별 추천", callback_data='course_3'),
         InlineKeyboardButton("4. 강의 시간별 추천", callback_data='course_4')],
        [InlineKeyboardButton("5. 학점별 추천", callback_data='course_5')],
        [InlineKeyboardButton("🔙 메뉴로 돌아가기", callback_data='course_back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("추천 강의 조건을 선택하세요:", reply_markup=reply_markup)


# 강의 검색 결과 처리 함수
async def handle_course_search(update: Update, context: ContextTypes.DEFAULT_TYPE, choice: str, user_input: str):
    """강의 검색 및 결과 표시"""
    conn = sqlite3.connect("lecture_data.db")
    cursor = conn.cursor()

    try:
        if choice == '5':  # 학점 검색의 경우
            try:
                credit_input = int(user_input)
                query = "SELECT * FROM lectures WHERE CAST(credit AS INTEGER) = ?"
                cursor.execute(query, (credit_input,))
            except ValueError:
                await update.message.reply_text("학점을 숫자로 입력해주세요.")
                return
        else:
            queries = {
                '1': ("SELECT * FROM lectures WHERE grade LIKE ?", f"%{user_input}%"),
                '2': ("SELECT * FROM lectures WHERE department LIKE ?", f"%{user_input}%"),
                '3': ("SELECT * FROM lectures WHERE lecture_type LIKE ?", f"%{user_input}%"),
                '4': ("SELECT * FROM lectures WHERE lecture_time LIKE ?", f"%{user_input}%")
            }
            query, param = queries[choice]
            cursor.execute(query, (param,))

        results = cursor.fetchall()

        if not results:
            await update.message.reply_text("조건에 맞는 강의가 없습니다.")
            return

        reply_message = "\n추천 강의 TOP 5:\n"
        for i, row in enumerate(results[:5], 1):
            reply_message += f"{i}. {row[6]} (담당 교수: {row[5]}, 학점: {row[4]}, 강의 시간: {row[10]})\n"

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

            reply_message += "\n추천 강의 이외의 데이터는 CSV 파일로 첨부되었습니다."

        await update.message.reply_text(reply_message)

        # 검색 완료 후 메뉴로 돌아가기
        await send_menu(update, context)

    finally:
        conn.close()
        if 'course_choice' in context.user_data:
            del context.user_data['course_choice']


async def meal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """학식 정보 조회"""
    meal_info = await mealCrawling()
    await update.message.reply_text(meal_info)


async def notices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """학사 공지 조회"""
    notices = get_notices()
    if notices:
        result = "📢 [학사 공지 알림]\n"
        for i, notice in enumerate(notices, start=1):
            result += f"{i}. {notice['title']} [{notice['writer']}] [{notice['date']}]\n 자세히 보기: {notice['link']}\n\n"
        await update.message.reply_text(result)
    else:
        await update.message.reply_text("공지사항을 가져오는 데 실패했습니다.")


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """과제 및 일정 조회"""
    telegram_id = str(update.effective_user.id)
    user_data = get_user(telegram_id)
    if user_data:
        user_id, user_password = user_data
        todo_info = await todoCrawling(user_id, user_password)
        await update.message.reply_text(todo_info)
    else:
        await update.message.reply_text("먼저 ID와 비밀번호를 등록해주세요. /start 명령어를 입력하세요.")


download_path = r"C:\Users\htutu\Downloads"
chrome_options = Options()
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": download_path,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})


def is_file_recent(file_path, expiration_time=86400):
    """
    파일이 최근에 다운로드된 파일인지 확인합니다.

    Args:
        file_path (str): 확인할 파일의 경로.
        expiration_time (int): 파일이 유효한 시간(초).

    Returns:
        bool: 파일이 최신 상태라면 True, 그렇지 않으면 False.
    """
    if os.path.exists(file_path):
        last_modified_time = os.path.getmtime(file_path)
        current_time = time.time()
        return (current_time - last_modified_time) < expiration_time
    return False

async def graduation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """졸업 인증 요건 조회"""
    # 현재 스크립트가 실행되는 디렉토리를 기준으로 경로 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    download_dir = os.path.join(current_dir, "downloads")
    os.makedirs(download_dir, exist_ok=True)  # 다운로드 디렉토리 생성

    file_name_1 = "(학부 공지용)24-2학기 교양 교과목 시간표_8.29.xlsx"
    file_name_2 = "(참고)구 필수교양 세부 8영역 기이수 과목 4영역 매칭 안내.xlsx"

    file_path_1 = os.path.join(download_dir, file_name_1)
    file_path_2 = os.path.join(download_dir, file_name_2)

    # 파일이 최신 상태인지 확인
    if is_file_recent(file_path_1) and is_file_recent(file_path_2):
        print("파일이 이미 최신 상태입니다. 다운로드를 건너뜁니다.")
        await update.message.reply_text("졸업 인증 요건 파일이 이미 최신 상태입니다. 다운로드를 건너뜁니다.")
        context.user_data["downloaded_file_paths"] = [file_path_1, file_path_2]
    else:
        print("데이터를 가져오는 중...")
        driver = initialize_browser(download_dir)

        try:
            # 파일 다운로드 로직 실행
            downloaded_files = download_file_from_page(
                driver,
                url='https://www.hknu.ac.kr/hkcult/2488/subview.do',
                search_text='학기 교양 교과목 시간표',
                result_xpath="//a[@onclick=\"jf_viewArtcl('hkcult', '305', '77268')\"]",
                download_xpaths=[
                    "//a[@href='/bbs/hkcult/305/93820/download.do']",
                    "//a[@href='/bbs/hkcult/305/92708/download.do']"
                ],
                download_dir=download_dir,  # 다운로드 디렉토리 추가
                expected_files=[file_name_1, file_name_2]  # 예상 파일 이름 목록 추가
            )

            # 다운로드된 파일을 Context에 저장
            context.user_data["downloaded_file_paths"] = [os.path.join(download_dir, f) for f in downloaded_files]
            await update.message.reply_text("졸업 인증 요건 데이터가 성공적으로 갱신되었습니다.")

        except FileNotFoundError as e:
            await update.message.reply_text(f"❌ 다운로드 실패: {e}")
        except Exception as e:
            await update.message.reply_text(f"❌ 처리 중 오류가 발생했습니다: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()

    # 메뉴 표시
    keyboard = [
        [InlineKeyboardButton("1. 수강내역", callback_data='case_1')],
        [InlineKeyboardButton("2. 강의", callback_data='case_2')],
        [InlineKeyboardButton("3. 졸업인증", callback_data='case_3')],
        [InlineKeyboardButton("🔙 메뉴로 돌아가기", callback_data='course_back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("확인하고 싶은 정보를 선택해주세요:", reply_markup=reply_markup)



# 브라우저 초기화 함수
# 브라우저 초기화 함수
def initialize_browser(download_dir):
    """브라우저 초기화 함수"""
    chrome_options = Options()
    chrome_options.add_argument("headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # 다운로드 경로 설정
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # JSON 직렬화 방지
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    except Exception as e:
        print(f"브라우저 초기화 오류: {e}")
        raise

    return driver


# 다운로드 완료 대기 함수
def wait_for_file_download(download_dir, expected_files, timeout=30):
    """
    지정된 디렉토리에서 예상된 파일들이 다운로드 완료될 때까지 대기합니다.

    Args:
        download_dir (str): 다운로드 디렉토리 경로.
        expected_files (list): 예상되는 파일 이름 목록.
        timeout (int): 최대 대기 시간(초).

    Returns:
        list: 실제 다운로드된 파일 이름 목록.
    """
    start_time = time.time()
    downloaded_files = []

    while time.time() - start_time < timeout:
        files_in_dir = os.listdir(download_dir)
        temp_files = [f for f in files_in_dir if f.endswith(".crdownload")]
        completed_files = [f for f in files_in_dir if f in expected_files]

        if not temp_files and set(completed_files) == set(expected_files):
            downloaded_files = completed_files
            break

        time.sleep(1)  # 1초 대기

    return downloaded_files

def download_file_from_page(driver, url, search_text, result_xpath, download_xpaths, download_dir, expected_files):
    """
    페이지에서 파일을 다운로드하고, 완료될 때까지 대기합니다.

    Args:
        driver: Selenium WebDriver 객체.
        url (str): 접근할 페이지 URL.
        search_text (str): 검색어.
        result_xpath (str): 검색 결과 클릭을 위한 XPath.
        download_xpaths (list): 다운로드할 파일 링크들의 XPath 목록.
        download_dir (str): 다운로드 디렉토리 경로.
        expected_files (list): 예상되는 파일 이름 목록.

    Returns:
        list: 다운로드된 파일 이름 목록.
    """
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    # 검색어 입력
    search = wait.until(EC.presence_of_element_located((By.ID, 'srchWrd')))
    search.clear()
    search.send_keys(search_text)
    search.send_keys(Keys.ENTER)

    # 페이지가 로드될 때까지 대기
    wait.until(EC.presence_of_element_located((By.XPATH, result_xpath)))

    # 검색 결과 페이지로 이동
    text_click = wait.until(EC.element_to_be_clickable((By.XPATH, result_xpath)))
    text_click.click()

    # 모든 파일 다운로드 클릭
    for download_xpath in download_xpaths:
        element = wait.until(EC.element_to_be_clickable((By.XPATH, download_xpath)))
        element.click()

    # 다운로드 완료 대기
    downloaded_files = wait_for_file_download(download_dir, expected_files, timeout=60)

    if len(downloaded_files) != len(expected_files):
        missing_files = set(expected_files) - set(downloaded_files)
        raise FileNotFoundError(f"다음 파일들이 누락되었습니다: {', '.join(missing_files)}")

    return downloaded_files


def execute_course_history(file_path, user_id, user_password):
    """
    수강 내역을 확인하는 함수

    Args:
        file_path (str): 엑셀 파일 경로
        user_id (str): 사용자 ID
        user_password (str): 사용자 비밀번호

    Returns:
        str: 수강 내역 결과 문자열
    """
    if not user_id or not user_password:
        return "사용자 ID와 비밀번호가 필요합니다."

    # 브라우저 초기화
    current_dir = os.path.dirname(os.path.abspath(__file__))
    download_dir = os.path.join(current_dir, "downloads")
    driver = initialize_browser(download_dir)

    try:
        data = []  # Selenium으로 추출한 데이터
        driver.get('https://cyber.hknu.ac.kr/ilos/main/member/login_form.acl')
        driver.find_element(By.ID, 'usr_id').send_keys(user_id)
        driver.find_element(By.ID, 'usr_pwd').send_keys(user_password)
        driver.find_element(By.ID, 'login_btn').click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//img[@val='coursesubject.png']"))).click()

        # 이전 학기 내용 추가 로드
        while True:
            try:
                more_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "onceLecture")))
                more_button.click()
                time.sleep(2)
            except:
                break

        # Selenium으로 텍스트 추출
        elements = driver.find_elements(By.CLASS_NAME, "content-title")
        for element in elements:
            full_text = element.text
            truncated_text = re.split(r'\(', full_text, maxsplit=1)[0].strip()
            data.append(truncated_text)

        # 파일 읽기 및 비교
        data_frame = pd.read_excel(file_path)
        data_frame.columns = data_frame.iloc[1]  # 두 번째 행을 열 이름으로 설정
        data_frame = data_frame[2:]  # 데이터만 남김
        comparison_data = data_frame[["영역", "과목명"]].dropna()  # 필요한 열만 추출

        # 데이터 비교 및 결과 저장
        result_lines = ["[수강 내역]", "----------------------------"]
        for item in data:
            for _, row in comparison_data.iterrows():
                if row["과목명"] == item:
                    area = row["영역"] if pd.notna(row["영역"]) else "미분류"
                    result_lines.append(f"{area:<15} {item}")  # 보기 좋게 정렬된 출력
                    break  # 일치 항목 발견 시 내부 루프 종료
        result_lines.append("----------------------------")

        # 결과 텍스트로 반환
        return "\n".join(result_lines)

    finally:
        if driver:
            driver.quit()


# 강의 데이터 처리 함수
def execute_lecture(file_path, additional_file_path):
    """
    강의 데이터 처리 함수.

    Parameters:
        file_path (str): 첫 번째 다운로드된 파일 경로.
        additional_file_path (str): 새로 추가된 다운로드 파일 경로.
    """
    # 첫 번째 파일 처리
    df_main = pd.read_excel(file_path)
    df_main.columns = df_main.iloc[1]  # 두 번째 행을 열 이름으로 설정
    df_main = df_main[2:]  # 나머지 데이터를 사용

    # 두 번째 파일 처리 (추가 다운로드된 파일)
    df_additional = pd.read_excel(additional_file_path)
    df_additional.columns = df_additional.iloc[1]
    df_additional = df_additional[2:]

    # 열 확인

    while True:
        try:
            # 사용자가 선택할 모드
            mode = input("\n처리 모드를 선택하세요 ('영역별 확인', '영역비교', '이수구분', '원격여부', '캠퍼스', '종료'): ").strip()

            if mode == "영역별 확인":
                keyword = input("검색할 영역 키워드를 입력하세요 (예: 1영역, 2영역, 3영역, 4영역, 기초문해교육, 기초과학교육): ").strip()
                filtered_rows = df_main[df_main["영역"].str.contains(keyword, na=False)]  # 영역 열 검색

                if not filtered_rows.empty:
                    print("\n[영역별 확인 결과]")
                    print(filtered_rows)
                else:
                    print("\n일치하는 데이터가 없습니다.")

            elif mode == "영역비교":
                keyword = input("검색할 과목명를 입력하세요(예: 공학윤리): ").strip()
                filtered_rows_main = df_main[df_main["영역"].str.contains(keyword, na=False)]  # 첫 번째 파일에서 영역 검색
                filtered_rows_additional = df_additional[
                    df_additional.iloc[:, 5].str.contains(keyword, na=False)]  # 두 번째 파일에서 6번째 열 검색

                if not filtered_rows_additional.empty:
                    print("\n[영역비교 결과]")
                    for _, row in filtered_rows_additional.iterrows():
                        print(f"{row.iloc[5]}의 영역은{row.iloc[7]}입니다.")
                else:
                    print("\n추가 다운로드된 파일에서 키워드와 일치하는 데이터가 없습니다.")

            elif mode == "이수구분":
                keyword = input("검색할 이수구분을 입력하세요 (예: 기초교양, 핵심교양, 소양교양): ").strip()
                filtered_rows = df_main[df_main.iloc[:, 8].str.contains(keyword, na=False)]  # 9번째 열

                if not filtered_rows.empty:
                    print("\n이수구분 결과: ")
                    print(filtered_rows.iloc[:, 5])  # 6번째 열 출력
                else:
                    print("\n일치하는 데이터가 없습니다.")

            elif mode == "원격여부":
                keyword = input("검색할 원격여부를 입력하세요 (예: Y, N): ").strip()
                filtered_rows = df_main[df_main.iloc[:, 6].str.contains(keyword, na=False)]  # 7번째 열

                if not filtered_rows.empty:
                    print("\n원격여부 결과: ")
                    print(filtered_rows.iloc[:, 5])  # 6번째 열 출력
                else:
                    print("\n일치하는 데이터가 없습니다.")

            elif mode == "캠퍼스":
                keyword = input("검색할 캠퍼스를 입력하세요 (예: 안캠, 평캠): ").strip()
                filtered_rows = df_main[df_main.iloc[:, 21].str.contains(keyword, na=False)]  # 22번째 열

                if not filtered_rows.empty:
                    print("\n캠퍼스 결과: ")
                    print(filtered_rows.iloc[:, 5])  # 6번째 열 출력
                else:
                    print("\n일치하는 데이터가 없습니다.")

            elif mode == "종료":
                print("프로그램을 종료합니다.")
                break

            else:
                print("\n올바른 입력이 아닙니다. 다시 선택하세요.")

        except Exception as e:
            print(f"오류 발생: {e}")


async def gpt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """GPT 대화 시작"""
    await update.message.reply_text("GPT와 대화를 시작합니다. 질문을 입력해주세요:")
    context.user_data["gpt_mode"] = True


async def gpt_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """GPT 메시지 처리"""
    # course_choice가 있으면 강의 검색 처리
    if 'course_choice' in context.user_data:
        choice = context.user_data['course_choice']
        await handle_course_search(update, context, choice, update.message.text)
        return

    # GPT 응답 처리
    if context.user_data.get("gpt_mode", False):
        answer = await gpt(update, update.message.text)
        await update.message.reply_text(answer)


# 봇 시작 메시지
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = str(update.effective_user.id)

    # 기존 사용자 확인
    user_data = get_user(telegram_id)
    if user_data:
        user_id, user_password = user_data
        await update.message.reply_text(
            f"이미 저장된 정보가 있습니다:\nID: {user_id}\nPassword: {user_password}"
        )
        await gaslighting(update)
        await send_menu(update, context)
    else:
        await update.message.reply_text("ID를 입력해주세요:")
        return ASKING_ID


async def handle_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.text
    context.user_data["user_id"] = user_id
    await update.message.reply_text("비밀번호를 입력해주세요:")
    return ASKING_PASSWORD


async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_password = update.message.text
    user_id = context.user_data["user_id"]
    telegram_id = str(update.effective_user.id)

    # 데이터 저장
    save_user(telegram_id, user_id, user_password)
    await update.message.reply_text(
        f"정보가 저장되었습니다:\nID: {user_id}\nPassword: {user_password}"
    )

    # 등록 완료 후 메뉴 표시
    await send_menu(update, context)
    return ConversationHandler.END


# 버튼 클릭 시 콜백 처리 함수
# async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = update.callback_query
#     await query.answer()  # 버튼 클릭 시 로딩 효과 제거
#
#     telegram_id = str(query.from_user.id)
#     user_data = get_user(telegram_id)
#
#     if not user_data:
#         # 저장된 정보가 없는 경우
#         await query.message.reply_text("먼저 ID와 비밀번호를 등록해주세요. /start 명령어를 입력하세요.")
#         return
#
#     user_id, user_password = user_data
#
#     # 콜백 데이터에 따라 응답
#     if query.data == "1":
#         meal_info = await mealCrawling()
#         await query.message.reply_text(meal_info)
#     elif query.data == "2":
#         await display_notices(query)
#     elif query.data == "3":
#         await query.message.reply_text("사용자 맞춤 강의 추천 정보를 제공합니다.")
#     elif query.data == "4":
#         # 과제 크롤링 호출
#         todo_info = await todoCrawling(user_id, user_password)
#         await query.message.reply_text(todo_info)
#     elif query.data == "5":
#         await query.message.reply_text("졸업 인증 요건 정보를 확인하실 수 있습니다.")
#     elif query.data == "gpt":
#         # GPT와 대화 시작
#         await query.message.reply_text("GPT와 대화를 시작합니다. 질문을 입력해주세요:")
#         context.user_data["gpt_mode"] = True  # GPT 모드 활성화
#     else:
#         await query.message.reply_text("잘못된 선택입니다.")
#
#     # 버튼 다시 표시
#     await send_menu(query.message)

# 메뉴 버튼 생성 및 전송
# async def send_menu(message):
#     keyboard = [
#         [InlineKeyboardButton("1. 학식정보 확인", callback_data="1")],
#         [InlineKeyboardButton("2. 학사공지 확인", callback_data="2")],
#         [InlineKeyboardButton("3. 사용자 맞춤 강의추천", callback_data="3")],
#         [InlineKeyboardButton("4. 과제 및 전체적인 일정 확인", callback_data="4")],
#         [InlineKeyboardButton("5. 졸업인증 요건 확인", callback_data="5")],
#         [InlineKeyboardButton("6. GPT와 대화하기", callback_data="gpt")]
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#
#     # 버튼 메시지 전송
#     await message.reply_text(
#         "더 필요하신 기능을 선택해주세요!",
#         reply_markup=reply_markup,
#     )

# 공지사항 가져오기
def get_notices():
    notices = []

    # SSL 경고 비활성화
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        url = 'https://hknu.ac.kr/kor/562/subview.do'
        response = requests.get(url, headers=headers, verify=False)  # 임시로 https 인증 비활성화함

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # 공지사항 요소 선택
            notice_elements = soup.select(".board-table tbody tr")[:6]  # 상위 6개 공지사항

            for notice in notice_elements:
                cells = notice.find_all("td")
                if len(cells) >= 3:
                    title_element = cells[1].find("a")
                    writer_element = cells[2]
                    date_element = cells[3]

                    # 요소가 존재하는지 확인
                    if title_element and date_element and writer_element:
                        title = title_element.get_text(strip=True)
                        date = date_element.get_text(strip=True)
                        writer = writer_element.get_text(strip=True)
                        link = title_element['href']

                        if not link.startswith('http'):
                            link = f'https://hknu.ac.kr{link}'

                        title = title.replace('\n', '').replace('\t', '').strip()

                        notices.append({"title": title, "date": date, "writer": writer, "link": link})
                    else:
                        print("공지사항 정보가 누락되었습니다.")

        else:
            print(f"HTTP 요청 실패: 상태 코드 {response.status_code}")

    except Exception as e:
        print(f"Error: {e}")

    return notices


# 공지사항 출력
async def display_notices(query: CallbackQuery) -> None:
    notices = get_notices()
    if notices:
        result = "📢 [학사 공지 알림]\n"
        for i, notice in enumerate(notices, start=1):
            result += f"{i}. {notice['title']} [{notice['writer']}] [{notice['date']}]\n 자세히 보기: {notice['link']}\n\n"
        await query.message.reply_text(result)  # query.message를 사용
    else:
        await query.message.reply_text("공지사항을 가져오는 데 실패했습니다.")


async def mealCrawling():
    try:
        # 학식 페이지 URL 설정
        url = 'https://www.hknu.ac.kr/kor/670/subview.do'
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
        }

        # 페이지 요청
        response = requests.get(url, headers=headers, verify=False)  # 임시로 https 인증 비활성화함
        response.raise_for_status()

        # BeautifulSoup을 사용하여 HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')

        # 현재 날짜 구하기
        today = datetime.datetime.now().strftime("%Y.%m.%d")
        print(f"오늘 날짜: {today}\n")

        # 학식 테이블 검색
        diet_table = soup.select_one("table._dietCont")
        if not diet_table:
            return "오늘의 식단 정보를 찾을 수 없습니다."

        # 테이블의 모든 행을 가져옴
        rows = diet_table.find_all("tr")

        # 오늘 날짜의 식단만 출력
        current_date = None
        menu_dict = {}

        for row in rows:
            # 날짜 셀 찾기
            date_cell = row.find("th", class_="dietDate")
            if date_cell:
                current_date = date_cell.text.strip().split()[0]  # 날짜 부분만 추출 (예: "2024.10.28")

                # 오늘 날짜가 아닌 경우 무시
                if current_date != today:
                    current_date = None
                    continue

                if current_date not in menu_dict:
                    menu_dict[current_date] = []

            # 메뉴 정보가 포함된 셀 찾기
            menu_cells = row.find_all("td", class_=["dietNm", "dietCont"])
            if len(menu_cells) >= 2 and current_date is not None:  # 메뉴와 내용이 모두 존재하는 경우
                meal_type = menu_cells[0].text.strip()  # 식단 종류
                menu_content = menu_cells[1].text.strip()  # 식단 내용

                # 내용이 '등록된 식단내용이(가) 없습니다.'인 경우 무시
                if "등록된 식단내용이(가) 없습니다." not in menu_content:
                    formatted_menu_content = " ".join(menu_content.split())  # 항목을 공백으로 구분
                    menu_dict[current_date].append((meal_type, formatted_menu_content))

        # 오늘 날짜의 메뉴 출력
        if today in menu_dict:
            result = f"📅 날짜: {today}\n\n"
            for meal_type, menu_content in menu_dict[today]:
                # 식단 종류에 따라 이모티콘 추가
                if "천원의 아침밥" in meal_type:
                    meal_icon = "🥣"
                elif "맛난한끼" in meal_type:
                    meal_icon = "🍛"
                elif "건강한끼" in meal_type:
                    meal_icon = "🥗"
                else:
                    meal_icon = "🍽️"

                result += f"{meal_icon} {meal_type}\n{menu_content}\n\n"
        else:
            result = "오늘의 식단 정보가 없습니다."

        return result

    except Exception as e:
        return f"에러 발생: {e}"


# 과제 크롤링 함수 (Selenium 활용)
async def todoCrawling(user_id, user_password):
    # 크롬 옵션 설정
    options = webdriver.ChromeOptions()
    options.add_argument("headless")  # 창 숨김

    # 웹 드라이버 초기화
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # 로그인 페이지 열기
        url = 'https://cyber.hknu.ac.kr/ilos/main/member/login_form.acl'
        driver.get(url)

        # 아이디와 비밀번호 입력
        driver.find_element(By.ID, 'usr_id').send_keys(user_id)
        driver.find_element(By.ID, 'usr_pwd').send_keys(user_password)

        # 로그인 버튼 클릭
        driver.find_element(By.ID, 'login_btn').click()

        # Todo List 버튼 클릭
        todo_button = driver.find_element(By.XPATH, "//img[@alt='Todo List']")
        todo_button.click()

        # 팝업이 로드될 때까지 대기
        WebDriverWait(driver, 6).until(EC.visibility_of_element_located((By.ID, "todo_pop")))

        # 팝업 내용 추출
        todo_popup_text = driver.find_element(By.ID, "todo_pop").text

        # 불필요한 정보 필터링
        TodoList_storage = "\n".join([
            line for line in todo_popup_text.splitlines()
            if "수강과목" not in line
               and "비정규과목" not in line
               and "전체 수강 과목" not in line
               and "2024년" not in line
               and line.strip()
        ])

        todo_lines = [line.strip() for line in TodoList_storage.splitlines() if line.strip()]

        print(todo_lines)

        # 데이터 정리
        formatted_response = format_todo_list(todo_lines)
        return formatted_response

    except Exception as e:
        return f"에러 발생: {e}"
    finally:
        driver.quit()


def format_todo_list(lines):
    assignments, exams, projects, lectures = [], [], [], []

    # 텍스트를 분석하여 각 카테고리로 분류
    for i in range(1, len(lines), 3):
        title = lines[i]
        subject = lines[i + 1] if i + 1 < len(lines) else "과목 정보 없음"
        due_date = lines[i + 2] if i + 2 < len(lines) else "마감일 정보 없음"

        if "[과제]" in title:
            assignments.append(f"- {title}\n  - 과목: {subject}\n  - 마감일: {due_date}\n")
        elif "[시험]" in title:
            exams.append(f"- {title}\n  - 과목: {subject}\n  - 일시: {due_date}\n")
        elif "[팀프로젝트]" in title:
            projects.append(f"- {title}\n  - 과목: {subject}\n  - 마감일: {due_date}\n")
        elif "[온라인강의]" in title:
            lectures.append(f"- {title}\n  - 마감일: {due_date}\n")

    # 각 카테고리별 내용 또는 없음 메시지 생성
    response = "📋 과제 목록\n"
    response += "\n".join(assignments) if assignments else "제출할 과제가 없습니다.\n"

    response += "\n📝 시험 일정\n"
    response += "\n".join(exams) if exams else "예정된 시험이 없습니다.\n"

    response += "\n💼 팀프로젝트\n"
    response += "\n".join(projects) if projects else "진행 중인 팀프로젝트가 없습니다.\n"

    response += "\n🎥 온라인 강의\n"
    response += "\n".join(lectures) if lectures else "수강할 온라인 강의가 없습니다."

    return response


async def gpt(update, user_message):
    global context

    context += f"User: {user_message}\n"

    payload = {
        "service": "gpt",
        "question": context,
        "hash": ""
    }

    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False)
        response.raise_for_status()
        result = response.json()
        answer = result.get('answer')
        if answer:
            context += f"AI: {answer}\n"
            return answer
        else:
            await update.message.reply_text("AI 응답을 받을 수 없습니다. 잠시 후 다시 시도해 주세요.")
    except requests.exceptions.RequestException as e:
        await update.message.reply_text(f"오류 발생: {e}")


async def main():
    init_user_db()
    init_lecture_db()

    TOKEN = ""

    # 강의 데이터 수집
    print("강의 데이터를 수집중입니다...")
    fetch_lecture_data()
    print("강의 데이터 수집이 완료되었습니다!")

    app = ApplicationBuilder().token(TOKEN).build()

    # 대화 핸들러 설정
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASKING_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_id)],
            ASKING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password)],
        },
        fallbacks=[],
    )

    # 핸들러 등록
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("menu", send_menu))

    # 메뉴 선택 핸들러
    app.add_handler(MessageHandler(filters.Regex('^📋 학식정보 확인$'), meal_command))
    app.add_handler(MessageHandler(filters.Regex('^📢 학사공지 확인$'), notices_command))
    app.add_handler(MessageHandler(filters.Regex('^🎓 사용자 맞춤 강의추천$'), courses_command))
    app.add_handler(MessageHandler(filters.Regex('^📝 과제 및 일정 확인$'), tasks_command))
    app.add_handler(MessageHandler(filters.Regex('^🎓 졸업인증 요건 확인$'), graduation_command))
    app.add_handler(MessageHandler(filters.Regex('^🤖 GPT와 대화하기$'), gpt_command))

    # 강의 추천 관련 콜백 핸들러
    app.add_handler(CallbackQueryHandler(course_button, pattern="^course_"))
    app.add_handler(CallbackQueryHandler(case_button, pattern="^case_"))
    app.add_handler(CallbackQueryHandler(lecture_button, pattern="^lecture_"))

    # GPT 메시지 핸들러
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex('^(📋|📢|🎓|📝|🤖)'),
        gpt_message
    ))

    # 봇 명령어 메뉴 설정
    commands = [
        BotCommand("start", "계정을 등록합니다. (처음 사용자용)"),
        BotCommand("menu", "메뉴를 표시합니다.")
    ]
    await app.bot.set_my_commands(commands)

    await app.run_polling()


if __name__ == "__main__":
    generate_key()
    nest_asyncio.apply()
    asyncio.run(main())