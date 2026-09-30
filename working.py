"""
eraPower Inventory CSV Downloader
==================================
Naming convention:  {store_no}_{SiteName}_{MAKE}_{New|Used}.csv
Example:            01_BooranCheltenham_CHERY_New.csv

Rooftops:
  01  Booran Cheltenham
  20  Cranbourne Hyundai
  40  South Morang Hyundai
  50  Dandenong Mitsubishi & Hyundai
  51  Cranbourne MG/MITS/KIA
  52  Dandenong NI & KI
  70  South Morang KIA
  90  Berwick MG & Hyundai

Setup (once):
  pip install playwright
  playwright install chromium

Run:
  python erapower_inventory_download.py
"""

import time
import re
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── CONFIG ────────────────────────────────────────────────────────────────────

BASE_URL    = "https://c2892-erapower.pentana.cloud/base/templates/vIndependent.htm"
USERNAME    = "shauns"
PASSWORD    = "Booran2"
WORKSTATION = "200"

DOWNLOAD_DIR = Path("erapower_downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

ROOFTOPS = [
    {"store": "01", "name": "BooranCheltenham",            "label": "01| Booran Cheltenham"},
    {"store": "20", "name": "CranbourneHyundai",           "label": "20| Cranbourne Hyundai"},
    {"store": "40", "name": "SouthMorangHyundai",          "label": "40| South Morang Hyundai"},
    {"store": "50", "name": "DandenongMitsubishi_Hyundai", "label": "50| Dandenong Mitsubishi & Hyundai"},
    {"store": "51", "name": "Cranbourne_MG_MITS_KIA",      "label": "51| Cranbourne MG/MITS/KIA"},
    {"store": "52", "name": "DandenongNI_KI",              "label": "52| Dandenong NI & KI"},
    {"store": "70", "name": "SouthMorangKIA",              "label": "70| South Morang KIA"},
    {"store": "90", "name": "BerwickMG_Hyundai",           "label": "90| Berwick MG & Hyundai"},
]

NEW_USED = [
    {"code": "New",  "value": "New"},
    {"code": "Used", "value": "Used"},
]

# ── CORE HELPERS ──────────────────────────────────────────────────────────────

def find_in_frames(page, selector, timeout_sec=8, must_visible=False):
    """Search page + all iframes for selector. Returns (element, frame) or (None, None)."""
    start = time.time()
    while time.time() - start < timeout_sec:
        for c in [page] + list(page.frames):
            try:
                loc = c.locator(selector)
                if loc.count() > 0:
                    if not must_visible or loc.first.is_visible():
                        return loc.first, c
            except Exception:
                pass
        time.sleep(0.15)
    return None, None


def wait_net(page, timeout=5000):
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass


def dismiss_any_dialog(page):
    """Dismiss any open alert/confirm dialog (e.g. LEPAS 'no stock' popup)."""
    try:
        page.evaluate("() => { if(window.__dialogDismissed === undefined) window.__dialogDismissed = 0; }")
    except Exception:
        pass


def fire_change(el):
    """Trigger eraPower VRE lifecycle + native change event on a select element."""
    try:
        el.evaluate("""(sel) => {
            if (window.VRE) {
                try { window.VRE.prefield(sel);       } catch(e) {}
                try { window.VRE.setSubmitQueue(sel); } catch(e) {}
                try { window.VRE.onChangeSelect(sel); } catch(e) {}
                try { window.VRE.postfield(sel);      } catch(e) {}
            }
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            sel.blur();
        }""")
    except Exception:
        pass


def wait_for_ajax(page, settle_sec=3.5):
    """
    Wait for eraPower's AJAX to complete.
    Strategy: install XHR counter once, then wait until it's 0 for 3 consecutive
    polls (each 0.4s = 1.2s quiet window), OR until settle_sec total elapses.
    From debug output we know PostMake takes ~2s on this server, so settle_sec=3.5
    gives a safe margin.
    """
    # Install monitor once
    for c in [page] + list(page.frames):
        try:
            c.evaluate("""() => {
                if (window.__xhrMonInstalled) return;
                window.__xhrPending = 0;
                const os = XMLHttpRequest.prototype.send;
                XMLHttpRequest.prototype.send = function(...a) {
                    window.__xhrPending++;
                    this.addEventListener('loadend', () => {
                        window.__xhrPending = Math.max(0, window.__xhrPending - 1);
                    });
                    return os.apply(this, a);
                };
                window.__xhrMonInstalled = true;
            }""")
        except Exception:
            pass

    # Poll until idle
    start   = time.time()
    streak  = 0
    needed  = 3   # 3 × 0.4s = 1.2s consecutive idle
    while time.time() - start < settle_sec:
        count = 0
        for c in [page] + list(page.frames):
            try:
                n = c.evaluate("() => window.__xhrPending ?? 0")
                count += (n or 0)
            except Exception:
                pass
        if count == 0:
            streak += 1
            if streak >= needed:
                break
        else:
            streak = 0
        time.sleep(0.4)


def get_row_text(page, table_name):
    """Read 'Row X of Y' from the named results table."""
    for sel in [
        f"span[name='{table_name}'] #SelectedRec",
        f"#{table_name} #SelectedRec",
        "#SelectedRec",
    ]:
        el, _ = find_in_frames(page, sel, timeout_sec=1)
        if el:
            try:
                return el.inner_text().strip().replace('\xa0', ' ')
            except Exception:
                pass
    return ""


def parse_count(text):
    m = re.search(r'of\s+(\d+)', text, re.I)
    return int(m.group(1)) if m else -1


# ── LOGIN ─────────────────────────────────────────────────────────────────────

def login(page):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
    wait_net(page)

    user_el, _ = find_in_frames(page, "#user, input[name='user']", timeout_sec=15)
    if not user_el:
        print("  (already authenticated)")
        return

    user_el.fill(USERNAME)
    user_el.press("Tab")
    time.sleep(2.5)   # wait for DefaultWks AJAX

    pw, _ = find_in_frames(page, "#password, input[name='password']")
    if pw: pw.fill(PASSWORD); pw.press("Tab"); time.sleep(0.3)

    ws, _ = find_in_frames(page, "#idLoginWorkstation")
    if ws:
        ws.press("Control+A"); ws.press("Backspace")
        ws.fill(WORKSTATION); ws.press("Tab"); time.sleep(0.3)

    btn, _ = find_in_frames(page, "#Button52, input[value='SIGN IN']")
    if btn: btn.click()
    else:   page.keyboard.press("Enter")

    time.sleep(2)
    wait_net(page, 30000)
    print("  Logged in ✓")


# ── ROOFTOP SWITCHER ──────────────────────────────────────────────────────────

def get_active_entity(page):
    el, _ = find_in_frames(page, "#EntityMenu", timeout_sec=2)
    if el:
        try: return el.inner_text().strip()
        except: pass
    return ""


def select_rooftop(page, rooftop):
    store = rooftop["store"]
    label = rooftop["label"]
    print(f"\n{'='*62}")
    print(f"  ROOFTOP  {store} | {rooftop['name']}")
    print(f"{'='*62}")

    # Already active?
    current = get_active_entity(page)
    if current and store in current:
        print(f"  ✓ Already active: {current}")
        return

    # Try JS API
    for c in [page] + list(page.frames):
        try:
            ok = c.evaluate(f"""() => {{
                const id = 'STORE{store}';
                if (window.top?.container?.setCurrentEntityAction)
                    {{ window.top.container.setCurrentEntityAction(id); return true; }}
                if (window.container?.setCurrentEntityAction)
                    {{ window.container.setCurrentEntityAction(id); return true; }}
                return false;
            }}""")
            if ok: break
        except: pass
    else:
        # UI fallback: open #EntityMenu and click row
        menu, _ = find_in_frames(page,
            "#EntityMenu, td#EntityMenu, [onclick*='entityMenuClick']", timeout_sec=5)
        if menu:
            menu.click(); time.sleep(1)

        store_id = f"STORE{store}"
        opt, _ = find_in_frames(page,
            f"#{store_id}, div[id='{store_id}'], [onclick*='{store_id}']", timeout_sec=5)
        if opt:
            opt.click()
        else:
            for c in [page] + list(page.frames):
                try:
                    c.evaluate(f"""() => {{
                        const el = document.getElementById('STORE{store}');
                        if (el) {{ el.click(); return true; }}
                    }}""")
                except: pass

    wait_net(page, 6000); time.sleep(0.5)
    current = get_active_entity(page)
    if current: print(f"  ✓ Active: {current}")


# ── NAVIGATION ────────────────────────────────────────────────────────────────

def navigate_to_inventory(page):
    print("  → Showroom …")
    for sel in ["span[xmlid='ShowrMenu']", "img[src*='flaticonShowroom']",
                "span.MenuItem:has-text('Showroom')", "td:has-text('Showroom')", "text=Showroom"]:
        el, _ = find_in_frames(page, sel, timeout_sec=2)
        if el: el.click(); break
    wait_net(page, 6000); time.sleep(0.3)

    print("  → Inventory Inquiry …")
    for sel in ["span[xmlid='StockInquiry']", "img[src*='StockInquirySearch']",
                "span.MenuItem:has-text('Inventory Inquiry')", "text=Inventory Inquiry"]:
        el, _ = find_in_frames(page, sel, timeout_sec=2)
        if el: el.click(); break
    wait_net(page, 6000); time.sleep(0.5)
    print("  At Inventory Inquiry ✓")


# ── DROPDOWN SETTERS ──────────────────────────────────────────────────────────

def set_new_used(page, value):
    """Set New/Used dropdown and wait for PostNewUsed AJAX to repopulate makes."""
    el, _ = find_in_frames(page, "#selNewUsed, select[name='selNewUsed']", timeout_sec=6)
    if not el:
        print("  ⚠ selNewUsed not found"); return False

    curr = el.evaluate("s => s.value")
    if curr == value:
        return True   # already set, no need to re-trigger

    try:    el.select_option(value=value)
    except: el.select_option(label=value)

    fire_change(el)

    # PostNewUsed repopulates the Make dropdown — must fully finish before we read makes
    wait_for_ajax(page, settle_sec=3.5)
    return True


def get_makes(page):
    """Read all non-empty options from #selMakeInventory."""
    el, _ = find_in_frames(page, "#selMakeInventory, select[name='selMakeInventory']", timeout_sec=6)
    if not el: return []
    try:
        return el.evaluate("""sel => Array.from(sel.options)
            .filter(o => o.value.trim() !== '')
            .map(o => {
                const text  = o.text.trim();
                const parts = text.split('-');
                const code  = parts.length > 1
                    ? parts.slice(1).join('-').trim().replace(/[^A-Za-z0-9]/g,'')
                    : o.value;
                return { val: o.value.trim(), code: code || o.value.trim(), label: text };
            })""")
    except: return []


def set_make(page, make_val, make_code):
    """
    Select make and wait for PostMake AJAX to complete.
    KEY: we re-read the dropdown value AFTER firing change to confirm it stuck,
    and we wait for full AJAX idle before returning.
    """
    el, _ = find_in_frames(page, "#selMakeInventory, select[name='selMakeInventory']", timeout_sec=6)
    if not el: return False

    # Select
    try:    el.select_option(value=make_val)
    except:
        try: el.select_option(label=make_code)
        except Exception as e:
            print(f"  ⚠ select_option failed: {e}"); return False

    # Confirm it took
    actual = el.evaluate("s => s.value")
    if actual != make_val:
        print(f"  ⚠ select_option returned {actual!r} not {make_val!r}")

    # Fire eraPower handlers + PostMake
    el.evaluate("""(sel) => {
        if (window.VRE) {
            try { window.VRE.prefield(sel);       } catch(e) {}
            try { window.VRE.setSubmitQueue(sel); } catch(e) {}
            try { window.VRE.onChangeSelect(sel); } catch(e) {}
            try { window.VRE.postfield(sel);      } catch(e) {}
        }
        if (window.VSC?.PostMake)
            try { window.VSC.PostMake('Inventory'); } catch(e) {}
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        sel.blur();
    }""")

    # Wait for PostMake AJAX to fully settle before caller touches Find
    wait_for_ajax(page, settle_sec=4.0)
    return True


def set_location_all(page):
    el, _ = find_in_frames(page, "#selLocation, select[name='selLocation']", timeout_sec=4)
    if not el: return
    curr = el.evaluate("s => s.value")
    if curr == "All": return
    try:    el.select_option(value="All")
    except:
        try: el.select_option(label="All")
        except: return
    fire_change(el)
    time.sleep(0.4)


# ── FIND + WAIT FOR REFRESH ───────────────────────────────────────────────────

def click_find_wait_refresh(page, table_name, text_before):
    """
    Click Find, then wait until the results table DOM actually changes.
    Uses a MutationObserver sentinel so we detect updates even when
    the row count happens to be identical across two different makes.
    """
    # Plant sentinel on the results table
    for c in [page] + list(page.frames):
        try:
            c.evaluate(f"""() => {{
                window.__tableRefreshed = false;
                const node =
                    document.querySelector("span[name='{table_name}']") ||
                    document.getElementById('{table_name}');
                if (!node) return;
                const obs = new MutationObserver(() => {{
                    window.__tableRefreshed = true;
                    obs.disconnect();
                }});
                obs.observe(node, {{ childList: true, subtree: true, characterData: true }});
            }}""")
        except Exception:
            pass

    # Click Find
    find_btn, _ = find_in_frames(page, "#But0, div[action='Find']", timeout_sec=5)
    if not find_btn:
        print("[Find btn missing]", end=" "); return ""

    try:    find_btn.click(timeout=3000)
    except:
        try: find_btn.evaluate("b => b.click()")
        except: print("[Find click failed]", end=" "); return ""

    # Poll up to 12s for either sentinel or row-text change
    deadline  = time.time() + 12.0
    refreshed = False
    while time.time() < deadline:
        time.sleep(0.35)

        # Check sentinel across frames
        for c in [page] + list(page.frames):
            try:
                if c.evaluate("() => window.__tableRefreshed ?? false"):
                    refreshed = True
                    break
            except: pass
        if refreshed: break

        # Fallback: row text changed
        now = get_row_text(page, table_name)
        if now and now != text_before:
            refreshed = True
            break

    text_after = get_row_text(page, table_name)
    status = "✓" if refreshed else "⚠ timeout"
    print(f"[{text_before!r} → {text_after!r} {status}]", end=" ", flush=True)

    # Brief render stabilisation
    time.sleep(0.6)
    return text_after


# ── DOWNLOAD ──────────────────────────────────────────────────────────────────

def download_csv(page, store, site, make_code, nu_code, rec_text):
    filename     = f"{store}_{site}_{make_code}_{nu_code}.csv"
    dest         = DOWNLOAD_DIR / filename
    total        = parse_count(rec_text)
    table_name   = "dtbNewResults" if nu_code == "New" else "dtbUsedResults"

    if total == 0:
        header = "stock#,carline,description,fa,colour,loc,list price,age,deal,status,open ro/po\n"
        dest.write_text(header, encoding="utf-8")
        print(f"→ {filename} (0 records)")
        return True

    # Locate export button scoped to our results table
    exp_btn = None
    for sel in [
        f"span[name='{table_name}'] img#Exp",
        f"#{table_name} img#Exp",
        f"span[name='{table_name}'] img[name='Exp']",
        f"span[name='{table_name}'] .TableExportUpButton",
    ]:
        exp_btn, _ = find_in_frames(page, sel, timeout_sec=3)
        if exp_btn: break

    if not exp_btn:
        print(f"✗ export btn not found ({filename})")
        return False

    try:
        with page.expect_download(timeout=20000) as dl_info:
            try:    exp_btn.click(force=True)
            except: exp_btn.evaluate("e => e.click()")
        dl_info.value.save_as(str(dest.resolve()))
        print(f"→ {filename}")
        time.sleep(0.4)
        return True
    except Exception as e:
        print(f"✗ download error: {e}")
        return False


# ── EXIT ──────────────────────────────────────────────────────────────────────

def exit_to_main(page):
    """Click Exit twice to return: Inventory Inquiry → Showroom → Main Menu."""
    for n in range(1, 3):
        btn, _ = find_in_frames(page,
            "span#caption:has-text('Exit'), div[action='Exit'], #But1", timeout_sec=3)
        if btn:
            btn.click()
        else:
            for c in [page] + list(page.frames):
                try:
                    c.evaluate("""() => {
                        const spans = [...document.querySelectorAll("span#caption,.ActUpButtonCaption")];
                        const ex = spans.find(s => s.textContent.trim().toLowerCase()==='exit');
                        if (ex) (ex.closest("div[action]") || ex).click();
                    }""")
                except: pass
        time.sleep(0.5)
        wait_net(page, 4000)
        print(f"    Exit {n}/2 ✓")
    time.sleep(0.4)


# ── PER-ROOFTOP LOOP ──────────────────────────────────────────────────────────

def run_rooftop(page, rooftop):
    select_rooftop(page, rooftop)
    navigate_to_inventory(page)

    store = rooftop["store"]
    site  = rooftop["name"]

    for nu in NEW_USED:
        table_name = "dtbNewResults" if nu["code"] == "New" else "dtbUsedResults"
        print(f"\n  ── {nu['code']} (table={table_name}) ──")

        # Set New/Used — PostNewUsed AJAX must finish before we read makes
        if not set_new_used(page, nu["value"]):
            print(f"  ✗ Could not set {nu['code']} — skipping"); continue

        makes = get_makes(page)
        if not makes:
            print("  ✗ No makes found — skipping"); continue
        print(f"  Makes: {[m['code'] for m in makes]}")

        for make in makes:
            make_val  = make["val"]
            make_code = make["code"]
            print(f"\n  → {nu['code']} / {make_code} … ", end="", flush=True)

            try:
                # 1. Confirm New/Used still correct (eraPower sometimes resets it)
                set_new_used(page, nu["value"])

                # 2. Set Make + wait for PostMake AJAX to fully complete
                if not set_make(page, make_val, make_code):
                    print("✗ make not set — skip"); continue

                # 3. Set Location = All
                set_location_all(page)

                # 4. Snapshot row count, click Find, wait for DOM refresh
                text_before = get_row_text(page, table_name)
                text_after  = click_find_wait_refresh(page, table_name, text_before)

                # 5. Download
                download_csv(page, store, site, make_code, nu["code"], text_after)

            except PWTimeout:
                print(f"✗ Timeout — skip")
            except Exception as e:
                print(f"✗ {e} — skip")

    print(f"\n  Exiting {site} …")
    exit_to_main(page)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            downloads_path=str(DOWNLOAD_DIR.resolve()),
            args=["--start-maximized"],
            slow_mo=80,
        )
        ctx  = browser.new_context(accept_downloads=True, viewport={"width": 1600, "height": 900})
        page = ctx.new_page()

        # Auto-dismiss any eraPower alert/confirm popups (e.g. LEPAS "no stock" dialog)
        page.on("dialog", lambda d: (print(f"  [dialog dismissed: {d.message!r}]"), d.accept()))

        print("=" * 62)
        print("  eraPower Inventory Downloader")
        print("=" * 62)

        login(page)

        for rooftop in ROOFTOPS:
            try:
                run_rooftop(page, rooftop)
            except Exception as e:
                print(f"\n  ✗ Fatal on {rooftop['store']}: {e}")
                try:
                    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
                    wait_net(page)
                except Exception:
                    pass

        print("\n" + "=" * 62)
        print(f"  Done!  Files in: {DOWNLOAD_DIR.resolve()}")
        print("=" * 62)
        input("\n  Press ENTER to close browser … ")
        browser.close()


if __name__ == "__main__":
    main()