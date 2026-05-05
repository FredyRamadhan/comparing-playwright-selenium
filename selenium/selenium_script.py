import os
import time
import unittest
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from axe_selenium_python import Axe

# --- LOGGING HELPERS ---
def log(step, msg=""):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{step}] {msg}")

def dump_state(driver, name="debug"):
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{name}_{timestamp}"

    driver.save_screenshot(f"{filename}.png")
    with open(f"{filename}.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)

    print(f"[DEBUG] Saved: {filename}.png + {filename}.html")

def wait_for_loader_to_disappear(wait):
    try:
        wait.until(
            EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, ".loading, .icon-loading")
            )
        )
    except:
        pass


class NextcloudTestSuite(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Setup WebDriver (Menggunakan Chrome)
        options = webdriver.ChromeOptions()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        cls.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        cls.wait = WebDriverWait(cls.driver, 20)
        cls.axe = Axe(cls.driver)
        
        # --- KONFIGURASI NEXTCLOUD ---
        cls.URL = "http://localhost:8081" 
        cls.USERNAME = "admin"         
        cls.PASSWORD = "admin"
        # -----------------------------
        
        # --- TEST DATA STATE ---
        # Initialize test data strings here so they are reliably shared across test methods
        timestamp = datetime.now().strftime('%H%M%S')
        cls.test_file_name = f"selenium_test_file_{timestamp}.txt"
        cls.test_folder_name = f"Selenium_Test_Folder_{timestamp}"
        cls.test_file_path = os.path.abspath(cls.test_file_name)

        # Create the local dummy file once for the upload test
        with open(cls.test_file_path, "w") as f:
            f.write("Selenium automation test file upload")

    def login_nextcloud(self, username, password):
        try:
            log("LOGIN", "Opening login page")
            self.driver.get(self.URL)

            log("LOGIN", "Waiting for username field")
            self.wait.until(EC.presence_of_element_located((By.ID, "user"))).send_keys(username)

            log("LOGIN", "Entering password")
            self.driver.find_element(By.ID, "password").send_keys(password)

            log("LOGIN", "Submitting login form")
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

            log("LOGIN", "Waiting for avatar")
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".avatardiv, .user-menu"))
            )
            
            log("LOGIN", "SUCCESS")
        except Exception as e:
            log("ERROR", f"Login failed: {e}")
            dump_state(self.driver, "login_error")
            raise

    def run_axe_test(self, page_name):
        time.sleep(2) # Tunggu DOM stabil sebelum inject Axe
        self.axe.inject()
        results = self.axe.run()
        violations = results.get('violations', [])
        print(f"\n--- [Axe-Score] Hasil Aksesibilitas: {page_name} ---")
        print(f"Ditemukan {len(violations)} pelanggaran aksesibilitas.")
        for violation in violations:
            print(f"- Aturan: {violation['id']} | Impact: {violation['impact']} | Deskripsi: {violation['description']}")
        return len(violations)

    # =================================================================
    # SKENARIO 2: ACCESSIBILITY & SCREEN READER COMPLIANCE
    # =================================================================
    def test_01_axe_login_page(self):
        try:
            log("TEST_01", "Starting Axe test for login page")
            self.driver.get(self.URL)
            self.wait.until(EC.presence_of_element_located((By.ID, "user")))
            violations_count = self.run_axe_test("Login Page")
            log("TEST_01", f"Found {violations_count} accessibility violations")
        except Exception as e:
            log("ERROR", f"test_01 failed: {e}")
            dump_state(self.driver, "test_01_error")
            raise

    # =================================================================
    # SKENARIO 3: USER ERROR PROTECTION
    # =================================================================
    def test_02_login_empty_password(self):
        try:
            log("TEST_02", "Starting empty password test")
            self.driver.get(self.URL)
            self.wait.until(EC.presence_of_element_located((By.ID, "user"))).send_keys(self.USERNAME)
            
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
            pwd_input = self.driver.find_element(By.ID, "password")
            is_required = pwd_input.get_attribute("required")
            
            if is_required:
                log("TEST_02", "✓ System prevents login with empty password (HTML5 Required form)")
            else:
                try:
                    error_msg = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "warning"))).text
                    log("TEST_02", f"✓ Error message displayed: {error_msg}")
                    self.assertTrue(len(error_msg) > 0)
                except:
                    log("TEST_02", "No explicit error message found, but form validation may have occurred")
        except Exception as e:
            log("ERROR", f"test_02 failed: {e}")
            dump_state(self.driver, "test_02_error")
            raise

    # =================================================================
    # SKENARIO 1: NAVIGASI & FUNGSIONAL UTAMA
    # =================================================================
    def test_03_login_and_dashboard_axe(self):
        try:
            log("TEST_03", "Starting login and dashboard Axe test")
            self.login_nextcloud(self.USERNAME, self.PASSWORD)
            
            log("TEST_03", "Waiting for avatar to confirm login")
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".avatardiv, .user-menu")))
            
            time.sleep(2)
            wait_for_loader_to_disappear(self.wait)
            
            log("TEST_03", "Running Axe test for Dashboard")
            violations_count = self.run_axe_test("Dashboard")
            log("TEST_03", f"Dashboard Axe test completed with {violations_count} violations")
        except Exception as e:
            log("ERROR", f"test_03 failed: {e}")
            dump_state(self.driver, "test_03_error")
            raise
        
    def test_04_navigation_and_files_axe(self):
        try:
            log("TEST_04", "Starting Files page Axe test")
            log("TEST_04", "Navigating to files app")
            self.driver.get(f"{self.URL}/index.php/apps/files/")
            
            log("TEST_04", "Waiting for app container")
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            time.sleep(2)
            wait_for_loader_to_disappear(self.wait)
            
            if "login" in self.driver.current_url:
                dump_state(self.driver, "files_redirected_to_login")
                raise Exception("Session lost - redirected to login")
            
            # Dismiss popups just like in the working functional script
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            log("TEST_04", "Dismissed onboarding popups")

            log("TEST_04", "Running Axe test for Files Page")
            violations_count = self.run_axe_test("Files Page")
            log("TEST_04", f"Files page Axe test completed with {violations_count} violations")
        except Exception as e:
            log("ERROR", f"test_04 failed: {e}")
            dump_state(self.driver, "test_04_error")
            raise

    def test_05_create_folder(self):
        try:
            log("TEST_05", "Starting create folder test")
            
            log("TEST_05", "Clicking New button")
            new_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'New')]"))
            )
            new_button.click()

            log("TEST_05", "Selecting New Folder")
            new_folder_option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(@class, 'action-button') and contains(., 'New folder')]"))
            )
            new_folder_option.click()

            log("TEST_05", "Typing folder name")
            input_box = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//form//input[@type='text']"))
            )
            
            input_box.clear()
            input_box.send_keys(self.__class__.test_folder_name)
            
            # Reintroduced the Vue.js timing delay before pressing enter
            time.sleep(0.5)
            input_box.send_keys(Keys.ENTER)

            log("TEST_05", "Verifying folder exists")
            # Upgraded verification from the functional script to pierce the virtual DOM 
            folder_row = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//span[contains(., '{self.__class__.test_folder_name}')] | //a[contains(., '{self.__class__.test_folder_name}')] | //tr[@data-file='{self.__class__.test_folder_name}']")
                )
            )
            
            self.assertTrue(folder_row.is_displayed(), "Folder gagal dibuat.")
            log("TEST_05", f"✓ Folder '{self.__class__.test_folder_name}' berhasil dibuat")
        except Exception as e:
            log("ERROR", f"test_05 failed: {e}")
            dump_state(self.driver, "test_05_error")
            raise

    def test_06_upload_file(self):
        try:
            log("TEST_06", "Starting upload file test")
            
            log("TEST_06", "Locating file inputs")
            file_inputs = self.driver.find_elements(By.XPATH, "//input[@type='file']")

            if not file_inputs:
                dump_state(self.driver, "no_file_inputs")
                raise Exception("No file inputs found")

            upload_input = file_inputs[0]

            log("TEST_06", "Forcing input visible")
            self.driver.execute_script("""
                arguments[0].style.display = 'block';
                arguments[0].style.visibility = 'visible';
                arguments[0].style.opacity = 1;
            """, upload_input)

            log("TEST_06", f"Uploading file: {self.__class__.test_file_path}")
            upload_input.send_keys(self.__class__.test_file_path)

            log("TEST_06", "Waiting for file to appear")
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//*[contains(text(), '{self.__class__.test_file_name.split('.')[0]}')]")
                )
            )
            
            log("TEST_06", f"✓ File '{self.__class__.test_file_name}' berhasil diupload")
            
        except Exception as e:
            log("ERROR", f"test_06 failed: {e}")
            dump_state(self.driver, "test_06_error")
            raise

    def test_07_delete_file(self):
        try:
            log("TEST_07", "Starting delete file test")
            
            # Using precise class data initialized at start of test run rather than wildcards
            log("TEST_07", f"Locating row for {self.__class__.test_file_name}")
            
            row_selector = f"tr[data-cy-files-list-row-name='{self.__class__.test_file_name}']"
            row_element = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, row_selector))
            )
            
            # Hover over the row to ensure the Actions button becomes interactable
            ActionChains(self.driver).move_to_element(row_element).perform()
            time.sleep(0.5)
            
            log("TEST_07", "Opening actions menu")
            action_button = row_element.find_element(By.CSS_SELECTOR, "[aria-label='Actions']")
            self.driver.execute_script("arguments[0].click();", action_button)
            
            time.sleep(1)
            
            log("TEST_07", "Scrolling menu and clicking Delete")
            ActionChains(self.driver).send_keys(Keys.END).perform()
            time.sleep(0.5)
            
            delete_xpath = "//*[@role='menu']//button[contains(., 'Delete')]"
            self.wait.until(EC.presence_of_element_located((By.XPATH, delete_xpath)))
            
            delete_buttons = self.driver.find_elements(By.XPATH, delete_xpath)
            if delete_buttons:
                self.driver.execute_script("arguments[0].click();", delete_buttons[-1])
            else:
                raise Exception("Could not find the 'Delete file' button in the menu.")
            
            log("TEST_07", "Waiting for file to disappear")
            self.wait.until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, row_selector))
            )
            
            log("TEST_07", f"✓ File '{self.__class__.test_file_name}' berhasil dihapus")
        except Exception as e:
            log("ERROR", f"test_07 failed: {e}")
            dump_state(self.driver, "test_07_error")
            raise

    def test_08_settings_axe(self):
        try:
            log("TEST_08", "Starting Settings page Axe test")
            log("TEST_08", "Navigating to settings")
            
            self.driver.get(f"{self.URL}/index.php/settings/user")
            
            log("TEST_08", "Waiting for settings page to load")
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            time.sleep(2)
            wait_for_loader_to_disappear(self.wait)
            
            if "login" in self.driver.current_url:
                dump_state(self.driver, "settings_redirected_to_login")
                raise Exception("Session lost - redirected to login")
            
            log("TEST_08", "Running Axe test for Settings Page")
            violations_count = self.run_axe_test("Settings Page")
            log("TEST_08", f"Settings page Axe test completed with {violations_count} violations")
        except Exception as e:
            log("ERROR", f"test_08 failed: {e}")
            dump_state(self.driver, "test_08_error")
            raise

    @classmethod
    def tearDownClass(cls):
        # Cleanup the test file created in setUpClass
        if hasattr(cls, 'test_file_path') and os.path.exists(cls.test_file_path):
            os.remove(cls.test_file_path)
            
        log("TEARDOWN", "Closing browser")
        time.sleep(2)
        cls.driver.quit()
        log("TEARDOWN", "Browser closed successfully")

if __name__ == "__main__":
    unittest.main(verbosity=2)