import base64
from datetime import datetime
import json
import os
import tempfile
import time
import zlib

import pytz
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# ====== Thông tin đăng nhập và cấu hình ======
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


def load_session_data():
    encoded = os.environ.get("TEAMS_SESSION")
    if not encoded and os.path.exists("teams_session.txt"):
        with open("teams_session.txt", "r", encoding="utf-8") as f:
            encoded = f.read().strip()
    if not encoded:
        return None
    raw_bytes = zlib.decompress(base64.b64decode(encoded))
    return json.loads(raw_bytes.decode("utf-8"))


def login():
    session_data = load_session_data()
    if not session_data:
        print("❌ Không tìm thấy TEAMS_SESSION hoặc file teams_session.txt!")
        return None

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Chạy ẩn danh trên GitHub Actions
    options.add_argument("--lang=en-GB")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    prefs = {
        "profile.cookie_controls_mode": 0,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")

    # Trên Windows local ưu tiên dùng driver đã tải sẵn để tránh timeout mạng; trên GitHub dùng ChromeDriverManager
    local_driver = os.path.join(
        os.environ.get("APPDATA", ""), "undetected_chromedriver", "undetected_chromedriver.exe"
    )
    if os.name == "nt" and os.path.exists(local_driver):
        driver = webdriver.Chrome(service=Service(local_driver), options=options)
    else:
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

    try:
        print("⏳ Đang nạp session đăng nhập Microsoft Teams...")
        driver.execute_cdp_cmd("Network.enable", {})

        allowed_keys = {
            "name", "value", "domain", "path", "secure", "httpOnly", "sameSite", "expires", "priority"
        }
        clean_cookies = []
        for c in session_data.get("cookies", []):
            item = {k: v for k, v in c.items() if k in allowed_keys and v is not None}
            if item.get("expires", 1) <= 0:
                item.pop("expires", None)
            clean_cookies.append(item)

        driver.execute_cdp_cmd("Network.setCookies", {"cookies": clean_cookies})

        # Mở Teams lần 1
        driver.get("https://teams.live.com/v2/")
        time.sleep(3)

        # Nạp localStorage nếu có
        local_storage = session_data.get("localStorage", {})
        if local_storage:
            for k, v in local_storage.items():
                driver.execute_script(
                    "window.localStorage.setItem(arguments[0], arguments[1]);", k, v
                )
            driver.get("https://teams.live.com/v2/")

        # Nếu trang Welcome hiện nút Sign in -> bấm 1 cái để kích hoạt SSO từ cookie sẵn có
        try:
            sso_btn = WebDriverWait(driver, 6).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(., "Sign in")]'))
            )
            print("🔄 Bấm Sign in để kích hoạt SSO từ cookie...")
            sso_btn.click()
        except Exception:
            pass

        # Xử lý nếu Teams hiện lỗi tạm thời "Retry"
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, '//*[contains(text(), "Retry")]'))
            )
            print("🔄 Phát hiện màn hình Retry, tải lại trang...")
            try:
                driver.set_page_load_timeout(40)
                driver.execute_script("window.location.replace('https://teams.live.com/v2/');")
            except Exception:
                pass
        except Exception:
            pass

        # Chờ thực sự thấy danh sách nhóm xuất hiện (tránh miss 2 nhóm đầu do load chậm)
        target_chat_xpath = " | ".join(
            [f"//span[contains(normalize-space(), '{g}')]" for g in groups]
        )
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.XPATH, target_chat_xpath))
        )

        print("✅ Đăng nhập bằng Session hoàn tất & Teams đã load xong!")
        driver.save_screenshot("team_after_login.png")
        return driver

    except Exception as e:
        driver.save_screenshot("team_error_login.png")
        print(f"❌ Lỗi đăng nhập bằng Session (có thể session đã hết hạn): {e}")
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
        except Exception:
            print(f"🔄 Đang cuộn danh sách để tìm nhóm: {chat_name}")
            container = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-tid="message-pane-list-runway"]'))
            )

            found = False
            for _ in range(10):
                driver.execute_script("arguments[0].scrollTop += 600;", container)
                time.sleep(1.5)
                try:
                    chat_element = driver.find_element(By.XPATH, xpath)
                    if chat_element.is_displayed():
                        found = True
                        break
                except Exception:
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
        msg_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
        )
        msg_box.send_keys(message_content)
        msg_box.send_keys(Keys.ENTER)
        print("🚀 Đã gửi tin nhắn thành công.")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Lỗi khi gửi tin nhắn: {e}")


def is_valid_break_time():
    now = datetime.now(local_tz)
    print(f"🕒 Giờ Việt Nam hiện tại: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        print("🛠️ Chạy thủ công (workflow_dispatch) -> Bỏ qua kiểm tra khung giờ.")
        return True

    # Nếu công ty nghỉ Chủ Nhật, bỏ comment khối dưới:
    # if now.weekday() == 6:
    #     print("📅 Hôm nay là Chủ Nhật -> Bỏ qua.")
    #     return False

    current_minutes = now.hour * 60 + now.minute

    # Khung sáng: 09:40 - 10:00; khung chiều: 15:10 - 15:30.
    morning_ok = (9 * 60 + 40) <= current_minutes <= (10 * 60)
    afternoon_ok = (15 * 60 + 10) <= current_minutes <= (15 * 60 + 30)

    if not (morning_ok or afternoon_ok):
        print("⛔ Ngoài khung giờ giải lao (09:40-10:00 hoặc 15:10-15:30). Hủy gửi tin nhắn!")
        return False

    return True


def job_wrapper():
    if not is_valid_break_time():
        return

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
    job_wrapper()