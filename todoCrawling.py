import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ChromeDriver 경로를 Service로 설정
service = Service('/usr/local/bin/chromedriver')
driver = webdriver.Chrome(service=service)

try:
    # 페이지 열기
    url = 'https://cyber.hknu.ac.kr/ilos/main/member/login_form.acl'
    driver.get(url)

    # Ajax로 동적으로 로드되는 데이터 기다리기
    time.sleep(3)

    # 아이디와 비밀번호 입력
    username = int(input('아이디를 입력해주세요: '))  # 실제 아이디 입력
    password = input('비밀번호를 입력해주세요: ')  # 실제 비밀번호 입력

    # 아이디 입력란에 값 입력
    driver.find_element(By.ID, 'usr_id').send_keys(username)

    # 비밀번호 입력란에 값 입력
    driver.find_element(By.ID, 'usr_pwd').send_keys(password)

    # 로그인 버튼 클릭
    login_button = driver.find_element(By.ID, 'login_btn')
    login_button.click()

    # 로그인 이후 페이지가 로드될 시간을 기다리기
    time.sleep(5)

    # Todo List 버튼 클릭
    todo_button = driver.find_element(By.XPATH, "//img[@alt='Todo List']")
    todo_button.click()

    # Todo List 팝업이 로드될 시간을 기다리기
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "todo_pop")))

    # Todo List 팝업 텍스트 추출
    time.sleep(3)  # 팝업이 완전히 로드될 시간을 보장하기 위한 추가 대기 시간
    todo_popup_text = driver.find_element(By.ID, "todo_pop").text

    # "수강 과목", "비정규과목" 관련된 내용 필터링
    TodoList_storage = "\n".join([line for line in todo_popup_text.splitlines()
                                  if "수강과목" not in line
                                  and "비정규과목" not in line
                                  and "전체 수강 과목" not in line
                                  and "2024년" not in line
                                  and line.strip()])

    # Todo List 텍스트가 잘 저장되었는지 확인
    if TodoList_storage.strip():
        print("Todo List에 저장된 내용:")
        print(TodoList_storage)  # Todo List 내용 출력
    else:
        print("No Todo items found or filtered out.")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    driver.quit()
