from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time

# 데이터 수집을 위한 브라우저 초기화 함수
def initialize_browser():
    # ChromeDriver 경로를 본인의 경로로 설정합니다.
    service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service)
    return driver

data = []  # 각 프로세스의 독립적인 데이터 리스트

driver = initialize_browser()
driver.get('https://info.hknu.ac.kr/intro/index.html#/login')
driver.implicitly_wait(10)

# 로그인
login_id = driver.find_element(By.CSS_SELECTOR, 'input.idInput')
login_id.send_keys('')
login_pwd = driver.find_element(By.CSS_SELECTOR, 'input.pwInput')
login_pwd.send_keys('')
login_button = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btnLogin'))
)
login_button.click()

try:
    # '예' 버튼 확인 및 클릭
    yes_button = driver.find_element(By.CSS_SELECTOR, 'div#mainframe\\.login\\.form\\.btn_yes\\:icontext')
    if yes_button.is_displayed():
        yes_button.click()
        print("예 버튼을 클릭했습니다.")
    else:
        print("예 버튼이 보이지 않습니다.")
except NoSuchElementException:
    print("예 버튼이 존재하지 않습니다.")

# 검색 및 강의계획서 선택
toggle_element = driver.find_element(By.ID, 'mainframe.VFrameSet.HFrameSet.SubButtonFrame.form.div_toggle.form.stt_togle')
toggle_element.click()
driver.implicitly_wait(10)

search_input = driver.find_element(By.ID, 'mainframe.VFrameSet.HFrameSet.SubFrame.form.div_sub.form.div_searchBackground.form.edt_search:input')
search_input.click()
search_input.send_keys('강의계획서')
search_input.send_keys(Keys.ENTER)
driver.implicitly_wait(10)

search_item = driver.find_element(By.ID, 'mainframe.VFrameSet.HFrameSet.SubFrame.form.PopupDiv00.form.ListBox00.item_0:text')
search_item.click()

# 조회 버튼 클릭
try:
    search_icon = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "mainframe.VFrameSet.HFrameSet.VFrameSet.WorkFrameSet.w_1310337.form.tit_main._btn_default_search:icontext"))
    )
    search_icon.click()
    print("조회 아이콘을 클릭했습니다.")
except TimeoutException:
    print("Timeout: 조회 버튼을 찾을 수 없습니다.")

# 방법 1: Keys.END를 사용하여 스크롤 이동
scrollable_area = driver.find_element(By.ID, 'mainframe.VFrameSet.HFrameSet.VFrameSet.WorkFrameSet.w_1310337.form.div_work.form.grd_main.hscrollbar.trackbar')
scrollable_area.send_keys(Keys.END)

# 방법 2: JavaScript를 사용하여 스크롤 위치를 오른쪽 끝으로 설정
driver.execute_script("arguments[0].scrollLeft = arguments[0].scrollWidth", scrollable_area)

time.sleep(5)
driver.quit()
