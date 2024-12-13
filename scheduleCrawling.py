import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 아이디와 비밀번호 입력
username = input('아이디를 입력해주세요: ')  # 실제 아이디 입력
password = input('비밀번호를 입력해주세요: ')  # 실제 비밀번호 입력

# ChromeDriver 경로를 Service로 설정
service = Service('/usr/local/bin/chromedriver')
driver = webdriver.Chrome(service=service)

try:
    # 페이지 열기
    url = 'https://cyber.hknu.ac.kr/ilos/main/member/login_form.acl'
    driver.get(url)

    # Ajax로 동적으로 로드되는 데이터 기다리기
    time.sleep(1)

    # 아이디 입력란에 값 입력
    driver.find_element(By.ID, 'usr_id').send_keys(username)

    # 비밀번호 입력란에 값 입력
    driver.find_element(By.ID, 'usr_pwd').send_keys(password)

    # 로그인 버튼 클릭
    login_button = driver.find_element(By.ID, 'login_btn')
    login_button.click()

    # 로그인 이후 페이지가 로드될 시간을 기다리기
    time.sleep(2)

    # 링크 클릭 (학사 시간표 페이지)
    timetable_link = driver.find_element(By.XPATH, "//a[@href='/ilos/st/main/pop_academic_timetable_form.acl']")
    timetable_link.click()

    # 학사 시간표 페이지가 로드될 시간을 기다리기
    WebDriverWait(driver, 15).until(EC.new_window_is_opened)

    # 학사 시간표 창으로 전환
    driver.switch_to.window(driver.window_handles[-1])

    time.sleep(10)

    # 학사 시간표 창에서 추가 작업을 수행할 수 있습니다.

except Exception as e:
    print(f"An error occurred: {e}")