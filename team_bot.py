from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime
import time
import pytz
import os

# ====== Thông tin đăng nhập và cấu hình ======
# Khuyên dùng os.environ.get để bảo mật, hoặc điền trực tiếp nếu chạy local
email = os.environ.get('TEAMS_EMAIL') or "tech.qtdata@gmail.com"
password = os.environ.get('TEAMS_PASSWORD') or "passnotE@1234"
message_content = "Thông báo: Reset 15min (Giải lao)"
local_tz = pytz.timezone("Asia/Ho_Chi_Minh")

# Danh sách nhóm (Đã cập nhật các nhóm mới)
groups = [
    "BoomWTF..AiLàmViệcRiêng*ThựcNÃO*ProofFileNGAY",
    "iX000s iSSale Boom&Task_1h TTS AA POSITIVE iShowOff/Top-iUp",
    "iX000s iSSale Boom CMT*iHugeNewRev*Top-iUp",
    "iX000s iSSale AU GlobalGroup.NỆN*iHugeNewRev*TiUp",
    "iX000s iSSale Boom QT*iHugeNewRev*Top-iUp",
    "iX000s iSSale AH GlobalGroup.NỆN*iHugeNewRev*TiUp",
    "SAM Foundation TTSVol",
    "iX000s iSSale Boom&Task_1h TTS NB POSITIVE iShowOff/Top-iUp",
    "iX000s iSSale Boom&Task_1h TTS TAHK Foundation POSITIVE iShowOff/Top-iUp"
]

