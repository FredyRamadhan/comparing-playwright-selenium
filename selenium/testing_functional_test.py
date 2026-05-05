import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from webdriver_manager.chrome import ChromeDriverManager


# --- CONFIG ---
NEXTCLOUD_URL = "http://localhost:8081"
USERNAME = "admin"
PASSWORD = "admin"
FILE_NAME = "sqa_test_file" + datetime.now().strftime("_%H%M%S") + ".txt"
FOLDER_NAME = "SQA_Test_Directory" + datetime.now().strftime("_%H%M%S")


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


def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # --- CREATE TEST FILE ---
    with open(FILE_NAME, "w") as f:
        f.write("Selenium debug upload file")
    file_path = os.path.abspath(FILE_NAME)

    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    wait = WebDriverWait(driver, 20)

    try:
        # ================= LOGIN =================
        log("LOGIN", "Opening login page")
        driver.get(NEXTCLOUD_URL)

        log("LOGIN", "Waiting for username field")
        wait.until(EC.presence_of_element_located((By.ID, "user"))).send_keys(USERNAME)

        log("LOGIN", "Entering password")
        driver.find_element(By.ID, "password").send_keys(PASSWORD)

        log("LOGIN", "Submitting login form")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        log("LOGIN", "Waiting for avatar")
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".avatardiv, .user-menu"))
        )

        log("LOGIN", "SUCCESS")

        # ================= FILES PAGE =================
        try:
            log("FILES", "Navigating to files app")
            driver.get(f"{NEXTCLOUD_URL}/index.php/apps/files/")

            log("FILES", f"URL after nav: {driver.current_url}")

            log("FILES", "Waiting for app container")
            wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            time.sleep(2)
            wait_for_loader_to_disappear(wait)

            log("FILES", f"Page title: {driver.title}")
            log("FILES", f"Current URL: {driver.current_url}")

            # Check if redirected to login
            if "login" in driver.current_url:
                dump_state(driver, "redirected_to_login")
                raise Exception("Session lost - redirected to login")

            # Count elements
            file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
            log("FILES", f"File inputs found: {len(file_inputs)}")

            buttons = driver.find_elements(By.TAG_NAME, "button")
            log("FILES", f"Buttons found: {len(buttons)}")

            # Dismiss popups
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()

            log("FILES", "Page ready")

        except Exception as e:
            log("ERROR", f"FILES PAGE FAILURE: {e}")
            dump_state(driver, "files_page_error")
            raise

        # ================= UPLOAD =================
        try:
            log("UPLOAD", "Locating file inputs")

            file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
            log("UPLOAD", f"Total inputs: {len(file_inputs)}")

            for i, inp in enumerate(file_inputs):
                log("UPLOAD", f"Input {i}: displayed={inp.is_displayed()}, enabled={inp.is_enabled()}")

            if not file_inputs:
                dump_state(driver, "no_inputs")
                raise Exception("No file inputs found")

            upload_input = file_inputs[0]

            log("UPLOAD", "Forcing input visible")
            driver.execute_script("""
                arguments[0].style.display = 'block';
                arguments[0].style.visibility = 'visible';
                arguments[0].style.opacity = 1;
            """, upload_input)

            log("UPLOAD", f"Uploading file: {file_path}")
            upload_input.send_keys(file_path)

            log("UPLOAD", "Waiting for file to appear")

            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//*[contains(text(), '{FILE_NAME.split('.')[0]}')]")
                )
            )

            log("UPLOAD", "SUCCESS")

        except Exception as e:
            log("ERROR", f"UPLOAD FAILURE: {e}")
            dump_state(driver, "upload_error")
            raise

        # ================= CREATE FOLDER =================
        # ================= CREATE FOLDER =================
        try:
            log("FOLDER", "Clicking New button")

            # 1. Click the main "New" button
            new_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(., 'New')]")
                )
            )
            new_button.click()

            log("FOLDER", "Selecting New Folder")

            # 2. Select "New folder" from the dropdown. 
            # Using a more forgiving XPATH that looks for the text anywhere inside the button/link
            new_folder_option = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(@class, 'action-button') and contains(., 'New folder')]")
                )
            )
            new_folder_option.click()

            log("FOLDER", "Typing folder name")

            # 3. Wait for the input box to appear in the file list
            # Nextcloud creates a temporary row with an input box for the new folder name
            input_box = wait.until(
                EC.presence_of_element_located((By.XPATH, "//form//input[@type='text']"))
            )
            
            # Clear any default text (like "New folder") before typing
            input_box.clear()
            input_box.send_keys(FOLDER_NAME)
            
            # Add a tiny sleep before pressing Enter, as Vue sometimes needs a tick to register the input
            time.sleep(0.5) 
            input_box.send_keys(Keys.ENTER)

            log("FOLDER", "Verifying folder exists")

            # Use '.' instead of 'text()' to evaluate the entire string context of the node.
            # This safely bypasses Nextcloud's Vue.js nested elements and virtual DOM comments.
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//span[contains(., '{FOLDER_NAME}')] | //a[contains(., '{FOLDER_NAME}')] | //tr[@data-file='{FOLDER_NAME}']")
                )
            )

            log("FOLDER", "SUCCESS")

        except Exception as e:
            log("ERROR", f"FOLDER FAILURE: {e}")
            dump_state(driver, "folder_error")
            raise
        
        time.sleep(2)  # Small pause before next action
        
        # ================= DELETE FILE =================
        try:
            log("DELETE", f"Locating row for {FILE_NAME}")
            
            # 1. Use the data-cy attribute to find the exact row (adapted from Playwright)
            row_selector = f"tr[data-cy-files-list-row-name='{FILE_NAME}']"
            row_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, row_selector))
            )
            
            # Hover over the row to ensure the Actions button becomes interactable
            ActionChains(driver).move_to_element(row_element).perform()
            time.sleep(0.5)
            
            log("DELETE", "Opening actions menu")
            # 2. Find and click the Actions button within that specific row
            action_button = row_element.find_element(By.CSS_SELECTOR, "[aria-label='Actions']")
            driver.execute_script("arguments[0].click();", action_button)
            
            # Wait for the popover menu to render
            time.sleep(1)
            
            log("DELETE", "Scrolling menu and clicking Delete")
            # 3. Simulate pressing "End" to scroll to the bottom of the actions menu (adapted from Playwright)
            ActionChains(driver).send_keys(Keys.END).perform()
            time.sleep(0.5)
            
            # 4. Find the Delete button. Playwright uses '.last' because there are sometimes hidden DOM clones.
            delete_xpath = "//*[@role='menu']//button[contains(., 'Delete')]"
            
            # Wait for the delete buttons to be present
            wait.until(EC.presence_of_element_located((By.XPATH, delete_xpath)))
            
            # Get all matching delete buttons and click the last one (matches Playwright's `.last` logic)
            delete_buttons = driver.find_elements(By.XPATH, delete_xpath)
            if delete_buttons:
                driver.execute_script("arguments[0].click();", delete_buttons[-1])
            else:
                raise Exception("Could not find the 'Delete file' button in the menu.")
            
            log("DELETE", "Waiting for file to disappear")
            # 5. Verify the file is actually removed from the UI
            wait.until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, row_selector))
            )
            
            log("DELETE", "SUCCESS")

        except Exception as e:
            log("ERROR", f"DELETE FAILURE: {e}")
            dump_state(driver, "delete_error")
            raise

        log("FINAL", "✅ ALL TESTS PASSED")

        time.sleep(3)

    except Exception as e:
        log("FATAL", str(e))

    finally:
        driver.quit()
        if os.path.exists(file_path):
            os.remove(file_path)


if __name__ == "__main__":
    main()