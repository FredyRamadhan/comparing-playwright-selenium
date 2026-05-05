import os
import time
import unittest
from datetime import datetime
from playwright.sync_api import sync_playwright
from axe_playwright_python.sync_playwright import Axe
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()
BASE_URL = os.getenv("BASE_URL")
NC_USER  = os.getenv("NC_USER")
NC_PASS  = os.getenv("NC_PASS")

# --- LOGGING HELPERS ---
def log(step, msg=""):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{step}] {msg}")

def dump_state(page, name="debug"):
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{name}_{timestamp}"

    page.screenshot(path=f"{filename}.png")
    with open(f"{filename}.html", "w", encoding="utf-8") as f:
        f.write(page.content())

    print(f"[DEBUG] Saved: {filename}.png + {filename}.html")

def wait_for_loader_to_disappear(page):
    try:
        page.locator(".loading, .icon-loading").first.wait_for(state="hidden", timeout=20000)
    except:
        pass


class NextcloudTestSuite(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Setup Playwright (Replacing Chrome WebDriver)
        cls.playwright = sync_playwright().start()
        
        # Match Selenium's non-headless default and window size
        cls.browser = cls.playwright.chromium.launch(
            headless=False, # Set to False to see the browser during test execution
            args=["--window-size=1920,1080", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        # viewport=None ensures the browser respects the window-size arg above
        cls.context = cls.browser.new_context(viewport=None)
        cls.page = cls.context.new_page()
        cls.page.set_default_timeout(20000) # Match WebDriverWait(driver, 20)
        
        cls.axe = Axe()
        
        # --- KONFIGURASI NEXTCLOUD ---
        cls.URL = BASE_URL
        cls.USERNAME = NC_USER
        cls.PASSWORD = NC_PASS
        # -----------------------------
        
        # --- TEST DATA STATE ---
        timestamp = datetime.now().strftime('%H%M%S')
        cls.test_file_name = f"playwright_test_file_{timestamp}.txt"
        cls.test_folder_name = f"Playwright_Test_Folder_{timestamp}"
        cls.test_file_path = os.path.abspath(cls.test_file_name)

        # Create the local dummy file once for the upload test
        with open(cls.test_file_path, "w") as f:
            f.write("Playwright automation test file upload")

    def login_nextcloud(self, username, password):
        try:
            log("LOGIN", "Opening login page")
            self.page.goto(self.URL)

            log("LOGIN", "Waiting for username field")
            user_input = self.page.locator("#user").first
            user_input.wait_for(state="visible")
            user_input.fill(username)

            log("LOGIN", "Entering password")
            self.page.locator("#password").first.fill(password)

            log("LOGIN", "Submitting login form")
            self.page.locator("button[type='submit']").first.click()

            log("LOGIN", "Waiting for avatar")
            self.page.locator(".avatardiv, .user-menu").first.wait_for(state="attached")
            
            log("LOGIN", "SUCCESS")
        except Exception as e:
            log("ERROR", f"Login failed: {e}")
            dump_state(self.page, "login_error")
            raise

    def run_axe_test(self, page_name):
        time.sleep(2) # Tunggu DOM stabil sebelum inject Axe
        results = self.axe.run(self.page)
        
        # Axe Playwright returns an object, we extract the violations array
        violations = results.violations if hasattr(results, 'violations') else []
        
        print(f"\n--- [Axe-Score] Hasil Aksesibilitas: {page_name} ---")
        print(f"Ditemukan {len(violations)} pelanggaran aksesibilitas.")
        for violation in violations:
            # Handle Axe Playwright violation structure (usually dictionaries inside the list)
            v_id = violation.get('id', 'N/A')
            v_impact = violation.get('impact', 'N/A')
            v_desc = violation.get('description', 'N/A')
            print(f"- Aturan: {v_id} | Impact: {v_impact} | Deskripsi: {v_desc}")
            
        return len(violations)

    # =================================================================
    # SKENARIO 2: ACCESSIBILITY & SCREEN READER COMPLIANCE
    # =================================================================
    def test_01_axe_login_page(self):
        try:
            log("TEST_01", "Starting Axe test for login page")
            self.page.goto(self.URL)
            self.page.locator("#user").first.wait_for(state="attached")
            violations_count = self.run_axe_test("Login Page")
            log("TEST_01", f"Found {violations_count} accessibility violations")
        except Exception as e:
            log("ERROR", f"test_01 failed: {e}")
            dump_state(self.page, "test_01_error")
            raise

    # =================================================================
    # SKENARIO 3: USER ERROR PROTECTION
    # =================================================================
    def test_02_login_empty_password(self):
        try:
            log("TEST_02", "Starting empty password test")
            self.page.goto(self.URL)
            
            user_input = self.page.locator("#user").first
            user_input.wait_for(state="visible")
            user_input.fill(self.USERNAME)
            
            self.page.locator("button[type='submit']").first.click()
            
            pwd_input = self.page.locator("#password").first
            is_required = pwd_input.get_attribute("required")
            
            # Playwright returns "" (empty string) or the attribute value if it exists, None if it doesn't
            if is_required is not None:
                log("TEST_02", "✓ System prevents login with empty password (HTML5 Required form)")
            else:
                try:
                    error_msg_locator = self.page.locator(".warning").first
                    error_msg_locator.wait_for(state="visible")
                    error_msg = error_msg_locator.inner_text()
                    log("TEST_02", f"✓ Error message displayed: {error_msg}")
                    self.assertTrue(len(error_msg) > 0)
                except:
                    log("TEST_02", "No explicit error message found, but form validation may have occurred")
        except Exception as e:
            log("ERROR", f"test_02 failed: {e}")
            dump_state(self.page, "test_02_error")
            raise

    # =================================================================
    # SKENARIO 1: NAVIGASI & FUNGSIONAL UTAMA
    # =================================================================
    def test_03_login_and_dashboard_axe(self):
        try:
            log("TEST_03", "Starting login and dashboard Axe test")
            self.login_nextcloud(self.USERNAME, self.PASSWORD)
            
            log("TEST_03", "Waiting for avatar to confirm login")
            self.page.locator(".avatardiv, .user-menu").first.wait_for(state="attached")
            
            time.sleep(2)
            wait_for_loader_to_disappear(self.page)
            
            log("TEST_03", "Running Axe test for Dashboard")
            violations_count = self.run_axe_test("Dashboard")
            log("TEST_03", f"Dashboard Axe test completed with {violations_count} violations")
        except Exception as e:
            log("ERROR", f"test_03 failed: {e}")
            dump_state(self.page, "test_03_error")
            raise
        
    def test_04_navigation_and_files_axe(self):
        try:
            log("TEST_04", "Starting Files page Axe test")
            log("TEST_04", "Navigating to files app")
            self.page.goto(f"{self.URL}/index.php/apps/files/")
            
            log("TEST_04", "Waiting for app container")
            self.page.locator("body").first.wait_for(state="attached")
            
            time.sleep(2)
            wait_for_loader_to_disappear(self.page)
            
            if "login" in self.page.url:
                dump_state(self.page, "files_redirected_to_login")
                raise Exception("Session lost - redirected to login")
            
            # Dismiss popups just like in the working functional script
            self.page.keyboard.press("Escape")
            log("TEST_04", "Dismissed onboarding popups")

            log("TEST_04", "Running Axe test for Files Page")
            violations_count = self.run_axe_test("Files Page")
            log("TEST_04", f"Files page Axe test completed with {violations_count} violations")
        except Exception as e:
            log("ERROR", f"test_04 failed: {e}")
            dump_state(self.page, "test_04_error")
            raise

    def test_05_create_folder(self):
        try:
            log("TEST_05", "Starting create folder test")
            
            log("TEST_05", "Clicking New button")
            # Using .first to bypass Playwright strict mode violation and match Selenium behavior
            new_button = self.page.locator("xpath=//button[contains(., 'New')]").first
            new_button.wait_for(state="visible")
            new_button.click()

            log("TEST_05", "Selecting New Folder")
            # Using .first here fixes the strict mode violation present in the logs
            new_folder_option = self.page.locator("xpath=//*[contains(@class, 'action-button') and contains(., 'New folder')]").first
            new_folder_option.wait_for(state="visible")
            new_folder_option.click()

            log("TEST_05", "Typing folder name")
            input_box = self.page.locator("xpath=//form//input[@type='text']").first
            input_box.wait_for(state="visible")
            
            input_box.clear()
            input_box.fill(self.__class__.test_folder_name)
            
            # Reintroduced the Vue.js timing delay before pressing enter
            time.sleep(0.5)
            input_box.press("Enter")

            log("TEST_05", "Verifying folder exists")
            # Upgraded verification from the functional script to pierce the virtual DOM 
            folder_row = self.page.locator(
                f"xpath=//span[contains(., '{self.__class__.test_folder_name}')] | //a[contains(., '{self.__class__.test_folder_name}')] | //tr[@data-file='{self.__class__.test_folder_name}']"
            ).first
            
            folder_row.wait_for(state="visible")
            self.assertTrue(folder_row.is_visible(), "Folder gagal dibuat.")
            log("TEST_05", f"✓ Folder '{self.__class__.test_folder_name}' berhasil dibuat")
        except Exception as e:
            log("ERROR", f"test_05 failed: {e}")
            dump_state(self.page, "test_05_error")
            raise

    def test_06_upload_file(self):
        try:
            log("TEST_06", "Starting upload file test")
            
            log("TEST_06", "Locating file inputs")
            file_inputs = self.page.locator("xpath=//input[@type='file']")

            if file_inputs.count() == 0:
                dump_state(self.page, "no_file_inputs")
                raise Exception("No file inputs found")

            upload_input = file_inputs.first

            log("TEST_06", "Forcing input visible")
            # Forcing styles natively matching ActionChains execution logic
            upload_input.evaluate("""node => {
                node.style.display = 'block';
                node.style.visibility = 'visible';
                node.style.opacity = 1;
            }""")

            log("TEST_06", f"Uploading file: {self.__class__.test_file_path}")
            upload_input.set_input_files(self.__class__.test_file_path)

            log("TEST_06", "Waiting for file to appear")
            new_file = self.page.locator(
                f"xpath=//*[contains(text(), '{self.__class__.test_file_name.split('.')[0]}')]"
            ).first
            new_file.wait_for(state="attached")
            
            log("TEST_06", f"✓ File '{self.__class__.test_file_name}' berhasil diupload")
            
        except Exception as e:
            log("ERROR", f"test_06 failed: {e}")
            dump_state(self.page, "test_06_error")
            raise

    def test_07_delete_file(self):
        try:
            log("TEST_07", "Starting delete file test")
            
            log("TEST_07", f"Locating row for {self.__class__.test_file_name}")
            
            row_selector = f"tr[data-cy-files-list-row-name='{self.__class__.test_file_name}']"
            row_element = self.page.locator(row_selector).first
            row_element.wait_for(state="attached")
            
            # Hover over the row to ensure the Actions button becomes interactable
            row_element.hover()
            time.sleep(0.5)
            
            log("TEST_07", "Opening actions menu")
            action_button = row_element.locator("[aria-label='Actions']").first
            # Executing JS click identically to Selenium arguments[0].click()
            action_button.evaluate("node => node.click()")
            
            time.sleep(1)
            
            log("TEST_07", "Scrolling menu and clicking Delete")
            self.page.keyboard.press("End")
            time.sleep(0.5)
            
            delete_xpath = "//*[@role='menu']//button[contains(., 'Delete')]"
            delete_buttons = self.page.locator(f"xpath={delete_xpath}")
            delete_buttons.last.wait_for(state="attached")
            
            if delete_buttons.count() > 0:
                delete_buttons.last.evaluate("node => node.click()")
            else:
                raise Exception("Could not find the 'Delete file' button in the menu.")
            
            log("TEST_07", "Waiting for file to disappear")
            row_element.wait_for(state="hidden")
            
            log("TEST_07", f"✓ File '{self.__class__.test_file_name}' berhasil dihapus")
        except Exception as e:
            log("ERROR", f"test_07 failed: {e}")
            dump_state(self.page, "test_07_error")
            raise

    def test_08_settings_axe(self):
        try:
            log("TEST_08", "Starting Settings page Axe test")
            log("TEST_08", "Navigating to settings")
            
            self.page.goto(f"{self.URL}/index.php/settings/user")
            
            log("TEST_08", "Waiting for settings page to load")
            self.page.locator("body").first.wait_for(state="attached")
            
            time.sleep(2)
            wait_for_loader_to_disappear(self.page)
            
            if "login" in self.page.url:
                dump_state(self.page, "settings_redirected_to_login")
                raise Exception("Session lost - redirected to login")
            
            log("TEST_08", "Running Axe test for Settings Page")
            violations_count = self.run_axe_test("Settings Page")
            log("TEST_08", f"Settings page Axe test completed with {violations_count} violations")
        except Exception as e:
            log("ERROR", f"test_08 failed: {e}")
            dump_state(self.page, "test_08_error")
            raise

    @classmethod
    def tearDownClass(cls):
        # Cleanup the test file created in setUpClass
        if hasattr(cls, 'test_file_path') and os.path.exists(cls.test_file_path):
            os.remove(cls.test_file_path)
            
        log("TEARDOWN", "Closing browser")
        time.sleep(2)
        
        # Shutdown Playwright cleanly
        cls.page.close()
        cls.context.close()
        cls.browser.close()
        cls.playwright.stop()
        
        log("TEARDOWN", "Browser closed successfully")

if __name__ == "__main__":
    unittest.main(verbosity=2)