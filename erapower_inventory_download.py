# """
# eraPower Inventory CSV Downloader
# ==================================
# Naming convention:  {store_no}_{SiteName}_{MAKE}_{New|Used}.csv
# Example:            90_BerwickMG_Hyundai_CHERY_New.csv

# Rooftops covered:
#   01  Booran Cheltenham
#   20  Cranbourne Hyundai
#   40  South Morang Hyundai
#   50  Dandenong Mitsubishi & Hyundai
#   51  Cranbourne MG/MITS/KIA
#   52  Dandenong NI & KI
#   70  South Morang KIA
#   90  Berwick MG & Hyundai

# Setup (run once):
#   pip install playwright
#   playwright install chromium

# Run:
#   python erapower_inventory_download.py
# """

# import os
# import re
# import time
# import shutil
# from pathlib import Path
# from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# # ── CONFIGURATION ─────────────────────────────────────────────────────────────

# BASE_URL    = "https://c2892-erapower.pentana.cloud/base/templates/vIndependent.htm"
# USERNAME    = "shauns"
# PASSWORD    = "Booran2"
# WORKSTATION = "200"

# DOWNLOAD_DIR = Path("erapower_downloads")
# DOWNLOAD_DIR.mkdir(exist_ok=True)

# # Exact text that appears in the rooftop picker dropdown (top-right of screen)
# ROOFTOPS = [
#     {"store": "01", "name": "BooranCheltenham",           "label": "01| Booran Cheltenham"},
#     {"store": "20", "name": "CranbourneHyundai",          "label": "20| Cranbourne Hyundai"},
#     {"store": "40", "name": "SouthMorangHyundai",         "label": "40| South Morang Hyundai"},
#     {"store": "50", "name": "DandenongMitsubishi_Hyundai","label": "50| Dandenong Mitsubishi & Hyundai"},
#     {"store": "51", "name": "Cranbourne_MG_MITS_KIA",     "label": "51| Cranbourne MG/MITS/KIA"},
#     {"store": "52", "name": "DandenongNI_KI",             "label": "52| Dandenong NI & KI"},
#     {"store": "70", "name": "SouthMorangKIA",             "label": "70| South Morang KIA"},
#     {"store": "90", "name": "BerwickMG_Hyundai",          "label": "90| Berwick MG & Hyundai"},
# ]

# MAKES = [
#     {"label": "CY  -  CHERY",     "code": "CHERY",   "val": "CY"},
#     {"label": "HY  -  HYUNDAI",   "code": "HYUNDAI", "val": "HY"},
#     {"label": "LE  -  LEPAS",     "code": "LEPAS",   "val": "LE"},
#     {"label": "MG  -  MG",        "code": "MG",      "val": "MG"},
#     {"label": "KI  -  KIA",       "code": "KIA",     "val": "KI"},
#     {"label": "IA  -  ISUZU UTE", "code": "ISUZU",   "val": "IA"},
#     {"label": "SK  -  SKODA",     "code": "SKODA",   "val": "SK"},
# ]

# NEW_USED = [
#     {"label": "New",  "code": "New"},
#     {"label": "Used", "code": "Used"},
# ]

# # ── HELPERS ───────────────────────────────────────────────────────────────────

# def wait_net(page, timeout=3000):
#     """Wait briefly for network to settle without stalling."""
#     try:
#         page.wait_for_load_state("networkidle", timeout=timeout)
#     except Exception:
#         pass
#     time.sleep(0.2)


# def find_element_in_frames(page, selector, timeout_sec=10, must_be_visible=False):
#     """Find an element matching selector across page and all current frames."""
#     start = time.time()
#     while time.time() - start < timeout_sec:
#         try:
#             containers = [page] + page.frames
#             for c in containers:
#                 try:
#                     loc = c.locator(selector)
#                     if loc.count() > 0:
#                         if not must_be_visible or loc.first.is_visible():
#                             return loc.first
#                 except Exception:
#                     continue
#         except Exception:
#             pass
#         time.sleep(0.15)
#     return None


# def login(page):
#     """Handle eraPower login screen if it appears."""
#     page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
#     wait_net(page)

#     print("  Waiting for login screen to load (checking page and frames)...")
#     user_el = find_element_in_frames(page, "#user, input[name='user'], input#user", timeout_sec=20)

#     if not user_el:
#         print("  (No login screen detected – already authenticated)")
#         return

#     print("  Login form detected. Entering username...")
#     try:
#         user_el.click()
#         user_el.fill(USERNAME)
#         user_el.press("Tab")

#         # eraPower triggers DefaultWks on blur, which reloads the iframe and sets default workstation (e.g. 129).
#         # Wait 2.5s for that reload to settle so we don't hit a detached frame.
#         time.sleep(2.5)

#         # Re-fetch password on the active frame
#         pass_el = find_element_in_frames(page, "#password, input[name='password'], input#password", timeout_sec=15)
#         if pass_el:
#             print("  Entering password...")
#             pass_el.click()
#             pass_el.fill(PASSWORD)
#             pass_el.press("Tab")
#             time.sleep(0.3)
#         else:
#             print("  ⚠ Password field not found after settling")

#         # Re-fetch workstation to clear the default (129) and set to configured WORKSTATION (200)
#         ws_el = find_element_in_frames(page, "#idLoginWorkstation, input[name='idLoginWorkstation']", timeout_sec=10)
#         if ws_el:
#             print(f"  Setting workstation to {WORKSTATION}...")
#             ws_el.click()
#             ws_el.press("Control+A")
#             ws_el.press("Backspace")
#             ws_el.fill(WORKSTATION)
#             ws_el.press("Tab")
#             time.sleep(0.3)

#         # Click SIGN IN button
#         btn_el = find_element_in_frames(page, "#Button52, input[value='SIGN IN'], input[name='Button52']", timeout_sec=10)
#         print("  Clicking SIGN IN...")
#         if btn_el:
#             btn_el.click()
#         else:
#             page.keyboard.press("Enter")

#         time.sleep(1.0)
#         wait_net(page, 30000)
#         print("  Logged in ✓")
#     except Exception as e:
#         print(f"  ⚠ Error while logging in: {e}")


# def get_current_entity(page):
#     """Read the active entity from #EntityMenu."""
#     try:
#         el = find_element_in_frames(page, "#EntityMenu", timeout_sec=2)
#         if el:
#             return el.inner_text().strip()
#     except Exception:
#         pass
#     return ""


# def click_rooftop_picker(page):
#     """
#     The top-right header shows the entity/rooftop menu (#EntityMenu).
#     Clicking it opens the list of all rooftops.
#     """
#     menu = find_element_in_frames(
#         page,
#         "#EntityMenu, td#EntityMenu, [onclick*='entityMenuClick'], [class*='EntityMenuWidth']",
#         timeout_sec=5
#     )
#     if menu:
#         try:
#             menu.hover()
#             time.sleep(0.3)
#         except Exception:
#             pass
#         menu.click()
#     else:
#         # Fallback to general selectors
#         loc = page.locator("a.location, #locationLink, [class*='siteloc' i]").first
#         loc.click()
#     time.sleep(1)


# def select_rooftop(page, rooftop: dict):
#     """Switch to a rooftop by clicking its name in the dropdown list."""
#     store = rooftop["store"]
#     print(f"\n{'='*62}")
#     print(f"  ROOFTOP  {store} | {rooftop['name']}")
#     print(f"{'='*62}")

#     # 1. If this rooftop is already active, don't open the picker
#     current = get_current_entity(page)
#     if current and (store in current or rooftop["name"][:6].lower() in current.lower()):
#         print(f"  ✓ Rooftop {store} is already selected ({current})")
#         return

#     # 2. Try eraPower's internal action API: window.top.container.setCurrentEntityAction('STORE{store}')
#     try:
#         switched = page.evaluate(f"""() => {{
#             const storeId = 'STORE{store}';
#             if (window.top && window.top.container && typeof window.top.container.setCurrentEntityAction === 'function') {{
#                 window.top.container.setCurrentEntityAction(storeId);
#                 return true;
#             }}
#             if (window.container && typeof window.container.setCurrentEntityAction === 'function') {{
#                 window.container.setCurrentEntityAction(storeId);
#                 return true;
#             }}
#             return false;
#         }}""")
#         if switched:
#             print(f"  Switched entity to STORE{store}")
#             time.sleep(0.5)
#             wait_net(page, 3000)
#             return
#     except Exception:
#         pass

