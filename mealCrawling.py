from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import datetime

# 웹 드라이버 실행 (Chrome 예시)
driver = webdriver.Chrome()

# 웹 페이지 로드
driver.get('https://www.hknu.ac.kr/kor/670/subview.do')

# 페이지가 완전히 로드될 때까지 대기
time.sleep(2)

# 메뉴 아이템을 기다림
wait = WebDriverWait(driver, 10)
diet_table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table._dietCont")))

# 현재 날짜 구하기
today = datetime.datetime.now().strftime("%Y.%m.%d")
print(f"오늘 날짜: {today}\n")

# 테이블의 모든 행을 가져옴
rows = diet_table.find_elements(By.TAG_NAME, "tr")

# 오늘 날짜의 식단만 출력
current_date = None
menu_dict = {}

for row in rows:
    # 날짜 셀 찾기
    date_cell = row.find_elements(By.CSS_SELECTOR, "th.dietDate")
    if date_cell:
        current_date = date_cell[0].text.strip().split()[0]  # 날짜 부분만 추출 (예: "2024.10.28")

        # 오늘 날짜가 아닌 경우 무시
        if current_date != today:
            current_date = None
            continue

        if current_date not in menu_dict:
            menu_dict[current_date] = []

    # 메뉴 정보가 포함된 셀 찾기
    menu_cells = row.find_elements(By.CSS_SELECTOR, "td.dietNm, td.dietCont")
    if len(menu_cells) >= 2 and current_date is not None:  # 메뉴와 내용이 모두 존재하는 경우
        meal_type = menu_cells[0].text.strip()  # 식단 종류
        menu_content = menu_cells[1].text.strip()  # 식단 내용

        # 내용이 '등록된 식단내용이(가) 없습니다.'인 경우 무시
        if "등록된 식단내용이(가) 없습니다." not in menu_content:
            menu_dict[current_date].append((meal_type, menu_content))

# 오늘 날짜의 메뉴 출력
if today in menu_dict:
    print(f"📅 날짜: {today}\n")
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

        print(f"{meal_icon} {meal_type}\n{menu_content}\n")
    print("---\n")
else:
    print("오늘의 식단 정보가 없습니다.")

# 드라이버 종료
driver.quit()