import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

# /start 명령어 처리 함수
async def start(update: Update, context) -> None:
    # 버튼 생성
    keyboard = [
        [InlineKeyboardButton("1. 학식정보 확인", callback_data="1")],
        [InlineKeyboardButton("2. 사용자 맞춤 강의추천", callback_data="2")],
        [InlineKeyboardButton("3. 과제 및 전체적인 일정 확인", callback_data="3")],
        [InlineKeyboardButton("4. 졸업인증 요건 확인", callback_data="4")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 사용자에게 버튼 메시지 전송
    await update.message.reply_text(
        "안녕하세요. HK챗봇입니다! \n\n"
        "한경대학교에 관한 정보들을 실시간으로 학습하고 원하시는 정보를 말씀해주시면 답변해드리겠습니다!! \n\n"
        "다음 선택지는 저의 주된 기능들이며 선택하여 이용하실 수 있습니다!!",
        reply_markup=reply_markup,
    )

# 학식 정보 가져오기 함수
async def get_meal_info():
    url = "https://www.hknu.ac.kr/kor/670/subview.do"
    response = requests.get(url, verify=False)
    soup = BeautifulSoup(response.text, "html.parser")

    # 요일별 식단 정보 수집
    result = []
    days = soup.select("th.dietDate")
    for day in days:
        date = day.get_text()

        # '토' 또는 '일'이 포함된 날짜는 스킵
        if "토" in date or "일" in date:
            continue

        result.append(f"날짜: {date}")
        sibling = day.find_next("td", class_="dietNm")  # 첫 번째 식단 항목을 찾음
        while sibling:
            meal_name = sibling.get_text(strip=True)
            meal_content = sibling.find_next_sibling("td", class_="dietCont")

            if meal_content:
                meal_content = meal_content.get_text("\n", strip=True)

            result.append(f"{meal_name}:\n{meal_content}\n")
            sibling = sibling.find_next("td", class_="dietNm")

            if not sibling or sibling.find_previous("th", class_="dietDate") != day:
                break

    return "\n".join(result) if result else "학식 정보를 가져올 수 없습니다."

# 버튼 클릭 시 콜백 처리 함수
async def button_handler(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()  # 버튼 클릭 시 로딩 효과 제거

    # 콜백 데이터에 따라 응답
    if query.data == "1":
        meal_info = await get_meal_info()  # 학식 정보 가져오기
        await query.message.reply_text(meal_info)  # 학식 정보를 메시지로 전송
    elif query.data == "2":
        await query.message.reply_text("사용자 맞춤 강의 추천 정보를 제공합니다.")
    elif query.data == "3":
        await query.message.reply_text("과제 및 전체적인 일정 정보를 확인하실 수 있습니다.")
    elif query.data == "4":
        await query.message.reply_text("졸업 인증 요건 정보를 확인하실 수 있습니다.")
    else:
        await query.message.reply_text("잘못된 선택입니다.")

    # 버튼 다시 표시
    await send_menu(query.message)

# 메뉴 버튼 생성 및 전송
async def send_menu(message):
    keyboard = [
        [InlineKeyboardButton("1. 학식정보 확인", callback_data="1")],
        [InlineKeyboardButton("2. 사용자 맞춤 강의추천", callback_data="2")],
        [InlineKeyboardButton("3. 과제 및 전체적인 일정 확인", callback_data="3")],
        [InlineKeyboardButton("4. 졸업인증 요건 확인", callback_data="4")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 버튼 메시지 전송
    await message.reply_text(
        "더 필요하신 기능을 선택해주세요!",
        reply_markup=reply_markup,
    )

if __name__ == '__main__':
    # 봇 토큰
    TOKEN = ""

    # 애플리케이션 생성
    app = ApplicationBuilder().token(TOKEN).build()

    # 핸들러 추가
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # 봇 실행
    app.run_polling()