#     # 3. Fallback: UI click via #EntityMenu
#     click_rooftop_picker(page)

#     store_id = f"STORE{store}"
#     selectors = [
#         f"#{store_id}",
#         f"div[id='{store_id}']",
#         f"[onclick*='{store_id}']",
#         f"div:has-text('{store}|')",
#     ]
#     option = None
#     for sel in selectors:
#         option = find_element_in_frames(page, sel, timeout_sec=4)
#         if option:
#             break

#     if option:
#         option.click()
#     else:
#         # Try JavaScript click across frames
#         try:
#             page.evaluate(f"""() => {{
#                 for (const win of [window, ...Array.from(window.frames)]) {{
#                     const el = win.document && win.document.getElementById('{store_id}');
#                     if (el) {{ el.click(); return true; }}
#                 }}
#                 return false;
#             }}""")
#         except Exception:
#             pass

#     wait_net(page, 5000)
#     time.sleep(0.4)

#     # Confirm active entity
#     current = get_current_entity(page)
#     if current:
#         print(f"  ✓ Active entity: {current}")


# def navigate_to_inventory(page):
#     """
#     From the main eraPower menu:
#       1. Click 'Showroom' tile/menu item (xmlid='ShowrMenu' / flaticonShowroom.png)
#       2. Click 'Inventory Inquiry' (xmlid='StockInquiry' / StockInquirySearch.png)
#     """
#     # ── Step 1: Showroom ──────────────────────────────────────────────────────
#     print("  Clicking Showroom...")
#     showroom_selectors = [
#         "span[xmlid='ShowrMenu']",
#         "img[src*='flaticonShowroom']",
#         "img[title='Showroom System']",
#         "#item2",
#         "span.MenuItem:has-text('Showroom')",
#         "td:has-text('Showroom')",
#     ]
#     showroom = None
#     for sel in showroom_selectors:
#         showroom = find_element_in_frames(page, sel, timeout_sec=2)
#         if showroom:
#             break

#     if showroom:
#         showroom.click()
#     else:
#         page.locator("span[xmlid='ShowrMenu'], img[src*='flaticonShowroom'], text=Showroom").first.click()

#     wait_net(page, 5000)
#     time.sleep(0.3)

#     # ── Step 2: Inventory Inquiry ─────────────────────────────────────────────
#     print("  Clicking Inventory Inquiry...")
#     inv_selectors = [
#         "span[xmlid='StockInquiry']",
#         "img[src*='StockInquirySearch']",
#         "img[title*='Search and view inventory details']",
#         "#item3",
#         "span.MenuItem:has-text('Inventory Inquiry')",
#         "td:has-text('Inventory Inquiry')",
#     ]
#     inv = None
#     for sel in inv_selectors:
#         inv = find_element_in_frames(page, sel, timeout_sec=2)
#         if inv:
#             break

#     if inv:
#         inv.click()
#     else:
#         page.locator("span[xmlid='StockInquiry'], img[src*='StockInquirySearch'], text='Inventory Inquiry'").first.click()

#     wait_net(page, 5000)
#     time.sleep(0.4)
#     print("  Navigated to Inventory Inquiry ✓")


# def select_new_used(page, nu_code: str) -> bool:
#     """
#     Ensure Condition (New or Used) is selected in #selNewUsed.
#     If already selected, simply confirm and return.
#     If changing (e.g. New -> Used), trigger PostNewUsed and wait for makes to repopulate.
#     """
#     sel_el = find_element_in_frames(page, "#selNewUsed, select[name='selNewUsed']", timeout_sec=5)
#     if not sel_el:
#         return False
#     try:
#         curr = sel_el.evaluate("sel => sel.value")
#         if curr == nu_code:
#             return True
#     except Exception:
#         pass

#     try:
#         sel_el.select_option(value=nu_code)
#     except Exception:
#         try:
#             sel_el.select_option(label=nu_code)
#         except Exception:
#             pass

#     try:
#         sel_el.evaluate("""(sel) => {
#             if (window.VRE) {
#                 if (typeof window.VRE.prefield === 'function') try { window.VRE.prefield(sel); } catch(e){}
#                 if (typeof window.VRE.setSubmitQueue === 'function') try { window.VRE.setSubmitQueue(sel); } catch(e){}
#                 if (typeof window.VRE.onChangeSelect === 'function') try { window.VRE.onChangeSelect(sel); } catch(e){}
#                 if (typeof window.VRE.postfield === 'function') try { window.VRE.postfield(sel); } catch(e){}
#             }
#             if (window.VSC && typeof window.VSC.PostNewUsed === 'function') {
#                 try { window.VSC.PostNewUsed(); } catch(e){}
#             }
#             sel.blur();
#         }""")
#     except Exception:
#         pass

#     time.sleep(2.0)
#     return True


# def select_make(page, make_val: str, make_code: str) -> bool:
#     """
#     Select make in #selMakeInventory, trigger eraPower's DSO lifecycle & PostMake,
#     and give eraPower adequate time to update state and carlines.
#     """
#     sel_el = find_element_in_frames(
#         page,
#         "#selMakeInventory, select[name='selMakeInventory']",
#         timeout_sec=5
#     )
#     if not sel_el:
#         return False

#     # Check if already set to this make
#     try:
#         curr_val = sel_el.evaluate("sel => sel.value")
#         if curr_val == make_val:
#             return True
#     except Exception:
#         pass

#     # Select the new option
#     selected = False
#     try:
#         sel_el.select_option(value=make_val, timeout=1000)
#         selected = True
#     except Exception:
#         pass

#     if not selected:
#         try:
#             sel_el.select_option(label=make_code, timeout=1000)
#             selected = True
#         except Exception:
#             pass

#     if not selected:
#         try:
#             matched_val = sel_el.evaluate("""(select, term) => {
#                 const termClean = term.toLowerCase().replace(/[^a-z0-9]/g, '');
#                 for (let i = 0; i < select.options.length; i++) {
#                     const opt = select.options[i];
#                     const textClean = opt.text.toLowerCase().replace(/[^a-z0-9]/g, '');
#                     const valClean = opt.value.toLowerCase().replace(/[^a-z0-9]/g, '');
#                     if (valClean === termClean || textClean.includes(termClean) || termClean.includes(valClean)) {
#                         return opt.value;
#                     }
#                 }
#                 return null;
#             }""", make_code)
#             if matched_val:
#                 sel_el.select_option(value=matched_val)
#                 selected = True
#         except Exception:
#             pass

#     # CRUCIAL: Trigger eraPower lifecycle handlers and PostMake
#     try:
#         sel_el.evaluate("""(sel) => {
#             if (window.VRE) {
#                 if (typeof window.VRE.prefield === 'function') try { window.VRE.prefield(sel); } catch(e){}
#                 if (typeof window.VRE.setSubmitQueue === 'function') try { window.VRE.setSubmitQueue(sel); } catch(e){}
#                 if (typeof window.VRE.onChangeSelect === 'function') try { window.VRE.onChangeSelect(sel); } catch(e){}
#                 if (typeof window.VRE.postfield === 'function') try { window.VRE.postfield(sel); } catch(e){}
#             }
#             if (window.VSC && typeof window.VSC.PostMake === 'function') {
#                 try { window.VSC.PostMake('Inventory'); } catch(e){}
#             }
#             sel.blur();
#         }""")
#     except Exception:
#         pass

#     # Give eraPower server call sufficient time to complete (2 seconds is proven in test)
#     time.sleep(2.0)
#     return True


# def select_location_all(page):
#     """Ensure Location dropdown is set to All (value='All')."""
#     loc_el = find_element_in_frames(page, "#selLocation, select[name='selLocation']", timeout_sec=4)
#     if not loc_el:
#         return False
#     try:
#         curr = loc_el.evaluate("sel => sel.value")
#         if curr == "All":
#             return True
#     except Exception:
#         pass

#     try:
#         loc_el.select_option(value="All")
#     except Exception:
#         try:
#             loc_el.select_option(label="All")
#         except Exception:
#             pass

#     try:
#         loc_el.evaluate("""(sel) => {
#             if (window.VRE) {
#                 if (typeof window.VRE.prefield === 'function') try { window.VRE.prefield(sel); } catch(e){}
#                 if (typeof window.VRE.setSubmitQueue === 'function') try { window.VRE.setSubmitQueue(sel); } catch(e){}
#                 if (typeof window.VRE.onChangeSelect === 'function') try { window.VRE.onChangeSelect(sel); } catch(e){}
#                 if (typeof window.VRE.postfield === 'function') try { window.VRE.postfield(sel); } catch(e){}
#             }
#             sel.blur();
#         }""")
#     except Exception:
#         pass
#     time.sleep(0.5)
#     return True


