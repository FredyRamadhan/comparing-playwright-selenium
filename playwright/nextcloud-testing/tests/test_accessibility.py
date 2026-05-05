import pytest
import time
from axe_playwright_python.sync_playwright import Axe
from conftest import BASE_URL, NC_USER, NC_PASS

axe = Axe()

def check_axe(page, label):
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    results = axe.run(page)

    if hasattr(results, 'violations'):
        violations = results.violations
    elif hasattr(results, 'response'):
        violations = results.response.get('violations', [])
    else:
        violations = results.__dict__.get('violations', [])

    critical = [v for v in violations if v.get("impact") == "critical"]
    serious  = [v for v in violations if v.get("impact") == "serious"]

    print(f"\n{'='*50}")
    print(f"[{label}] Violations: {len(violations)} total | {len(critical)} critical | {len(serious)} serious")
    for v in violations:
        print(f"  [{v.get('impact','?').upper()}] {v.get('id','?')}: {v.get('description','?')}")
    print('='*50)

    return critical


class TestAxeScore:

    def test_axe_login_page(self, nc_browser):
        """Buka halaman login di context terpisah tanpa session."""
        browser = nc_browser.browser
        fresh_context = browser.new_context()
        page = fresh_context.new_page()
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")
        critical = check_axe(page, "LOGIN")
        fresh_context.close()
        assert len(critical) == 0, f"{len(critical)} critical violations di halaman login"

    def test_axe_files_page(self, nc_logged_in):
        p = nc_logged_in
        p.goto(f"{BASE_URL}/apps/files")
        critical = check_axe(p, "FILES")
        known_violations = ['label', 'empty-table-header', 'region']
        unknown_critical = [v for v in critical if v.get('id') not in known_violations]
        assert len(unknown_critical) == 0, f"{len(unknown_critical)} unknown critical violations di halaman files"

    def test_axe_settings_page(self, nc_logged_in):
        p = nc_logged_in
        p.goto(f"{BASE_URL}/settings/user")
        critical = check_axe(p, "SETTINGS")
        assert len(critical) == 0, f"{len(critical)} critical violations di halaman settings"

    def test_axe_dashboard_page(self, nc_logged_in):
        p = nc_logged_in
        p.goto(f"{BASE_URL}/apps/dashboard")
        critical = check_axe(p, "DASHBOARD")
        assert len(critical) == 0, f"{len(critical)} critical violations di halaman dashboard"


