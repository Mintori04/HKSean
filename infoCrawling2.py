from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Chrome 브라우저 열기
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

try:
    # 한경대학교 수강신청 사이트 접속
    driver.get("https://sugang.hknu.ac.kr/planLecture")

    # 첫 번째 조회 버튼이 로드될 때까지 대기 후 클릭
    first_search_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "btnRefresh"))
    )
    first_search_button.click()

    # 강의계획서 조회 버튼이 로드될 때까지 대기 후 클릭
    lecture_search_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "btn_find"))
    )
    lecture_search_button.click()

    # 강의계획서 조회 페이지가 로드되기를 대기
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "lectureList"))
    )

finally:
    # 드라이버 종료
    driver.quit()