# def get_table_rec_info(page, target_table: str):
#     """
#     Returns (rec_text, total_records_int).
#     e.g. ('Row 1 of 151', 151) or ('Row 0 of 0', 0)
#     """
#     rec_el = find_element_in_frames(
#         page,
#         f"span[name='{target_table}'] #SelectedRec, #{target_table} #SelectedRec",
#         timeout_sec=2,
#         must_be_visible=False
#     )
#     if not rec_el:
#         return "", -1
#     try:
#         text = rec_el.inner_text().strip().replace('\xa0', ' ')
#         match = re.search(r'of\s+(\d+)', text, re.IGNORECASE)
#         if match:
#             return text, int(match.group(1))
#         return text, -1
#     except Exception:
#         return "", -1


# def click_find(page, target_table: str, prev_count: int = -1):
#     """
#     Click Find button (#But0), wait for server query to execute (takes 3.5-4s in eraPower),
#     and confirm the results table has updated.
#     """
#     find_btn = find_element_in_frames(
#         page,
#         "#But0, div[action='Find'], span#caption:has-text('Find')",
#         timeout_sec=4,
#         must_be_visible=False
#     )
#     if not find_btn:
#         print(" [Find btn not found]", end=" ", flush=True)
#         return False

#     time.sleep(0.3)

#     # 1. Click via Playwright
#     try:
#         find_btn.click(timeout=3000)
#     except Exception:
#         try:
#             find_btn.evaluate("btn => btn.click()")
#         except Exception:
#             pass

#     # 2. Wait for eraPower database query and table update.
#     # Live diagnostics proved eraPower query takes ~3.5 to 4.0 seconds.
#     # Sleep 2.0s initial query execution, then poll up to 5.0s:
#     time.sleep(2.0)
#     start_poll = time.time()
#     while time.time() - start_poll < 5.0:
#         _, curr_count = get_table_rec_info(page, target_table)
#         if curr_count != -1 and prev_count != -1 and curr_count != prev_count:
#             # Table count successfully updated!
#             time.sleep(0.5)
#             break
#         time.sleep(0.5)

#     return True


# def download_csv(page, store, site, make_code, nu_code, total_records: int) -> bool:
#     """
#     Click the Export button on the active results table (dtbNewResults or dtbUsedResults)
#     and save the CSV. If total_records is 0, writes empty CSV with header immediately.
#     """
#     filename = f"{store}_{site}_{make_code}_{nu_code}.csv"
#     dest = DOWNLOAD_DIR / filename
#     target_table = "dtbNewResults" if nu_code == "New" else "dtbUsedResults"

#     # If 0 records were found, write clean empty CSV with standard headers
#     if total_records == 0:
#         header = "stock#,carline,description,fa,colour,loc,dest loc,list price,age,age,deal,status,open ro/po\n"
#         dest.write_text(header, encoding="utf-8")
#         print(f"  ✔  Saved (0 records) → {filename}")
#         return True

#     # Specifically target the export icon in the active results table
#     exp_selectors = (
#         f"span[name='{target_table}'] img#Exp, "
#         f"#{target_table} img#Exp, "
#         f"span[name='{target_table}'] img[name='Exp'], "
#         f"span[name='{target_table}'] .TableExportUpButton, "
#         f"#{target_table} .TableExportUpButton"
#     )

#     exp_btn = find_element_in_frames(
#         page,
#         exp_selectors,
#         timeout_sec=4,
#         must_be_visible=False
#     )

#     if not exp_btn:
#         for container in [page] + page.frames:
#             try:
#                 candidate = container.locator(exp_selectors).first
#                 if candidate.count() > 0:
#                     exp_btn = candidate
#                     break
#             except Exception:
#                 continue

#     if not exp_btn:
#         print(f"    ✗ Export button not found for {target_table} ({filename})")
#         return False

#     try:
#         with page.expect_download(timeout=15000) as dl_info:
#             try:
#                 exp_btn.click(force=True)
#             except Exception:
#                 exp_btn.evaluate("el => el.click()")
#         download = dl_info.value
#         download.save_as(str(dest.resolve()))
#         print(f"  ✔  Saved → {filename}")
#         time.sleep(0.5)
#         return True
#     except Exception as e:
#         print(f"    ✗ Download note: {e}")
#         return False


# def exit_to_main(page):
#     """
#     Click the eraPower Exit button exactly 2 times:
#       1st click: Inventory Inquiry -> Showroom
#       2nd click: Showroom -> Main Menu
#     Then return so select_rooftop can change the store.
#     """
#     print("  Exiting back to main menu (2 clicks)...")
#     for click_num in (1, 2):
#         exit_btn = find_element_in_frames(
#             page,
#             "span#caption:has-text('Exit'), div[action='Exit'], .Standard-Label-PSWhiteonGreyActBtn:has-text('Exit'), #But1",
#             timeout_sec=3
#         )
#         if exit_btn:
#             exit_btn.click()
#             time.sleep(0.4)
#             wait_net(page, 4000)
#             print(f"    Exit {click_num}/2 ✓")
#         else:
#             try:
#                 page.evaluate("""() => {
#                     const spans = Array.from(document.querySelectorAll("span#caption, .ActUpButtonCaption"));
#                     const exit = spans.find(s => s.textContent.trim().toLowerCase() === 'exit');
#                     if (exit) (exit.closest("div[action]") || exit).click();
#                 }""")
#                 time.sleep(0.4)
#                 print(f"    Exit {click_num}/2 (JS) ✓")
#             except Exception:
#                 pass
#     time.sleep(0.4)


# def get_dropdown_makes(page, timeout_sec=5):
#     """
#     Read all make options dynamically from #selMakeInventory.
#     Returns list of dicts: [{'val': 'CY', 'code': 'CHERY', 'label': 'CY  -  CHERY'}, ...]
#     """
#     start = time.time()
#     while time.time() - start < timeout_sec:
#         el = find_element_in_frames(page, "#selMakeInventory, select[name='selMakeInventory']", timeout_sec=1)
#         if el:
#             try:
#                 options = el.evaluate("""select => {
#                     const list = [];
#                     for (let i = 0; i < select.options.length; i++) {
#                         const opt = select.options[i];
#                         const val = (opt.value || '').trim();
#                         if (val && val !== '') {
#                             let text = (opt.text || '').trim();
#                             let code = text;
#                             if (text.includes('-')) {
#                                 code = text.split('-').slice(1).join('-').trim();
#                             }
#                             code = code.replace(/[^A-Za-z0-9_]/g, '');
#                             list.push({ val: val, code: code || val, label: text });
#                         }
#                     }
#                     return list;
#                 }""")
#                 if options and len(options) > 0:
#                     return options
#             except Exception:
#                 pass
#         time.sleep(0.2)
#     return []


# # ── CORE LOOP ─────────────────────────────────────────────────────────────────

# def run_rooftop(page, rooftop: dict):
#     store = rooftop["store"]
#     site  = rooftop["name"]

#     # 1. Switch rooftop via header picker / API
#     select_rooftop(page, rooftop)

#     # 2. Navigate: Showroom → Inventory Inquiry
#     navigate_to_inventory(page)

#     # 3. For each condition (New, then Used)
#     for nu in NEW_USED:
#         print(f"\n  ── Condition: {nu['code']} ──")
#         target_table = "dtbNewResults" if nu["code"] == "New" else "dtbUsedResults"

#         # Select New/Used ONCE per condition and let PostNewUsed finish
#         nu_ok = select_new_used(page, nu["code"])
#         if not nu_ok:
#             print(f"  ✗ Could not select {nu['code']} in New/Used dropdown")
#             continue

#         # Dynamically read all available makes for this rooftop and condition
#         dropdown_makes = get_dropdown_makes(page, timeout_sec=5)
#         if not dropdown_makes:
#             dropdown_makes = MAKES

#         make_names = ", ".join(m["code"] for m in dropdown_makes)
#         print(f"  Available makes ({len(dropdown_makes)}): {make_names}")

#         last_count = -1
#         for make in dropdown_makes:
#             make_code = make.get("code") or make.get("val")
#             make_val = make.get("val") or make_code
#             print(f"  → {nu['code']} / {make_code} …", end=" ", flush=True)

