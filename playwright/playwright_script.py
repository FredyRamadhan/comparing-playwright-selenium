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

def wait_for_loaders(page):
    """Helper to ensure Nextcloud UI is fully settled"""
    try:
        # Reduced loader timeout from 5000ms to 2000ms
        page.wait_for_selector(".loading, .icon-loading", state="hidden", timeout=2000)
    except:
        pass

def check_axe(page, label):
    """Accessibility check logic"""
    axe = Axe()
    wait_for_loaders(page)
    results = axe.run(page)
    violations = results.violations if hasattr(results, 'violations') else []
    critical = [v for v in violations if v.get("impact") == "critical"]
    
    print(f"--- Accessibility: {label} ---")
    print(f"Found {len(violations)} total violations ({len(critical)} critical).")
    return len(critical) == 0

def run_tests():
    with sync_playwright() as p:
        print("Starting browser...")
        # Reduced slow_mo from 300ms to 50ms to massively speed up execution
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. Login Phase
            print(f"\n[Test] Logging in as {NC_USER}...")
            page.goto(f"{BASE_URL}/login")
            page.fill('input[name="user"]', NC_USER)
            page.fill('input[name="password"]', NC_PASS)
            page.click('button[type="submit"]')
            
            # Reduced timeout from 30000ms to 10000ms
            page.wait_for_selector('.avatardiv, .user-menu', timeout=10000)
            print("Successfully logged in.")

            # 2. Navigation & Accessibility
            test_targets = [
                ("Dashboard", f"{BASE_URL}/apps/dashboard"),
                ("Files", f"{BASE_URL}/index.php/apps/files/"),
                ("Settings", f"{BASE_URL}/index.php/settings/user")
            ]

            for label, url in test_targets:
                print(f"\n[Test] Navigating to {label}...")
                page.goto(url)
                page.wait_for_load_state("networkidle")
                wait_for_loaders(page)
                
                # Dismiss any Nextcloud onboarding popups
                page.keyboard.press("Escape")

                if "login" in page.url:
                    print(f"FAILED: Redirected to login while accessing {label}")
                else:
                    print(f"PASSED: Reached {label}")
                
                a11y_status = "PASSED" if check_axe(page, label) else "FAILED"
                print(f"Accessibility Result: {a11y_status}")

            # 3. File Operations (Create Folder)
            print("\n[Test] Creating a folder...")
            page.goto(f"{BASE_URL}/index.php/apps/files/")
            wait_for_loaders(page)
            
            print("  -> Dismissing onboarding popups...")
            page.keyboard.press("Escape")

            print("  -> Clicking 'New' button...")
            page.locator('button:has-text("New")').click()
            
            print("  -> Selecting 'New folder' option...")
            page.locator('.action-button:has-text("New folder")').click()
            
            timestamp = datetime.now().strftime('%H%M%S')
            folder_name = f"Playwright_Test_Folder_{timestamp}"
            print(f"  -> Typing folder name: '{folder_name}'...")
            input_box = page.locator("form input[type='text']")
            input_box.fill(folder_name)
            
            print("  -> Waiting 200ms for Vue.js state sync...")
            # Reduced from 500ms to 200ms
            page.wait_for_timeout(200)
            
            print("  -> Pressing 'Enter'...")
            input_box.press("Enter")
            
            print(f"  -> Verifying folder '{folder_name}' exists in the UI...")
            try:
                # Broadened selector: checks for data-file, Cypress test IDs, or exact text matches
                row_selector = f"tr[data-file='{folder_name}'], tr[data-cy-files-list-row-name='{folder_name}'], span:text-is('{folder_name}')"
                
                # Reduced from 10000ms to 5000ms
                page.wait_for_selector(row_selector, timeout=5000)
                print(f"PASSED: Created folder '{folder_name}'")
            except Exception as e:
                print(f"\nFAILED: Could not find folder '{folder_name}' in the DOM after 5 seconds.")
                print(f"  -> Debug Info: Current URL: {page.url}")
                
                # Debugging: Grab the text of the files list to see what actually rendered
                try:
                    file_list_text = page.locator("table, .files-list").inner_text()
                    print(f"  -> Debug Info: Current visible files/folders:\n{file_list_text[:500]}...\n")
                except:
                    print("  -> Debug Info: Could not extract file list text.")
                
                # Re-raise the exception to trigger the main script's finally block
                raise e

            # 4. Negative Test: Login without password
            print("\n[Test] Attempting login without password...")
            temp_context = browser.new_context()
            temp_page = temp_context.new_page()
            temp_page.goto(f"{BASE_URL}/login")
            temp_page.fill('input[name="user"]', NC_USER)
            temp_page.click('button[type="submit"]')
            
            # Check for HTML5 required attribute validation
            pwd_input = temp_page.locator('input[name="password"]')
            is_required = pwd_input.get_attribute("required")
            
            if is_required is not None:
                print("PASSED: System prevents login with empty password (HTML5 Required form)")
            else:
                print("FAILED: User was not blocked by empty password.")
            temp_context.close()

            # 5. Logout
            print("\n[Test] Logging out...")
            page.click('.avatardiv, .user-menu')
            page.click('li:has-text("Log out")')
            
            # Reduced from 15000ms to 5000ms
            page.wait_for_url("**/login**", timeout=5000)
            print("PASSED: Successfully logged out.")

        except Exception as e:
            print(f"\nAn error occurred during execution: {e}")
        finally:
            print("\nClosing browser...")
            browser.close()

if __name__ == "__main__":
    run_tests()