import os
import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from axe_selenium_python import Axe

class NextcloudTestSuite(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Setup WebDriver (Menggunakan Chrome)
        options = webdriver.ChromeOptions()
        # options.add_argument("--headless")
        options.add_argument("--start-maximized")
        cls.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        cls.wait = WebDriverWait(cls.driver, 15)
        cls.axe = Axe(cls.driver)
        
        # --- KONFIGURASI NEXTCLOUD ---
        cls.URL = "http://localhost:8081" 
        cls.USERNAME = "admin"         
        cls.PASSWORD = "admin"
        # -----------------------------

    def login_nextcloud(self, username, password):
        self.driver.get(self.URL)
        self.wait.until(EC.presence_of_element_located((By.ID, "user"))).send_keys(username)
        pwd_input = self.driver.find_element(By.ID, "password")
        pwd_input.clear()
        if password:
            pwd_input.send_keys(password)
        self.driver.find_element(By.XPATH, "//button[@data-login-form-submit]").click()

    def run_axe_test(self, page_name):
        """Helper untuk menjalankan Axe-core dan mencetak hasil/score"""
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
    # SKENARIO 2: ACCESSIBILITY & SCREEN READER COMPLIANCE (Skenario 2 didahulukan untuk flow)
    # =================================================================
    def test_01_axe_login_page(self):
        self.driver.get(self.URL)
        self.wait.until(EC.presence_of_element_located((By.ID, "user")))
        self.run_axe_test("Login Page")

    # =================================================================
    # SKENARIO 3: USER ERROR PROTECTION
    # =================================================================
    def test_02_login_empty_password(self):
        self.driver.get(self.URL)
        self.login_nextcloud(self.USERNAME, "")
        
        # Mengecek apakah atribut 'required' HTML5 memblokir submit 
        # atau ada alert message khusus dari Nextcloud
        pwd_input = self.driver.find_element(By.ID, "password")
        is_required = pwd_input.get_attribute("required")
        
        if is_required:
            print("Berhasil: Sistem mencegah login dengan password kosong (HTML5 Required form).")
        else:
            # Jika Nextcloud menggunakan flash message untuk error
            error_msg = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "warning"))).text
            print(f"Error message muncul: {error_msg}")
            self.assertTrue(len(error_msg) > 0)

    # =================================================================
    # SKENARIO 1: NAVIGASI & FUNGSIONAL UTAMA
    # =================================================================
    def test_03_login_and_dashboard_axe(self):
        self.login_nextcloud(self.USERNAME, self.PASSWORD)
        # Menunggu sampai dashboard/files termuat
        self.wait.until(EC.presence_of_element_located((By.ID, "appmenu")))
        
        # Axe test untuk Dashboard (sebelum masuk secara spesifik ke tab/modul Files)
        self.run_axe_test("Dashboard")
        
    def test_04_navigation_and_files_axe(self):
        # Klik menu Files di Navbar
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//ul[@id='appmenu']//li[@data-id='files']"))).click()
        self.wait.until(EC.presence_of_element_located((By.ID, "fileList")))
        
        # Axe test untuk Files Page
        self.run_axe_test("Files Page")

    def test_05_create_folder(self):
        # Klik tombol tambah (+)
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".button.view-switcher"))).click()
        time.sleep(1)
        # Klik menu 'New folder'
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-templatename='New folder']"))).click()
        
        # Masukkan nama folder
        folder_name_input = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".header-input")))
        folder_name_input.send_keys("Test_Folder_Automation")
        folder_name_input.send_keys(Keys.ENTER)
        
        # Verifikasi folder terbuat (menunggu folder muncul di list)
        folder_row = self.wait.until(EC.presence_of_element_located((By.XPATH, "//tr[@data-file='Test_Folder_Automation']")))
        self.assertTrue(folder_row.is_displayed(), "Folder gagal dibuat.")

    def test_06_upload_file(self):
        # Untuk upload di Selenium, kita langsung send_keys ke hidden input type="file"
        file_input = self.driver.find_element(By.CSS_SELECTOR, "input.file_upload_start")
        
        # Buat file dummy sementara
        test_file_path = os.path.abspath("dummy_upload.txt")
        with open(test_file_path, "w") as f:
            f.write("Ini adalah file test automation.")
            
        file_input.send_keys(test_file_path)
        
        # Tunggu sampai proses upload selesai (file muncul di list)
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//tr[@data-file='dummy_upload.txt']")))
        print("File berhasil diupload.")
        
        # Hapus file dummy dari local setelah diupload
        os.remove(test_file_path)

    def test_07_delete_multiple_files_protection(self):
        # Skenario 3: Delete multiple files (apakah ada konfirmasi/undo alert)
        
        # Asumsi: "Test_Folder_Automation" dan "dummy_upload.txt" ada di list
        # Klik checkbox untuk "Test_Folder_Automation"
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//tr[@data-file='Test_Folder_Automation']//label"))).click()
        # Klik checkbox untuk "dummy_upload.txt"
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//tr[@data-file='dummy_upload.txt']//label"))).click()
        
        # Klik tombol Action di Header (Actions for selected items)
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#headerName-container .action-menu"))).click()
        
        # Klik Delete
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-action='Delete']"))).click()
        
        # Nextcloud biasanya tidak menampilkan Pop-up Modal, melainkan Toast Notification di atas layar untuk "Undo"
        try:
            undo_toast = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".toast-undo")))
            print("Berhasil: Notifikasi Undo (Error Protection/Konfirmasi implisit) muncul setelah menghapus.")
        except:
            print("Gagal: Tidak ada notifikasi konfirmasi/undo yang muncul saat menghapus multiple file.")

    def test_08_settings_axe(self):
        # Navigasi ke settings page via profile menu di kanan atas
        self.wait.until(EC.element_to_be_clickable((By.ID, "settings"))).click()
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='settings/user']"))).click()
        self.wait.until(EC.presence_of_element_located((By.ID, "personal-settings-avatar")))
        
        # Axe test untuk Settings Page
        self.run_axe_test("Settings Page")

    @classmethod
    def tearDownClass(cls):
        # Tutup browser setelah semua test selesai
        time.sleep(2)
        cls.driver.quit()

if __name__ == "__main__":
    unittest.main(verbosity=2)