#             try:
#                 # ── Step 1: Select Condition (New/Used) in each loop ──────────
#                 select_new_used(page, nu["code"])

#                 # ── Step 2: Select Make in each loop ──────────────────────────
#                 ok_make = select_make(page, make_val, make_code)
#                 if not ok_make:
#                     print("could not set make dropdown – skipping")
#                     continue

#                 # ── Step 3: Select Location to All in each loop ───────────────
#                 select_location_all(page)

#                 # ── Step 4: Find & wait for query to update table ─────────────
#                 click_find(page, target_table, prev_count=last_count)

#                 # ── Step 5: Read record count from updated table ──────────────
#                 rec_text, rec_count = get_table_rec_info(page, target_table)
#                 last_count = rec_count
#                 if rec_text:
#                     print(f"[{rec_text}]", end=" ", flush=True)

#                 # ── Step 6: Download CSV ──────────────────────────────────────
#                 download_csv(page, store, site, make_code, nu["code"], total_records=rec_count)

#             except PWTimeout:
#                 print(f"\n    ✗ Timeout – skipping {make_code} / {nu['code']}")
#             except Exception as e:
#                 print(f"\n    ✗ Error: {e} – skipping")

#     # 4. Exit back through to the main menu via Exit button (2 clicks)
#     print(f"\n  Exiting {site} …")
#     exit_to_main(page)


# # ── ENTRY POINT ───────────────────────────────────────────────────────────────

# def main():
#     with sync_playwright() as p:
#         browser = p.chromium.launch(
#             headless=False,                  # visible browser – you can watch progress
#             downloads_path=str(DOWNLOAD_DIR.resolve()),
#             args=["--start-maximized"],
#             slow_mo=200,                     # slight slow-down helps stability
#         )
#         ctx = browser.new_context(
#             accept_downloads=True,
#             viewport={"width": 1600, "height": 900},
#         )
#         page = ctx.new_page()
#         # Automatically dismiss any browser alert / prompt dialogs without hanging
#         page.on("dialog", lambda dialog: dialog.accept())

#         print("=" * 62)
#         print("  eraPower Inventory Downloader")
#         print("=" * 62)

#         login(page)

#         for rooftop in ROOFTOPS:
#             try:
#                 run_rooftop(page, rooftop)
#             except Exception as e:
#                 print(f"\n  ✗ Fatal error on {rooftop['store']}: {e}")
#                 # Try to recover by going back to BASE_URL
#                 try:
#                     page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
#                     wait_net(page)
#                 except Exception:
#                     pass

#         print("\n" + "=" * 62)
#         print(f"  All done!  Files saved to:  {DOWNLOAD_DIR.resolve()}")
#         print("=" * 62)

#         input("\n  Press ENTER to close the browser …")
#         browser.close()


# if __name__ == "__main__":
#     main()"""

# """
# eraPower Inventory CSV Downloader
# ==================================
# Naming convention:  {store_no}_{SiteName}_{MAKE}_{New|Used}.csv
# Example:            90_BerwickMG_Hyundai_CHERY_New.csv

# Rooftops covered:
#   01  Booran Cheltenham
#   20  Cranbourne Hyundai
#   40  South Morang Hyundai
#   50  Dandenong Mitsubishi & Hyundai
#   51  Cranbourne MG/MITS/KIA
#   52  Dandenong NI & KI
#   70  South Morang KIA
#   90  Berwick MG & Hyundai

# Setup (run once):
#   pip install playwright
#   playwright install chromium

# Run:
#   python erapower_inventory_download.py
# """

# import os
# import re
# import time
# import shutil
# from pathlib import Path
# from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# # ── CONFIGURATION ─────────────────────────────────────────────────────────────

# BASE_URL    = "https://c2892-erapower.pentana.cloud/base/templates/vIndependent.htm"
# USERNAME    = "shauns"
# PASSWORD    = "Booran2"
# WORKSTATION = "200"

# DOWNLOAD_DIR = Path("erapower_downloads")
# DOWNLOAD_DIR.mkdir(exist_ok=True)

# ROOFTOPS = [
#     {"store": "01", "name": "BooranCheltenham",           "label": "01| Booran Cheltenham"},
#     {"store": "20", "name": "CranbourneHyundai",          "label": "20| Cranbourne Hyundai"},
#     {"store": "40", "name": "SouthMorangHyundai",         "label": "40| South Morang Hyundai"},
#     {"store": "50", "name": "DandenongMitsubishi_Hyundai","label": "50| Dandenong Mitsubishi & Hyundai"},
#     {"store": "51", "name": "Cranbourne_MG_MITS_KIA",     "label": "51| Cranbourne MG/MITS/KIA"},
#     {"store": "52", "name": "DandenongNI_KI",             "label": "52| Dandenong NI & KI"},
#     {"store": "70", "name": "SouthMorangKIA",             "label": "70| South Morang KIA"},
#     {"store": "90", "name": "BerwickMG_Hyundai",          "label": "90| Berwick MG & Hyundai"},
# ]

# NEW_USED = [
#     {"label": "New",  "code": "New"},
#     {"label": "Used", "code": "Used"},
# ]

# # ── HELPERS ───────────────────────────────────────────────────────────────────

# def wait_net(page, timeout=3000):
#     try:
#         page.wait_for_load_state("networkidle", timeout=timeout)
#     except Exception:
#         pass
#     time.sleep(0.2)


# def find_element_in_frames(page, selector, timeout_sec=10, must_be_visible=False):
#     """Find an element across the page and all iframes."""
#     start = time.time()
#     while time.time() - start < timeout_sec:
#         try:
#             containers = [page] + list(page.frames)
#             for c in containers:
#                 try:
#                     loc = c.locator(selector)
#                     if loc.count() > 0:
#                         if not must_be_visible or loc.first.is_visible():
#                             return loc.first
#                 except Exception:
#                     continue
#         except Exception:
#             pass
#         time.sleep(0.15)
#     return None


# def js_in_frames(page, script):
#     """Run a JS snippet in page and each frame, return first truthy result."""
#     for container in [page] + list(page.frames):
#         try:
#             result = container.evaluate(script)
#             if result:
#                 return result
#         except Exception:
#             continue
#     return None


# # ── LOGIN ─────────────────────────────────────────────────────────────────────

# def login(page):
#     page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
#     wait_net(page)
#     print("  Checking for login screen …")

#     user_el = find_element_in_frames(page, "#user, input[name='user'], input#user", timeout_sec=20)
#     if not user_el:
#         print("  (No login screen – already authenticated)")
#         return

#     print("  Login form detected. Filling credentials …")
#     user_el.click()
#     user_el.fill(USERNAME)
#     user_el.press("Tab")
#     time.sleep(2.5)   # wait for DefaultWks AJAX to settle

#     pass_el = find_element_in_frames(page, "#password, input[name='password']", timeout_sec=15)
#     if pass_el:
#         pass_el.click()
#         pass_el.fill(PASSWORD)
#         pass_el.press("Tab")
#         time.sleep(0.3)

#     ws_el = find_element_in_frames(page, "#idLoginWorkstation, input[name='idLoginWorkstation']", timeout_sec=10)
#     if ws_el:
#         ws_el.click()
#         ws_el.press("Control+A")
#         ws_el.press("Backspace")
#         ws_el.fill(WORKSTATION)
#         ws_el.press("Tab")
#         time.sleep(0.3)

#     btn_el = find_element_in_frames(page, "#Button52, input[value='SIGN IN'], input[name='Button52']", timeout_sec=10)
#     if btn_el:
#         btn_el.click()
#     else:
#         page.keyboard.press("Enter")

#     time.sleep(1.0)
#     wait_net(page, 30000)
#     print("  Logged in ✓")


# # ── ROOFTOP SWITCHER ──────────────────────────────────────────────────────────

# def get_current_entity(page):
#     try:
#         el = find_element_in_frames(page, "#EntityMenu", timeout_sec=2)
#         if el:
#             return el.inner_text().strip()
#     except Exception:
#         pass
#     return ""


# def select_rooftop(page, rooftop: dict):
#     store = rooftop["store"]
#     print(f"\n{'='*62}")
#     print(f"  ROOFTOP  {store} | {rooftop['name']}")
#     print(f"{'='*62}")

#     current = get_current_entity(page)
#     if current and store in current:
#         print(f"  ✓ Already on {store} ({current})")
#         return

