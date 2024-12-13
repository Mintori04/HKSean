from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time

# Service 객체 생성
service = Service(executable_path='/usr/local/bin/chromedriver')

# WebDriver 생성
driver = webdriver.Chrome(service=service)

# 페이지 열기
url = 'https://info.hknu.ac.kr/nxui/index.html'
driver.get(url)

# Ajax로 동적으로 로드되는 데이터 기다리기
time.sleep(3)  # 필요 시 더 기다릴 수 있음

driver.implicitly_wait(5) #화면이 나올 때까지 대기
login_id = driver.find_element(By.CSS_SELECTOR, 'input.idInput')
login_id.send_keys('')
login_pwd = driver.find_element(By.CSS_SELECTOR, 'input.pwInput')
login_pwd.send_keys('')
driver.implicitly_wait(5)
login_button = WebDriverWait(driver, 30).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.btnLogin'))
)
login_button.click()

time.sleep(10)


# favbutton = driver.find_element(By.ID, 'mainframe.VFrameSet.TopFrame.form.div_top.form.btn_myMenu')
# favbutton.click()
#
# time.sleep(3)
#
# fav = driver.find_element(By.ID, 'mainframe.VFrameSet.TopFrame.form.pdv_mymenu.form.grd_mymenu.body.gridrow_1.cell_1_0.celltreeitem.treeitemtext')
# fav.click()

toggle_element = WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.ID, 'mainframe.VFrameSet.HFrameSet.SubButtonFrame.form.div_toggle.form.stt_togle'))
)

toggle_element.click()

search_input = WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.ID, 'mainframe.VFrameSet.HFrameSet.SubFrame.form.div_sub.form.div_searchBackground.form.edt_search'))  # 'id'로 선택
)

time.sleep(5)

search_input.click()
search_input.send_keys('강의계획서조회')
search_input.send_keys(Keys.ENTER)

time.sleep(1)

search_button = driver.find_element(By.ID, 'mainframe.VFrameSet.HFrameSet.SubFrame.form.PopupDiv00.form.ListBox00.item_0')
search_button.click()

time.sleep(10)

# 페이지에서 필요한 데이터 추출
# element = driver.find_element_by_id('mainframe.gwamok_popup.form.tab_master.tab_classPlan.form.grd_detail03.body.gridrow_0.cell_0_0:text')  # 필요한 요소의 ID나 XPath 사용
# print(element.text)

# 브라우저 종료
# driver.quit()
