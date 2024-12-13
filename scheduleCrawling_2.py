import time
import numpy as np
import textwrap
import matplotlib.pyplot as plt
from matplotlib import font_manager, rc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 한글 폰트 설정 (AppleGothic 사용)
rc('font', family='Pretendard')

# 음수 부호 깨짐 방지 (matplotlib 한글 문제 해결 시 필요한 경우)
plt.rcParams['axes.unicode_minus'] = False

# 아이디와 비밀번호 입력
# username = input('아이디를 입력해주세요: ')  # 실제 아이디 입력
# password = input('비밀번호를 입력해주세요: ')  # 실제 비밀번호 입력
username = ""
password = ""

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

    time.sleep(3)

    # 테이블 요소 찾기 (class='timetable'으로 가정)
    try:
        table = driver.find_element(By.XPATH, "//table")  # 구체적인 테이블 XPATH나 클래스로 변경 필요
        rows = table.find_elements(By.TAG_NAME, "tr")  # 각 행 추출

        timetable = []
        max_cols = 0  # 최대 열 개수를 추적

        # # 각 행에서 열을 추출하여 2차원 배열로 저장
        # for row in rows:
        #     cols = row.find_elements(By.TAG_NAME, "td")
        #     row_data = [col.text for col in cols]
        #     timetable.append(row_data)
        #     max_cols = max(max_cols, len(row_data))  # 가장 긴 열의 길이를 기록
        #
        # # 각 행에서 열을 추출하여 2차원 배열로 저장
        # for row in rows:
        #     cols = row.find_elements(By.TAG_NAME, "td")
        #     row_data = []
        #     for col in cols:
        #         text = col.text
        #         # 텍스트 형식 조정
        #         if "(" in text and ")" in text:
        #             parts = text.split(" ")
        #             if len(parts) >= 2:
        #                 new_text = f"{parts[0]}\n({parts[1]})\n{parts[2]}"
        #                 row_data.append(new_text)
        #             else:
        #                 row_data.append(text)
        #         else:
        #             row_data.append(text)
        #     timetable.append(row_data)
        #     max_cols = max(max_cols, len(row_data))  # 가장 긴 열의 길이를 기록
        #
        # # 각 행의 열 개수를 동일하게 맞추기 (빈 문자열 추가)
        # for row in timetable:
        #     while len(row) < max_cols:
        #         row.append('')  # 부족한 열을 빈 문자열로 채움
        #
        # # 터미널에 출력
        # for row in timetable:
        #     print(row)
        #
        # # 시간표를 numpy 배열로 변환
        # np_timetable = np.array(timetable)

        # 각 행에서 열을 추출하여 2차원 배열로 저장
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            row_data = []

            for col in cols:
                text = col.text
                # 텍스트 형식 조정
                if "(" in text and ")" in text:
                    parts = text.split(" ")
                    # parts의 길이가 3 이상인지 확인
                    if len(parts) >= 3:  # (공학1 316) 형식이 있을 것으로 가정
                        new_text = f"{parts[0]}\n({parts[1]})\n{parts[2]}"
                        row_data.append(new_text)
                    else:
                        row_data.append(text)  # 형식이 맞지 않으면 원본 텍스트 추가
                else:
                    row_data.append(text)  # 원본 텍스트 추가

            timetable.append(row_data)

        # 최대 열 개수를 찾기
        max_cols = max(len(row) for row in timetable)

        # 각 행의 열 개수를 동일하게 맞추기 (빈 문자열 추가)
        for row in timetable:
            while len(row) < max_cols:
                row.append('')  # 부족한 열을 빈 문자열로 채움

        # 터미널에 출력
        for row in timetable:
            print(row)

        # 시간표를 numpy 배열로 변환
        np_timetable = np.array(timetable, dtype=object)  # dtype을 object로 설정하여 다양한 길이의 배열 처리

        # # 시각화를 위한 준비
        # fig, ax = plt.subplots(figsize=(10, 12))  # figsize로 그래프 크기 조정
        # ax.set_title('학사 시간표')
        #
        # # 시간표의 크기를 얻음
        # num_rows, num_cols = np_timetable.shape
        #
        # # 표의 셀에 시간표 내용 채우기 (글자 크기 조정)
        # for i in range(num_rows):
        #     for j in range(num_cols):
        #         ax.text(j, num_rows-i-1, np_timetable[i, j], ha='center', va='center', fontsize=10)  # fontsize로 글자 크기 조정
        #
        # # 격자 그리기
        # ax.set_xticks(np.arange(num_cols))
        # ax.set_yticks(np.arange(num_rows))
        # ax.set_xticklabels([f"시간 {i+1}" for i in range(num_cols)], fontsize=10)  # x축 라벨 크기 조정
        # ax.set_yticklabels([f"요일 {i+1}" for i in range(num_rows)], fontsize=10)  # y축 라벨 크기 조정
        #
        # # 그리드 설정
        # ax.grid(True)
        #
        # # 셀 간의 간격을 넓힘 (x, y축 범위 조정)
        # plt.xticks(np.arange(num_cols), [f"시간 {i+1}" for i in range(num_cols)], fontsize=10)
        # plt.yticks(np.arange(num_rows), [f"요일 {i+1}" for i in range(num_rows)], fontsize=10)
        #
        # # 축 비율을 맞춤
        # ax.set_aspect('auto')
        #
        # # 표시
        # plt.tight_layout()  # 레이아웃 조정
        # plt.show()

        # 표 생성
        fig, ax = plt.subplots(figsize=(10, 8))  # 표 크기 조정

        ax.set_title('학사 시간표', fontsize=18, pad=20)  # 제목 설정

        # 표 셀에 텍스트 넣기
        num_rows, num_cols = np.shape(timetable)

        for i in range(num_rows):
            for j in range(num_cols):
                text = timetable[i][j]
                ax.text(j, num_rows - i - 1, text, ha='center', va='center', fontsize=12)

        # 그리드 생성
        ax.set_xticks(np.arange(-0.5, num_cols, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, num_rows, 1), minor=True)
        ax.grid(which='minor', color='black', linestyle='-', linewidth=1)

        # 레이아웃 조정
        plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)

        # 그래프 표시
        plt.show()

    except Exception as e:
        print("Error extracting timetable:", e)

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    driver.quit()