#     # Try JS API first
#     switched = js_in_frames(page, f"""() => {{
#         const storeId = 'STORE{store}';
#         if (window.top?.container?.setCurrentEntityAction) {{
#             window.top.container.setCurrentEntityAction(storeId); return true;
#         }}
#         if (window.container?.setCurrentEntityAction) {{
#             window.container.setCurrentEntityAction(storeId); return true;
#         }}
#         return false;
#     }}""")

#     if not switched:
#         # UI fallback: open entity picker and click the row
#         menu = find_element_in_frames(
#             page,
#             "#EntityMenu, td#EntityMenu, [onclick*='entityMenuClick'], [class*='EntityMenuWidth']",
#             timeout_sec=5
#         )
#         if menu:
#             menu.click()
#             time.sleep(1)

#         store_id = f"STORE{store}"
#         option = None
#         for sel in [f"#{store_id}", f"div[id='{store_id}']", f"[onclick*='{store_id}']"]:
#             option = find_element_in_frames(page, sel, timeout_sec=4)
#             if option:
#                 break

#         if option:
#             option.click()
#         else:
#             js_in_frames(page, f"""() => {{
#                 for (const win of [window, ...Array.from(window.frames || [])]) {{
#                     const el = win.document?.getElementById('{store_id}');
#                     if (el) {{ el.click(); return true; }}
#                 }}
#                 return false;
#             }}""")

#     wait_net(page, 5000)
#     time.sleep(0.4)
#     current = get_current_entity(page)
#     if current:
#         print(f"  ✓ Active entity: {current}")


# # ── NAVIGATION ────────────────────────────────────────────────────────────────

# def navigate_to_inventory(page):
#     print("  Clicking Showroom …")
#     showroom = None
#     for sel in ["span[xmlid='ShowrMenu']", "img[src*='flaticonShowroom']",
#                 "span.MenuItem:has-text('Showroom')", "td:has-text('Showroom')"]:
#         showroom = find_element_in_frames(page, sel, timeout_sec=2)
#         if showroom:
#             break
#     if showroom:
#         showroom.click()
#     else:
#         page.locator("text=Showroom").first.click()
#     wait_net(page, 5000)
#     time.sleep(0.3)

#     print("  Clicking Inventory Inquiry …")
#     inv = None
#     for sel in ["span[xmlid='StockInquiry']", "img[src*='StockInquirySearch']",
#                 "span.MenuItem:has-text('Inventory Inquiry')", "td:has-text('Inventory Inquiry')"]:
#         inv = find_element_in_frames(page, sel, timeout_sec=2)
#         if inv:
#             break
#     if inv:
#         inv.click()
#     else:
#         page.locator("text=Inventory Inquiry").first.click()
#     wait_net(page, 5000)
#     time.sleep(0.4)
#     print("  At Inventory Inquiry ✓")


# # ── DROPDOWN HELPERS ──────────────────────────────────────────────────────────

# def trigger_change(el):
#     """Fire eraPower's VRE lifecycle + blur so server AJAX is triggered."""
#     try:
#         el.evaluate("""(sel) => {
#             if (window.VRE) {
#                 try { window.VRE.prefield(sel); } catch(e){}
#                 try { window.VRE.setSubmitQueue(sel); } catch(e){}
#                 try { window.VRE.onChangeSelect(sel); } catch(e){}
#                 try { window.VRE.postfield(sel); } catch(e){}
#             }
#             // Dispatch native change so any addEventListener also fires
#             sel.dispatchEvent(new Event('change', { bubbles: true }));
#             sel.blur();
#         }""")
#     except Exception:
#         pass


# def select_new_used(page, nu_code: str):
#     el = find_element_in_frames(page, "#selNewUsed, select[name='selNewUsed']", timeout_sec=5)
#     if not el:
#         return False
#     try:
#         curr = el.evaluate("s => s.value")
#         if curr == nu_code:
#             return True
#     except Exception:
#         pass
#     try:
#         el.select_option(value=nu_code)
#     except Exception:
#         try:
#             el.select_option(label=nu_code)
#         except Exception:
#             pass
#     trigger_change(el)
#     # PostNewUsed repopulates makes — give it time
#     time.sleep(2.5)
#     return True


# def get_dropdown_makes(page, timeout_sec=6):
#     """Read available makes from #selMakeInventory dynamically."""
#     start = time.time()
#     while time.time() - start < timeout_sec:
#         el = find_element_in_frames(page, "#selMakeInventory, select[name='selMakeInventory']", timeout_sec=1)
#         if el:
#             try:
#                 options = el.evaluate("""select => {
#                     const list = [];
#                     for (let i = 0; i < select.options.length; i++) {
#                         const opt = select.options[i];
#                         const val = (opt.value || '').trim();
#                         if (!val) continue;
#                         let text = (opt.text || '').trim();
#                         let code = text.includes('-')
#                             ? text.split('-').slice(1).join('-').trim().replace(/[^A-Za-z0-9]/g,'')
#                             : val;
#                         list.push({ val, code: code || val, label: text });
#                     }
#                     return list;
#                 }""")
#                 if options and len(options) > 0:
#                     return options
#             except Exception:
#                 pass
#         time.sleep(0.3)
#     return []


# def select_make(page, make_val: str, make_code: str) -> bool:
#     """
#     Select make, fire change handlers, then wait for the PostMake AJAX to complete.
#     KEY FIX: we stamp a 'data-selecting' attribute on the select before clicking Find
#     so we can detect when the server response has come back and the DOM has settled.
#     """
#     el = find_element_in_frames(page, "#selMakeInventory, select[name='selMakeInventory']", timeout_sec=5)
#     if not el:
#         return False

#     # Already set?
#     try:
#         curr = el.evaluate("s => s.value")
#         if curr == make_val:
#             print(f"[already {make_val}]", end=" ")
#     except Exception:
#         pass

#     # Set the value
#     selected = False
#     for attempt in [lambda: el.select_option(value=make_val),
#                     lambda: el.select_option(label=make_code)]:
#         try:
#             attempt()
#             selected = True
#             break
#         except Exception:
#             continue

#     if not selected:
#         # Fuzzy match
#         try:
#             matched = el.evaluate("""(sel, term) => {
#                 const t = term.toLowerCase().replace(/[^a-z0-9]/g,'');
#                 for (let i=0; i<sel.options.length; i++){
#                     const o=sel.options[i];
#                     const v=o.value.toLowerCase().replace(/[^a-z0-9]/g,'');
#                     const x=o.text.toLowerCase().replace(/[^a-z0-9]/g,'');
#                     if(v===t||x.includes(t)||t.includes(v)) return o.value;
#                 }
#                 return null;
#             }""", make_code)
#             if matched:
#                 el.select_option(value=matched)
#                 selected = True
#         except Exception:
#             pass

#     # Fire VRE lifecycle + PostMake
#     trigger_change(el)
#     try:
#         el.evaluate("""(sel) => {
#             if (window.VSC?.PostMake) {
#                 try { window.VSC.PostMake('Inventory'); } catch(e){}
#             }
#         }""")
#     except Exception:
#         pass

#     # Wait for PostMake AJAX to complete — poll XHR idle
#     _wait_for_ajax_idle(page, wait_sec=3.0, poll_interval=0.3)
#     return selected


# def select_location_all(page):
#     el = find_element_in_frames(page, "#selLocation, select[name='selLocation']", timeout_sec=4)
#     if not el:
#         return False
#     try:
#         if el.evaluate("s => s.value") == "All":
#             return True
#     except Exception:
#         pass
#     try:
#         el.select_option(value="All")
#     except Exception:
#         try:
#             el.select_option(label="All")
#         except Exception:
#             pass
#     trigger_change(el)
#     time.sleep(0.5)
#     return True


# # ── AJAX IDLE DETECTOR ────────────────────────────────────────────────────────