class TestUserErrorProtection:

    def test_login_tanpa_password(self, nc_browser):
        browser = nc_browser.browser
        fresh_context = browser.new_context()
        page = fresh_context.new_page()

        page.goto(f"{BASE_URL}/login")
        page.wait_for_selector('input[name="user"]', timeout=15000)
        page.fill('input[name="user"]', NC_USER)
        page.fill('input[name="password"]', "")
        page.click('button[type="submit"]')
        page.wait_for_timeout(3000)

        assert "login" in page.url, "Harusnya tetap di halaman login"

        error_selectors = [
            '.warning', '.error', '[role="alert"]',
            '#body-login .warning-info', '.login-additional',
            'p.warning', '.v-toast', '.toast-error',
        ]
        error_found = False
        for sel in error_selectors:
            try:
                if page.is_visible(sel):
                    print(f"Error ditemukan dengan selector: {sel}")
                    print(f"Text: {page.inner_text(sel)}")
                    error_found = True
                    break
            except:
                continue

        if not error_found:
            print(f"\nURL saat ini: {page.url}")
            print("Tidak ada error selector yang cocok, cek apakah masih di login...")

        assert "login" in page.url, "Harus tetap di halaman login setelah submit tanpa password"
        fresh_context.close()

    def test_delete_multiple_files_ada_konfirmasi(self, nc_logged_in, tmp_path):
        """
        [TEMUAN] Nextcloud 28 TIDAK menampilkan dialog konfirmasi saat menghapus
        multiple file. File langsung masuk Trash tanpa peringatan apapun.
        Ini adalah UX/safety issue — user bisa tidak sengaja menghapus banyak file
        sekaligus tanpa ada kesempatan untuk membatalkan.
        """
        p = nc_logged_in
        p.goto(f"{BASE_URL}/apps/files")
        p.wait_for_load_state("networkidle")

        # Upload 2 file — pakai suffix _0 dan _1 agar nama selalu beda
        # meski int(time.time()) sama karena loop jalan dalam 1 detik
        filenames = []
        for i in range(2):
            fname = f"multi_delete_{int(time.time())}_{i}.txt"
            filenames.append(fname)
            f = tmp_path / fname
            f.write_text(f"file {i}")

            p.click('.upload-picker button:last-child, button:has-text("New")')
            p.wait_for_timeout(500)
            with p.expect_file_chooser() as fc_info:
                p.click('button:has-text("Upload files"), li:has-text("Upload files")')
            fc_info.value.set_files(str(f))
            p.wait_for_timeout(2000)

        p.reload()
        p.wait_for_load_state("networkidle")

        # Centang checkbox dengan force karena label intercept
        for fname in filenames:
            row = p.get_by_role("row", name=fname, exact=False)
            checkbox = row.locator('input[type="checkbox"]')
            checkbox.click(force=True)
            p.wait_for_timeout(500)

        selected = p.locator('input[type="checkbox"]:checked').count()
        print(f"\nFile terselect: {selected}")

        # Debug: print SEMUA button di halaman yang visible
        # untuk nemuin selector "..." di selection bar
        all_btns = p.locator('button:visible').all()
        print(f"Semua button visible ({len(all_btns)} total):")
        for b in all_btns:
            label = b.get_attribute('aria-label') or ''
            txt = b.inner_text().strip()
            data_cy = b.get_attribute('data-cy-files-list-selection-action') or ''
            if label or data_cy:
                print(f"  aria-label='{label}' | data-cy='{data_cy}' | text='{txt}'")

        # Klik "..." di selection bar atas (samping "Move or copy")
        # Selection bar Nextcloud 28 bukan di thead tapi di baris header tersendiri
        more_btn_selectors = [
            '[data-cy-files-list-selection-action="more"]',
            'button[aria-label="More actions"]:visible',
            'button[aria-label="Actions"]:visible',
            # Cari di parent yang mengandung teks "selected"
            ':has-text("selected") >> button:last-child',
        ]

        clicked_more = False
        for sel in more_btn_selectors:
            try:
                btn = p.locator(sel).first
                btn.wait_for(timeout=2000)
                btn.scroll_into_view_if_needed()
                btn.click()
                clicked_more = True
                print(f"Tombol '...' diklik: {sel}")
                p.wait_for_timeout(500)
                break
            except:
                continue

        assert clicked_more, "Tidak bisa menemukan tombol '...' di selection bar — lihat debug output di atas"

        # Klik "Delete files" dari dropdown
        delete_selectors = [
            'button:has-text("Delete files")',
            '[role="menuitem"]:has-text("Delete files")',
            'li:has-text("Delete files")',
        ]

        clicked_delete = False
        for sel in delete_selectors:
            try:
                p.wait_for_selector(sel, timeout=3000)
                p.click(sel)
                clicked_delete = True
                print(f"Delete files diklik: {sel}")
                break
            except:
                continue

        assert clicked_delete, "Tidak bisa menemukan 'Delete files' di dropdown"

        # Cek apakah muncul dialog konfirmasi
        # TEMUAN: Nextcloud 28 tidak menampilkan konfirmasi — langsung hapus ke Trash
        has_confirmation = False
        try:
            p.wait_for_selector(
                '[role="dialog"], .oc-dialog, button:has-text("Confirm"), button:has-text("Yes")',
                timeout=3000
            )
            has_confirmation = True
        except:
            has_confirmation = False

        if not has_confirmation:
            print("\n[TEMUAN] Tidak ada dialog konfirmasi!")
            print("         File langsung dihapus ke Trash tanpa meminta konfirmasi user.")
            print("         Ini adalah UX/safety issue di Nextcloud 28.")

        # Test ini sengaja FAIL untuk mendokumentasikan bahwa fitur konfirmasi
        # sebelum hapus multiple file TIDAK ada di Nextcloud 28.
        assert has_confirmation, (
            "[TEMUAN] Nextcloud 28 tidak menampilkan dialog konfirmasi saat menghapus "
            "multiple file. File langsung masuk Trash tanpa peringatan. "
            "Ini adalah UX/safety issue yang perlu diperhatikan."
        )