def login():
    import tempfile
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Chạy ẩn danh trên GitHub Actions
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ) # Cập nhật User-Agent mới nhất của Chrome 120 để tránh bị nhận diện là bot
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # --- THÊM ĐOẠN NÀY ĐỂ VƯỢT RÀO MICROSOFT ---
    # Tắt thông báo "Chrome is being controlled..." và ẩn danh tính bot
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Cho phép tất cả Cookie (Teams cực kỳ cần cái này để không bị văng)
    prefs = {"profile.cookie_controls_mode": 0,
             "credentials_enable_service": False,      # Tắt popup hỏi lưu pass
             "profile.password_manager_enabled": False # Tắt trình quản lý mật khẩu
             } 
    
    options.add_experimental_option("prefs", prefs)
    # -------------------------------------------
    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'credentials', {
                    get: () => undefined
                });

                window.PublicKeyCredential = undefined;
            """
        }
    )
    driver.get("https://teams.live.com/v2/")
    wait = WebDriverWait(driver, 25)

    try:
        # Bước 1: Click Sign in
        sign_in_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Sign in")]')))
        sign_in_btn.click()
        
        # Bước 2: Nhập Email
        email_input = wait.until(EC.presence_of_element_located((By.ID, "usernameEntry")))
        email_input.send_keys(email)
        email_input.send_keys(Keys.RETURN)
        time.sleep(3)

        # Bước 3: Xử lý nút 'Use your password' nếu có
        try:
            use_pass_btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Use your password")]'))
            )
            use_pass_btn.click()
        except:
            pass

        # Bước 4: Nhập Password
        pass_input = wait.until(EC.presence_of_element_located((By.ID, "passwordEntry")))
        pass_input.send_keys(password)
        pass_input.send_keys(Keys.RETURN)
        
       # ... [Giữ nguyên code từ Bước 1 đến Bước 5] ...

        # Bước 5: Vượt qua các màn hình phụ (Stay signed in / No)
        try:
            no_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="secondaryButton"]'))
            )
            no_btn.click()
        except:
            pass

        print("⏳ Đang chờ Microsoft Teams load giao diện...")
        time.sleep(10) # Chờ 10s xem Teams điều hướng đi đâu
        
        # --- THÊM BƯỚC 6 VÀO ĐÂY ---
        # --- CẬP NHẬT LẠI BƯỚC 6 VÀ BƯỚC 7 ---
       # Bước 6: Xử lý nếu Teams hiện lỗi "We've run into an issue"
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//*[contains(text(), "Retry") or contains(., "Retry")]'))
            )
            print("🔄 Phát hiện lỗi hệ thống. Đang ép trình duyệt tải lại trang (F5)...")
            time.sleep(2)
            
            # --- Cách tải lại trang chống Timeout ---
            try:
                # Chỉ cho phép trang tải tối đa 40 giây
                driver.set_page_load_timeout(40) 
                # Dùng Javascript để điều hướng thay vì driver.get()
                driver.execute_script("window.location.replace('https://teams.live.com/v2/');")
            except Exception as load_e:
                print("⏳ Trang Teams tải hơi lâu, bỏ qua chờ đợi và tiếp tục chạy...")
            # ----------------------------------------
            
            time.sleep(15) # Chờ Teams load lại giao diện
        except:
            pass # Nếu không bị lỗi này thì cứ đi tiếp
        # Bước 7: Xử lý lỗi văng lại màn hình Welcome
        try:
            sign_in_again = driver.find_element(By.XPATH, '//button[contains(., "Sign in")]')
            print("🔄 Phát hiện bị văng lại màn hình chờ, đang click Sign in lần 2...")
            sign_in_again.click()
            time.sleep(15) 
        except:
            pass # Không tìm thấy nút Sign in nữa, hy vọng là đã vào được chat!
        # -------------------------------------

        print("✅ Đăng nhập hoàn tất!")
        time.sleep(5) 
        return driver
        
    except Exception as e:
        print(f"❌ Lỗi đăng nhập: {e}")
        # Nếu ở bước trước bạn đã thêm driver.save_screenshot("error_login.png") thì cứ giữ nguyên nhé
        driver.quit()
        return None

def open_chat_with_scroll(driver, chat_name):
    """Hàm tìm chat có hỗ trợ cuộn chuột nếu không thấy tên nhóm"""
    wait = WebDriverWait(driver, 15)
    try:
        # Thử tìm trực tiếp xem nhóm có hiện sẵn không
        try:
            xpath = f"//span[contains(normalize-space(), '{chat_name}')]"
            chat_element = driver.find_element(By.XPATH, xpath)
        except:
            print(f"🔄 Đang cuộn danh sách để tìm nhóm: {chat_name}")
            # Tìm vùng chứa danh sách chat để thực hiện scroll
            container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-tid="message-pane-list-runway"]')))
            
            found = False
            for _ in range(10): # Cuộn tối đa 10 lần
                driver.execute_script("arguments[0].scrollTop += 600;", container)
                time.sleep(1.5)
                try:
                    chat_element = driver.find_element(By.XPATH, xpath)
                    if chat_element.is_displayed():
                        found = True
                        break
                except:
                    continue
            
            if not found:
                raise Exception("Không tìm thấy tên nhóm sau khi cuộn")

        # Click vào nhóm
        driver.execute_script("arguments[0].scrollIntoView(true);", chat_element)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", chat_element)
        print(f"📂 Đã mở nhóm: {chat_name}")
        time.sleep(3)
        return True
    except Exception as e:
        print(f"⚠️ Không thể tìm thấy nhóm '{chat_name}': {e}")
        return False

def send_message(driver):
    try:
        # Tìm ô nhập tin nhắn
        msg_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
        )
        msg_box.send_keys(message_content)
        msg_box.send_keys(Keys.ENTER)
        print("🚀 Đã gửi tin nhắn thành công.")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Lỗi khi gửi tin nhắn: {e}")

def job_wrapper():
    driver = login()
    if not driver:
        return

    for group in groups:
        print(f"\n--- Xử lý nhóm: {group} ---")
        if open_chat_with_scroll(driver, group):
            send_message(driver)
        
    print("\n✅ Hoàn tất tất cả các nhóm!")
    driver.quit()

if __name__ == "__main__":
    # Bạn có thể thêm logic kiểm tra giờ ở đây nếu chạy Cron 24/7
    # now = datetime.now(local_tz)
    # if (now.hour, now.minute) in [(9, 45), (15, 15)]:
    job_wrapper()