# def _wait_for_ajax_idle(page, wait_sec: float = 4.0, poll_interval: float = 0.3):
#     """
#     Poll every `poll_interval` seconds until no XHR/fetch is in-flight,
#     or until `wait_sec` total has elapsed.
#     Injects a tiny XHR monitor into the page on first call (idempotent).
#     """
#     try:
#         # Inject monitor once (idempotent guard via window.__xhrCount)
#         js_in_frames(page, """() => {
#             if (window.__xhrMonitorInstalled) return;
#             window.__xhrCount = 0;
#             const origOpen = XMLHttpRequest.prototype.open;
#             const origSend = XMLHttpRequest.prototype.send;
#             XMLHttpRequest.prototype.send = function(...args) {
#                 window.__xhrCount++;
#                 this.addEventListener('loadend', () => { window.__xhrCount = Math.max(0, window.__xhrCount - 1); });
#                 return origSend.apply(this, args);
#             };
#             const origFetch = window.fetch;
#             if (origFetch) {
#                 window.fetch = function(...args) {
#                     window.__xhrCount++;
#                     return origFetch.apply(this, args).finally(() => {
#                         window.__xhrCount = Math.max(0, window.__xhrCount - 1);
#                     });
#                 };
#             }
#             window.__xhrMonitorInstalled = true;
#         }""")
#     except Exception:
#         pass

#     start = time.time()
#     idle_streak = 0          # consecutive polls where XHR count == 0
#     needed_streak = 3        # require 3 consecutive idle polls (~0.9s) before declaring idle

#     while time.time() - start < wait_sec:
#         try:
#             count = js_in_frames(page, "() => window.__xhrCount ?? 0") or 0
#             if count == 0:
#                 idle_streak += 1
#                 if idle_streak >= needed_streak:
#                     break
#             else:
#                 idle_streak = 0
#         except Exception:
#             pass
#         time.sleep(poll_interval)


# # ── FIND & RESULTS ────────────────────────────────────────────────────────────

# def get_row_count_text(page, target_table: str) -> str:
#     """
#     Read the 'Row X of Y' span from the results table.
#     Returns the raw text (e.g. 'Row 1 of 151') or '' if not found.
#     """
#     selectors = [
#         f"span[name='{target_table}'] #SelectedRec",
#         f"#{target_table} #SelectedRec",
#         f"span[name='{target_table}'] span[id*='Rec']",
#         "#SelectedRec",
#     ]
#     for sel in selectors:
#         el = find_element_in_frames(page, sel, timeout_sec=1, must_be_visible=False)
#         if el:
#             try:
#                 return el.inner_text().strip().replace('\xa0', ' ')
#             except Exception:
#                 pass
#     return ""


# def parse_total(text: str) -> int:
#     m = re.search(r'of\s+(\d+)', text, re.IGNORECASE)
#     return int(m.group(1)) if m else -1


# def click_find_and_wait(page, target_table: str, prev_make_val: str, curr_make_val: str):
#     """
#     THE FIX:
#     Rather than comparing row counts (which can be identical across different makes),
#     we use a 3-phase approach:
#       1. Read the CURRENT row-count text before clicking Find (snapshot_before).
#       2. Inject a DOM mutation sentinel on the results table so we know the
#          moment the server pushes new HTML back.
#       3. Click Find, wait for the sentinel to fire OR for row-count text to change,
#          then add a short stabilisation sleep.
#     """
#     target_table_name = target_table   # e.g. 'dtbNewResults'

#     # ── Phase 1: snapshot before ──────────────────────────────────────────────
#     text_before = get_row_count_text(page, target_table_name)
#     print(f"[before={text_before!r}]", end=" ", flush=True)

#     # ── Phase 2: inject sentinel ──────────────────────────────────────────────
#     try:
#         js_in_frames(page, f"""() => {{
#             window.__tableRefreshed = false;
#             const container =
#                 document.querySelector("span[name='{target_table_name}']") ||
#                 document.getElementById('{target_table_name}');
#             if (!container) return;
#             const obs = new MutationObserver(() => {{
#                 window.__tableRefreshed = true;
#                 obs.disconnect();
#             }});
#             obs.observe(container, {{ childList: true, subtree: true }});
#         }}""")
#     except Exception:
#         pass

#     # ── Phase 3: click Find ───────────────────────────────────────────────────
#     find_btn = find_element_in_frames(
#         page,
#         "#But0, div[action='Find'], span#caption:has-text('Find')",
#         timeout_sec=4,
#         must_be_visible=False
#     )
#     if not find_btn:
#         print("[Find btn missing]", end=" ")
#         return

#     try:
#         find_btn.click(timeout=3000)
#     except Exception:
#         try:
#             find_btn.evaluate("b => b.click()")
#         except Exception:
#             pass

#     # ── Phase 4: wait for table refresh ──────────────────────────────────────
#     # Poll for up to 10 seconds for either:
#     #   (a) our MutationObserver sentinel fires  (DOM replaced)
#     #   (b) the row-count text changes           (content updated)
#     #   (c) XHR becomes idle for 3 consecutive polls
#     deadline = time.time() + 10.0
#     refreshed = False
#     while time.time() < deadline:
#         time.sleep(0.35)
#         # Check sentinel
#         try:
#             sentinel = js_in_frames(page, "() => window.__tableRefreshed ?? false")
#             if sentinel:
#                 refreshed = True
#                 break
#         except Exception:
#             pass
#         # Check text change
#         text_now = get_row_count_text(page, target_table_name)
#         if text_now and text_now != text_before:
#             refreshed = True
#             break

#     status = "refreshed ✓" if refreshed else "timeout—continuing anyway"
#     text_after = get_row_count_text(page, target_table_name)
#     print(f"[after={text_after!r} {status}]", end=" ", flush=True)

#     # Short stabilisation pause so the full row data renders
#     time.sleep(0.8)
#     return text_after


# # ── DOWNLOAD ──────────────────────────────────────────────────────────────────

# def download_csv(page, store, site, make_code, nu_code, rec_text: str) -> bool:
#     filename  = f"{store}_{site}_{make_code}_{nu_code}.csv"
#     dest      = DOWNLOAD_DIR / filename
#     total     = parse_total(rec_text)
#     target_table = "dtbNewResults" if nu_code == "New" else "dtbUsedResults"

#     if total == 0:
#         header = "stock#,carline,description,fa,colour,loc,list price,age,deal,status,open ro/po\n"
#         dest.write_text(header, encoding="utf-8")
#         print(f"→ Saved (0 records) {filename}")
#         return True

#     exp_selectors = [
#         f"span[name='{target_table}'] img#Exp",
#         f"#{target_table} img#Exp",
#         f"span[name='{target_table}'] img[name='Exp']",
#         f"span[name='{target_table}'] .TableExportUpButton",
#         f"#{target_table} .TableExportUpButton",
#     ]

#     exp_btn = None
#     for sel in exp_selectors:
#         exp_btn = find_element_in_frames(page, sel, timeout_sec=3, must_be_visible=False)
#         if exp_btn:
#             break

#     if not exp_btn:
#         print(f"✗ Export button not found ({filename})")
#         return False

#     try:
#         with page.expect_download(timeout=20000) as dl_info:
#             try:
#                 exp_btn.click(force=True)
#             except Exception:
#                 exp_btn.evaluate("e => e.click()")
#         download = dl_info.value
#         download.save_as(str(dest.resolve()))
#         print(f"→ Saved {filename}")
#         time.sleep(0.5)
#         return True
#     except Exception as e:
#         print(f"✗ Download error: {e} ({filename})")
#         return False


# # ── EXIT ──────────────────────────────────────────────────────────────────────

# def exit_to_main(page):
#     """Click Exit twice: Inventory Inquiry → Showroom → Main Menu."""
#     print("  Exiting (2× Exit) …")
#     for n in range(1, 3):
#         exit_btn = find_element_in_frames(
#             page,
#             "span#caption:has-text('Exit'), div[action='Exit'], #But1",
#             timeout_sec=3
#         )
#         if exit_btn:
#             exit_btn.click()
#         else:
#             js_in_frames(page, """() => {
#                 const spans = [...document.querySelectorAll("span#caption, .ActUpButtonCaption")];
#                 const ex = spans.find(s => s.textContent.trim().toLowerCase() === 'exit');
#                 if (ex) (ex.closest("div[action]") || ex).click();
#             }""")
#         time.sleep(0.5)
#         wait_net(page, 4000)
#         print(f"    Exit {n}/2 ✓")
#     time.sleep(0.4)


# # ── CORE LOOP ─────────────────────────────────────────────────────────────────

# def run_rooftop(page, rooftop: dict):
#     store = rooftop["store"]
#     site  = rooftop["name"]

#     select_rooftop(page, rooftop)
#     navigate_to_inventory(page)

#     for nu in NEW_USED:
#         target_table = "dtbNewResults" if nu["code"] == "New" else "dtbUsedResults"
#         print(f"\n  ── Condition: {nu['code']} (table={target_table}) ──")

