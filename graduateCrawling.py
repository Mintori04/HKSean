from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
import os
import olefile
import zlib
import struct
import pandas as pd
import re

# Chrome 옵션 설정
chrome_options = Options()
download_path = r""  # 사용자 PC에 맞게 다운로드 경로 설정

chrome_options.add_experimental_option("prefs", {
    "download.default_directory": download_path,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

# 브라우저 초기화 함수
def initialize_browser():
    s = Service('C:/chromedriver-win64/chromedriver.exe')
    driver = webdriver.Chrome(service=s, options=chrome_options)
    return driver

# 메인 크롤링 및 다운로드 함수
def download_file_from_page(driver, url, search_text, result_xpath, download_xpaths):
    """
    페이지에서 파일을 다운로드하는 함수.

    Parameters:
        driver: Selenium WebDriver 객체.
        url: 접근할 페이지 URL.
        search_text: 검색어.
        result_xpath: 검색 결과 클릭을 위한 XPath.
        download_xpaths: 다운로드할 파일 링크들의 XPath 목록.

    Returns:
        list: 다운로드된 파일명 목록.
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

    # 다운로드한 파일명을 저장할 리스트
    downloaded_file_names = []

    # 모든 파일 다운로드 클릭 및 텍스트 가져오기
    for download_xpath in download_xpaths:
        element = wait.until(EC.element_to_be_clickable((By.XPATH, download_xpath)))
        element_text = element.text.strip()
        element.click()
        downloaded_file_names.append(element_text)

    return downloaded_file_names

# 다운로드 상태 확인 함수
def wait_for_downloads(target_extensions=[".hwp", ".xlsx"], num_files=1):
    while True:
        time.sleep(1)
        downloaded_files = [f for f in os.listdir(download_path) if any(f.endswith(ext) for ext in target_extensions)]
        temp_files = [f for f in os.listdir(download_path) if f.endswith(".crdownload")]
        if len(downloaded_files) >= num_files and len(temp_files) == 0:
            return downloaded_files

def execute_course_history(file_path):
    driver = initialize_browser()
    try:
        data = []  # Selenium으로 추출한 데이터
        driver.get('https://cyber.hknu.ac.kr/ilos/main/member/login_form.acl')
        driver.find_element(By.ID, 'usr_id').send_keys("")  # 사용자 ID
        driver.find_element(By.ID, 'usr_pwd').send_keys("")  # 사용자 PW
        driver.find_element(By.ID, 'login_btn').click()

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//img[@val='coursesubject.png']"))).click()

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

        # 데이터 비교 및 출력 형식 개선
        print("\n[수강 내역]")
        print("----------------------------")
        for item in data:
            for _, row in comparison_data.iterrows():
                if row["과목명"] == item:
                    area = row["영역"] if pd.notna(row["영역"]) else "미분류"
                    print(f"{area:<15} {item}")  # 보기 좋게 정렬된 출력
                    break  # 일치 항목 발견 시 내부 루프 종료
        print("----------------------------")

    finally:
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
                filtered_rows_additional = df_additional[df_additional.iloc[:, 5].str.contains(keyword, na=False)]  # 두 번째 파일에서 6번째 열 검색

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

# 실행 시작
try:
    print("데이터를 가져오는 중...")
    driver = initialize_browser()

    # 첫 번째 파일 다운로드
    downloaded_files = download_file_from_page(
        driver,
        'https://www.hknu.ac.kr/hkcult/2488/subview.do',
        '학기 교양 교과목 시간표',
        "//a[@onclick=\"jf_viewArtcl('hkcult', '305', '77268')\"]",
        [
            "//a[@href='/bbs/hkcult/305/93820/download.do']",
            "//a[@href='/bbs/hkcult/305/92708/download.do']"  # 두 번째 다운로드 파일
        ]
    )
    wait_for_downloads(target_extensions=[".xlsx"], num_files=2)

    # 다운로드된 파일 경로 설정
    if len(downloaded_files) < 2:
        print("두 개의 파일을 모두 다운로드하지 못했습니다. 프로그램을 종료합니다.")
    else:
        downloaded_file_paths = [os.path.join(download_path, f) for f in downloaded_files]

        # 사용자 선택
        user_input = input("작업을 선택하세요 ('수강내역', '강의', '졸업인증'): ").strip()

        if user_input == "수강내역":
            execute_course_history(downloaded_file_paths[0])

        elif user_input == "강의":
            execute_lecture(downloaded_file_paths[0], downloaded_file_paths[1])

        elif user_input == "졸업인증":
            print("졸업인증 요건을 확인할 수 있는 페이지 입니다. \nhttps://www.hknu.ac.kr/hkcommath/2083/subview.do?enc=Zm5jdDF8QEB8JTJGYmJzJTJGaGtjb21tYXRoJTJGMjY4JTJGNzU5MDAlMkZhcnRjbFZpZXcuZG8lM0ZwYWdlJTNEMSUyNnNyY2hDb2x1bW4lM0QlMjZzcmNoV3JkJTNEJTI2YmJzQ2xTZXElM0QlMjZiYnNPcGVuV3JkU2VxJTNEJTI2cmdzQmduZGVTdHIlM0QlMjZyZ3NFbmRkZVN0ciUzRCUyNmlzVmlld01pbmUlM0RmYWxzZSUyNnBhc3N3b3JkJTNEJTI2")
        else:
            print("올바른 입력이 아닙니다.")
finally:
    driver.quit()
