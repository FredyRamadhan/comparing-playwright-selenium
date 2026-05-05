import pytest
import os
from conftest import BASE_URL, NC_USER, NC_PASS


class TestAuth:

    def test_login_berhasil(self, nc_page):
        """Login: verifikasi session sudah aktif dan bisa akses apps."""
        nc_page.goto(f"{BASE_URL}/apps/dashboard")
        nc_page.wait_for_load_state("networkidle")
        assert "apps" in nc_page.url, f"Harusnya di halaman apps, tapi URL: {nc_page.url}"


class TestNavigasi:

    def test_navigasi_ke_files(self, nc_logged_in):
        p = nc_logged_in
        p.goto(f"{BASE_URL}/apps/files")
        p.wait_for_load_state("networkidle")
        assert "files" in p.url

    def test_navigasi_ke_settings(self, nc_logged_in):
        p = nc_logged_in
        p.goto(f"{BASE_URL}/settings/user")
        p.wait_for_load_state("networkidle")
        assert "settings" in p.url

    def test_navigasi_ke_dashboard(self, nc_logged_in):
        p = nc_logged_in
        p.goto(f"{BASE_URL}/apps/dashboard")
        p.wait_for_load_state("networkidle")
        assert "dashboard" in p.url


UPLOAD_FILENAME = "test_upload.txt"

class TestUploadFile:

    def test_upload_file(self, nc_logged_in, tmp_path):
        p = nc_logged_in
        p.goto(f"{BASE_URL}/apps/files")
        p.wait_for_load_state("networkidle")

        dummy = tmp_path / UPLOAD_FILENAME
        dummy.write_text("Ini file test upload dari Playwright")

        # Klik tombol "+ New" dulu
        p.click('.upload-picker button:last-child, button:has-text("New")')
        p.wait_for_timeout(500)

        # Klik "Upload files" dari dropdown, sambil expect file chooser
        with p.expect_file_chooser() as fc_info:
            p.click('button:has-text("Upload files"), li:has-text("Upload files")')
        fc_info.value.set_files(str(dummy))

        p.wait_for_selector(f'text={UPLOAD_FILENAME}', timeout=20000)
        assert p.is_visible(f'text={UPLOAD_FILENAME}')


class TestCreateFolder:

    def test_create_folder(self, nc_logged_in):
        p = nc_logged_in
        p.goto(f"{BASE_URL}/apps/files")
        p.wait_for_load_state("networkidle")

        folder_name = "FolderTestPlaywright"

        new_button_selectors = [
            '[data-cy-upload-picker-menu-toggle]',
            'button[data-cy-upload-picker-menu-toggle]',
            '.upload-picker button:last-child',
            'button:has-text("New")',
            '.button-vue:has-text("New")',
        ]

        for sel in new_button_selectors:
            try:
                p.wait_for_selector(sel, timeout=3000)
                p.click(sel)
                print(f"Tombol New diklik: {sel}")
                break
            except:
                continue

        folder_menu_selectors = [
            '[data-cy-upload-picker-menu-entry="newFolder"]',
            'button:has-text("New folder")',
            'li:has-text("New folder")',
            'span:has-text("New folder")',
        ]

        for sel in folder_menu_selectors:
            try:
                p.wait_for_selector(sel, timeout=3000)
                p.click(sel)
                print(f"Menu folder diklik: {sel}")
                break
            except:
                continue

        p.wait_for_selector('input[placeholder*="folder" i], input[placeholder*="name" i]', timeout=8000)
        p.fill('input[placeholder*="folder" i], input[placeholder*="name" i]', folder_name)
        p.keyboard.press("Enter")

        p.wait_for_selector(f'text={folder_name}', timeout=10000)
        assert p.is_visible(f'text={folder_name}')


class TestDeleteFile:

    def test_delete_file(self, nc_logged_in, tmp_path):
        p = nc_logged_in
        p.goto(f"{BASE_URL}/apps/files")
        p.wait_for_load_state("networkidle")

        # Tunggu file muncul
        p.wait_for_selector(f'[data-cy-files-list-row-name="{UPLOAD_FILENAME}"]', timeout=10000)

        # Ambil row spesifik
        row = p.get_by_role("row", name=f'"{UPLOAD_FILENAME}"', exact=False)
        row.hover()
        p.wait_for_timeout(500)

        # Klik tombol Actions di row ini
        row.get_by_label("Actions", exact=True).click()
        p.wait_for_timeout(800)

        # Print semua item menu yang muncul untuk debug
        menu_items = p.locator('[role="menu"] button, [role="menuitem"], .action-button').all()
        print(f"\nMenu items ditemukan: {len(menu_items)}")
        for item in menu_items:
            print(f"  - '{item.inner_text()}'")

        # Scroll menu ke bawah pakai keyboard
        p.keyboard.press("End")
        p.wait_for_timeout(300)

        # Coba berbagai selector delete
        delete_selectors = [
             '[role="menu"] button:has-text("Delete file")'
        ]

        deleted = False
        for sel in delete_selectors:
            try:
                btn = p.locator(sel).last
                btn.wait_for(timeout=2000)
                btn.click()
                print(f"Delete diklik: {sel}")
                deleted = True
                break
            except:
                continue

        assert deleted, "Tidak bisa menemukan tombol Delete di dropdown"

        p.wait_for_timeout(3000)
        assert not p.is_visible(f'[data-cy-files-list-row-name="{UPLOAD_FILENAME}"]')


# =============================================
# LOGOUT — selalu dijalankan PALING TERAKHIR
# =============================================
class TestLogout:

    def test_logout(self, nc_logged_in):
        p = nc_logged_in

        avatar_selectors = [
            '[data-cy-header-menu-avatar]',
            '#header .avatardiv',
            '.header-menu__trigger',
            'button.avatardiv',
            '#expand',
            '[aria-label="Open user menu"]',
            '.user-menu button',
        ]

        clicked = False
        for sel in avatar_selectors:
            try:
                p.wait_for_selector(sel, timeout=3000)
                p.click(sel)
                clicked = True
                print(f"Avatar diklik: {sel}")
                break
            except:
                continue

        assert clicked, "Tidak bisa menemukan tombol avatar/user menu"

        logout_selectors = [
            '[data-cy-user-menu-logout]',
            'a[href*="logout"]',
            'button:has-text("Log out")',
            'a:has-text("Log out")',
        ]

        for sel in logout_selectors:
            try:
                p.wait_for_selector(sel, timeout=3000)
                p.click(sel)
                print(f"Logout diklik: {sel}")
                break
            except:
                continue

        p.wait_for_url("**/login**", timeout=15000)
        assert "login" in p.url