#         # Select New/Used once; PostNewUsed repopulates makes
#         if not select_new_used(page, nu["code"]):
#             print(f"  ✗ Could not select {nu['code']} – skipping")
#             continue

#         # Read makes dynamically so we only iterate what's available
#         dropdown_makes = get_dropdown_makes(page, timeout_sec=6)
#         if not dropdown_makes:
#             print("  ✗ Make dropdown empty – skipping condition")
#             continue
#         print(f"  Makes found: {[m['code'] for m in dropdown_makes]}")

#         prev_make_val = ""

#         for make in dropdown_makes:
#             make_val  = make.get("val") or make.get("code")
#             make_code = make.get("code") or make_val
#             print(f"\n  → {nu['code']} / {make_code} … ", end="", flush=True)

#             try:
#                 # 1. Set New/Used (confirm it's still correct)
#                 select_new_used(page, nu["code"])

#                 # 2. Set Make — includes PostMake AJAX wait
#                 ok = select_make(page, make_val, make_code)
#                 if not ok:
#                     print("✗ make not set – skipping")
#                     continue

#                 # 3. Location = All
#                 select_location_all(page)

#                 # 4. Click Find and wait for the table to actually refresh
#                 rec_text = click_find_and_wait(page, target_table, prev_make_val, make_val)

#                 # 5. Download
#                 download_csv(page, store, site, make_code, nu["code"], rec_text or "")

#                 prev_make_val = make_val

#             except PWTimeout:
#                 print(f"✗ Timeout – skipping")
#             except Exception as e:
#                 print(f"✗ Error: {e} – skipping")

#     print(f"\n  Exiting {site} …")
#     exit_to_main(page)


# # ── ENTRY POINT ───────────────────────────────────────────────────────────────

# def main():
#     with sync_playwright() as p:
#         browser = p.chromium.launch(
#             headless=False,
#             downloads_path=str(DOWNLOAD_DIR.resolve()),
#             args=["--start-maximized"],
#             slow_mo=100,
#         )
#         ctx = browser.new_context(
#             accept_downloads=True,
#             viewport={"width": 1600, "height": 900},
#         )
#         page = ctx.new_page()
#         page.on("dialog", lambda d: d.accept())

#         print("=" * 62)
#         print("  eraPower Inventory Downloader")
#         print("=" * 62)

#         login(page)

#         for rooftop in ROOFTOPS:
#             try:
#                 run_rooftop(page, rooftop)
#             except Exception as e:
#                 print(f"\n  ✗ Fatal error on {rooftop['store']}: {e}")
#                 try:
#                     page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
#                     wait_net(page)
#                 except Exception:
#                     pass

#         print("\n" + "=" * 62)
#         print(f"  All done!  Files in:  {DOWNLOAD_DIR.resolve()}")
#         print("=" * 62)
#         input("\n  Press ENTER to close browser …")
#         browser.close()


# if __name__ == "__main__":
#     main()

"""
eraPower Inventory CSV Downloader
==================================
Naming convention:  {store_no}_{SiteName}_{MAKE}_{New|Used}.csv

Strategy: For EVERY make + new/used combination we do a FULL fresh navigation:
  Exit → Showroom → Inventory Inquiry → set dropdowns → Find → Download
This avoids any stale state from previous searches.

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
    # {"store": "01", "name": "BooranCheltenham",            "label": "01| Booran Cheltenham"},
    # {"store": "20", "name": "CranbourneHyundai",           "label": "20| Cranbourne Hyundai"},
    # {"store": "40", "name": "SouthMorangHyundai",          "label": "40| South Morang Hyundai"},
    # {"store": "50", "name": "DandenongMitsubishi_Hyundai", "label": "50| Dandenong Mitsubishi & Hyundai"},
    # {"store": "51", "name": "Cranbourne_MG_MITS_KIA",      "label": "51| Cranbourne MG/MITS/KIA"},
    # {"store": "52", "name": "DandenongNI_KI",              "label": "52| Dandenong NI & KI"},
    {"store": "70", "name": "SouthMorangKIA",              "label": "70| South Morang KIA"},
    {"store": "90", "name": "BerwickMG_Hyundai",           "label": "90| Berwick MG & Hyundai"},
]

NEW_USED = ["New", "Used"]

# ── HELPERS ───────────────────────────────────────────────────────────────────

def find_in_frames(page, selector, timeout_sec=8, must_visible=False):
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


def wait_net(page, timeout=6000):
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass
    time.sleep(0.3)


def fire_change(el):
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


def wait_ajax(page, settle=4.0):
    """Wait until no XHR in flight for 1.2s straight, or settle seconds total."""
    # Install monitor once per frame
    for c in [page] + list(page.frames):
        try:
            c.evaluate("""() => {
                if (window.__xhrMon) return;
                window.__xhrMon = true;
                window.__xhrN = 0;
                const os = XMLHttpRequest.prototype.send;
                XMLHttpRequest.prototype.send = function(...a) {
                    window.__xhrN++;
                    this.addEventListener('loadend', () => {
                        window.__xhrN = Math.max(0, window.__xhrN - 1);
                    });
                    return os.apply(this, a);
                };
            }""")
        except Exception:
            pass

    start  = time.time()
    streak = 0
    while time.time() - start < settle:
        total = 0
        for c in [page] + list(page.frames):
            try: total += c.evaluate("() => window.__xhrN ?? 0") or 0
            except: pass
        if total == 0:
            streak += 1
            if streak >= 3:   # 3 × 0.4s = 1.2s quiet
                break
        else:
            streak = 0
        time.sleep(0.4)


def get_row_text(page, table_name):
    for sel in [
        f"span[name='{table_name}'] #SelectedRec",
        f"#{table_name} #SelectedRec",
        "#SelectedRec",
    ]:
        el, _ = find_in_frames(page, sel, timeout_sec=1)
        if el:
            try: return el.inner_text().strip().replace('\xa0', ' ')
            except: pass
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

    user_el.fill(USERNAME); user_el.press("Tab")
    time.sleep(2.5)

    pw, _ = find_in_frames(page, "#password, input[name='password']")
    if pw: pw.fill(PASSWORD); pw.press("Tab"); time.sleep(0.3)

    ws, _ = find_in_frames(page, "#idLoginWorkstation")
    if ws:
        ws.press("Control+A"); ws.press("Backspace")
        ws.fill(WORKSTATION); ws.press("Tab"); time.sleep(0.3)

    btn, _ = find_in_frames(page, "#Button52, input[value='SIGN IN']")
    if btn: btn.click()
    else:   page.keyboard.press("Enter")

    time.sleep(2); wait_net(page, 30000)
    print("  Logged in ✓")


# ── ROOFTOP ───────────────────────────────────────────────────────────────────

def get_active_entity(page):
    el, _ = find_in_frames(page, "#EntityMenu", timeout_sec=2)
    if el:
        try: return el.inner_text().strip()
        except: pass
    return ""


def select_rooftop(page, rooftop):
    store = rooftop["store"]
    current = get_active_entity(page)
    if current and store in current:
        print(f"  ✓ Already active: {current}")
        return

    # Try JS API
    switched = False
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
            if ok: switched = True; break
        except: pass

    if not switched:
        menu, _ = find_in_frames(page, "#EntityMenu, td#EntityMenu, [onclick*='entityMenuClick']", timeout_sec=5)
        if menu: menu.click(); time.sleep(1)
        opt, _ = find_in_frames(page, f"#STORE{store}, div[id='STORE{store}']", timeout_sec=5)
        if opt: opt.click()

    wait_net(page, 6000); time.sleep(0.5)
    current = get_active_entity(page)
    if current: print(f"  ✓ Active: {current}")


# ── NAVIGATION ────────────────────────────────────────────────────────────────

def go_to_inventory_fresh(page):
    """
    Navigate fresh to Inventory Inquiry every time.
    Showroom → Inventory Inquiry.
    """
    for sel in ["span[xmlid='ShowrMenu']", "img[src*='flaticonShowroom']",
                "span.MenuItem:has-text('Showroom')", "text=Showroom"]:
        el, _ = find_in_frames(page, sel, timeout_sec=2)
        if el: el.click(); break
    wait_net(page, 6000); time.sleep(0.5)

    for sel in ["span[xmlid='StockInquiry']", "img[src*='StockInquirySearch']",
                "span.MenuItem:has-text('Inventory Inquiry')", "text=Inventory Inquiry"]:
        el, _ = find_in_frames(page, sel, timeout_sec=2)
        if el: el.click(); break
    wait_net(page, 6000); time.sleep(0.5)


def exit_once(page):
    """Click Exit once (Inventory → Showroom, or Showroom → Main Menu)."""
    btn, _ = find_in_frames(page,
        "span#caption:has-text('Exit'), div[action='Exit'], #But1", timeout_sec=4)
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
    time.sleep(0.5); wait_net(page, 5000)


def exit_to_main(page):
    """Two Exit clicks: Inventory Inquiry → Showroom → Main Menu."""
    exit_once(page)
    exit_once(page)
    time.sleep(0.3)


# ── DROPDOWNS ─────────────────────────────────────────────────────────────────

def set_new_used(page, value):
    el, _ = find_in_frames(page, "#selNewUsed, select[name='selNewUsed']", timeout_sec=8)
    if not el: return False
    try:    el.select_option(value=value)
    except: el.select_option(label=value)
    fire_change(el)
    # PostNewUsed repopulates make dropdown — wait for it
    wait_ajax(page, settle=4.0)
    return True


def get_makes(page):
    el, _ = find_in_frames(page, "#selMakeInventory, select[name='selMakeInventory']", timeout_sec=6)
    if not el: return []
    try:
        return el.evaluate("""sel => Array.from(sel.options)
            .filter(o => o.value.trim() !== '')
            .map(o => {
                const text  = o.text.trim();
                const parts = text.split('-');
                const code  = parts.length > 1
                    ? parts.slice(1).join('-').trim().replace(/[^A-Za-z0-9]/g, '')
                    : o.value;
                return { val: o.value.trim(), code: code || o.value.trim() };
            })""")
    except: return []


def set_make(page, make_val, make_code):
    el, _ = find_in_frames(page, "#selMakeInventory, select[name='selMakeInventory']", timeout_sec=6)
    if not el: return False

    try:    el.select_option(value=make_val)
    except:
        try: el.select_option(label=make_code)
        except Exception as e:
            print(f"    ⚠ select failed: {e}"); return False

    # Check it stuck
    actual = el.evaluate("s => s.value")
    if actual != make_val:
        print(f"    ⚠ value is {actual!r} not {make_val!r}")

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
    wait_ajax(page, settle=4.0)
    return True


def set_location_all(page):
    el, _ = find_in_frames(page, "#selLocation, select[name='selLocation']", timeout_sec=4)
    if not el: return
    try:    el.select_option(value="All")
    except:
        try: el.select_option(label="All")
        except: return
    fire_change(el)
    time.sleep(0.4)


# ── FIND + WAIT ───────────────────────────────────────────────────────────────

def click_find(page, table_name):
    """Click Find and wait up to 12s for the results table to refresh."""
    text_before = get_row_text(page, table_name)

    # Plant MutationObserver sentinel
    for c in [page] + list(page.frames):
        try:
            c.evaluate(f"""() => {{
                window.__tableRefreshed = false;
                const node =
                    document.querySelector("span[name='{table_name}']") ||
                    document.getElementById('{table_name}');
                if (!node) return;
                new MutationObserver((_, obs) => {{
                    window.__tableRefreshed = true;
                    obs.disconnect();
                }}).observe(node, {{ childList: true, subtree: true, characterData: true }});
            }}""")
        except: pass

    # Click Find
    find_btn, _ = find_in_frames(page, "#But0, div[action='Find']", timeout_sec=5)
    if not find_btn:
        print("[no Find btn]", end=" "); return ""

    try:    find_btn.click(timeout=3000)
    except:
        try: find_btn.evaluate("b => b.click()")
        except: print("[Find click failed]", end=" "); return ""

    # Poll until sentinel fires or row text changes (max 12s)
    deadline = time.time() + 12.0
    refreshed = False
    while time.time() < deadline:
        time.sleep(0.35)
        for c in [page] + list(page.frames):
            try:
                if c.evaluate("() => window.__tableRefreshed ?? false"):
                    refreshed = True; break
            except: pass
        if refreshed: break
        now = get_row_text(page, table_name)
        if now and now != text_before:
            refreshed = True; break

    text_after = get_row_text(page, table_name)
    flag = "✓" if refreshed else "⚠timeout"
    print(f"[{text_before} → {text_after} {flag}]", end=" ", flush=True)
    time.sleep(0.5)
    return text_after


# ── DOWNLOAD ──────────────────────────────────────────────────────────────────

def download_csv(page, store, site, make_code, nu_code, rec_text):
    filename   = f"{store}_{site}_{make_code}_{nu_code}.csv"
    dest       = DOWNLOAD_DIR / filename
    total      = parse_count(rec_text)
    table_name = "dtbNewResults" if nu_code == "New" else "dtbUsedResults"

    if total == 0:
        dest.write_text(
            "stock#,carline,description,fa,colour,loc,list price,age,deal,status,open ro/po\n",
            encoding="utf-8")
        print(f"→ {filename} (0 records)")
        return True

    exp_btn = None
    for sel in [
        f"span[name='{table_name}'] img#Exp",
        f"#{table_name} img#Exp",
        f"span[name='{table_name}'] img[name='Exp']",
        f"span[name='{table_name}'] .TableExportUpButton",
        f"#{table_name} .TableExportUpButton",
    ]:
        exp_btn, _ = find_in_frames(page, sel, timeout_sec=3)
        if exp_btn: break

    if not exp_btn:
        print(f"✗ export btn not found ({filename})"); return False

    try:
        with page.expect_download(timeout=20000) as dl_info:
            try:    exp_btn.click(force=True)
            except: exp_btn.evaluate("e => e.click()")
        dl_info.value.save_as(str(dest.resolve()))
        print(f"→ {filename}")
        time.sleep(0.4)
        return True
    except Exception as e:
        print(f"✗ {e}"); return False


# ── CORE LOOP — fresh navigation per make×condition ───────────────────────────

def run_rooftop(page, rooftop):
    store = rooftop["store"]
    site  = rooftop["name"]

    print(f"\n{'='*62}")
    print(f"  ROOFTOP  {store} | {site}")
    print(f"{'='*62}")

    select_rooftop(page, rooftop)

    # First pass: navigate in once to read what makes are available per condition
    make_map = {}   # { "New": [...], "Used": [...] }
    for nu in NEW_USED:
        print(f"\n  Reading makes for {nu} …")
        go_to_inventory_fresh(page)

        if not set_new_used(page, nu):
            print(f"  ✗ Could not set {nu}"); make_map[nu] = []; continue

        makes = get_makes(page)
        make_map[nu] = makes
        print(f"  Makes ({nu}): {[m['code'] for m in makes]}")

        # Exit back to main menu (2 clicks)
        exit_to_main(page)

    # Second pass: for each condition × make, do a FULL fresh navigation
    for nu in NEW_USED:
        table_name = "dtbNewResults" if nu == "New" else "dtbUsedResults"
        makes = make_map.get(nu, [])
        if not makes:
            print(f"\n  No makes for {nu} — skipping"); continue

        for make in makes:
            make_val  = make["val"]
            make_code = make["code"]
            filename  = f"{store}_{site}_{make_code}_{nu}.csv"

            # Skip if already downloaded
            if (DOWNLOAD_DIR / filename).exists():
                print(f"  ✓ Already exists — skip: {filename}")
                continue

            print(f"\n  → {nu} / {make_code} … ", end="", flush=True)

            try:
                # Fresh navigation every single time
                go_to_inventory_fresh(page)

                # Set New/Used
                if not set_new_used(page, nu):
                    print("✗ new/used not set"); exit_to_main(page); continue

                # Set Make
                if not set_make(page, make_val, make_code):
                    print("✗ make not set"); exit_to_main(page); continue

                # Set Location = All
                set_location_all(page)

                # Find + wait for refresh
                rec_text = click_find(page, table_name)

                # Download
                download_csv(page, store, site, make_code, nu, rec_text)

                # Exit back to main (2 clicks)
                exit_to_main(page)

            except PWTimeout:
                print("✗ Timeout")
                try: exit_to_main(page)
                except: pass
            except Exception as e:
                print(f"✗ {e}")
                try: exit_to_main(page)
                except: pass


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

        # Auto-dismiss eraPower alert popups (e.g. LEPAS "no stock number" dialog)
        page.on("dialog", lambda d: (
            print(f"\n  [dialog: {d.message!r}] → dismissed"),
            d.accept()
        ))

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