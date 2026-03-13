import time
import re
import os

from seleniumbase import SB

SERVER_ID   = "daa4eb9e-8398-47f1-a8a5-9b6654e2d3ef"
RENEW_URL   = f"https://host2play.gratis/server/renew?i={SERVER_ID}"
LOCAL_PROXY = "http://127.0.0.1:8080"

os.makedirs("screenshots", exist_ok=True)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def full_screenshot(sb, name):
    try:
        sb.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.3)
        sb.save_screenshot(name, folder=".")
        log(f"screenshot: {name}")
    except Exception as e:
        log(f"screenshot failed {name}: {e}")


def find_ext_path():
    """Find the dir containing manifest.json under ./nopecha_ext"""
    base = os.path.abspath("./nopecha_ext")
    # manifest directly inside?
    if os.path.exists(os.path.join(base, "manifest.json")):
        return base
    # one level deeper
    for entry in os.listdir(base):
        sub = os.path.join(base, entry)
        if os.path.isdir(sub) and os.path.exists(os.path.join(sub, "manifest.json")):
            log(f"manifest.json found in subdir: {sub}")
            return sub
    raise FileNotFoundError(f"manifest.json not found under {base}")


def get_expire_time(sb) -> str:
    try:
        return sb.execute_script(
            "return document.getElementById('expireDate')?.innerText || ''"
        ) or ""
    except Exception:
        return ""


def is_renewed(expire_text: str) -> bool:
    m = re.match(r'(\d+):(\d+):\d+', expire_text.strip())
    if not m:
        return False
    h, mn = int(m.group(1)), int(m.group(2))
    return h > 7 or (h == 7 and mn >= 59)


def wait_for_token(sb, timeout=300) -> str:
    log("waiting for NopeCHA to solve reCAPTCHA...")
    for i in range(timeout * 2):
        token = sb.execute_script(
            "return document.querySelector('textarea[name=\"g-recaptcha-response\"]')?.value || ''"
        )
        if token and len(token) > 20:
            log(f"token received (len={len(token)})")
            return token
        if i > 0 and i % 60 == 0:
            full_screenshot(sb, f"nopecha_waiting_{i//60}min.png")
        time.sleep(0.5)
    raise TimeoutError("reCAPTCHA token timeout after 5 min")


def remove_ads(sb):
    log("removing ads...")
    sb.execute_script("""
        [
            'ins.adsbygoogle','#google-anno-sa','#ad-msg',
            'iframe[id^="aswift"]','iframe[src*="doubleclick"]',
            'iframe[src*="googlesyndication"]','ins[data-vignette-loaded]',
        ].forEach(sel => document.querySelectorAll(sel).forEach(el => el.remove()));
    """)
    time.sleep(1)


def run_script():
    log("starting browser...")

    ext_path = find_ext_path()
    log(f"loading extension from: {ext_path}")

    with SB(
        uc=True,
        test=True,
        proxy=LOCAL_PROXY,
        extension_dir=ext_path,
    ) as sb:
        log("browser ready")

        # IP check
        try:
            sb.open("https://api.ipify.org/?format=json")
            ip_text = re.sub(r'(\d+\.\d+\.\d+\.)\d+', r'\1xx', sb.get_text('body'))
            log(f"exit IP: {ip_text}")
        except Exception:
            log("IP check skipped")

        # Check extensions page
        log("checking extensions page...")
        sb.open("chrome://extensions/")
        time.sleep(3)
        full_screenshot(sb, "00_extensions.png")

        # Activate NopeCHA — visiting this page lets it initialize
        # For automation build, no key needed; free tier uses IP-based quota
        log("activating NopeCHA...")
        sb.open("https://nopecha.com/setup#")
        time.sleep(4)
        full_screenshot(sb, "00_nopecha_setup.png")

        # Open the renew page
        log("opening renew page...")
        sb.uc_open_with_reconnect(RENEW_URL, reconnect_time=4)
        time.sleep(3)
        full_screenshot(sb, "00_page_loaded.png")

        remove_ads(sb)
        full_screenshot(sb, "01_ads_removed.png")

        # Click the Renew button
        log("clicking Renew server button...")
        try:
            sb.wait_for_element_visible('button[onclick*="renew"]', timeout=15)
        except Exception:
            log("Renew button not found — aborting")
            full_screenshot(sb, "02_no_renew_btn.png")
            exit(1)

        sb.execute_script(
            'document.querySelector(\'button[onclick*="renew"]\').scrollIntoView({behavior:"smooth",block:"center"});'
        )
        time.sleep(1)
        full_screenshot(sb, "02_before_click.png")
        sb.click('button[onclick*="renew"]')
        time.sleep(2)
        full_screenshot(sb, "03_after_click.png")

        # Wait for NopeCHA to fill the hidden reCAPTCHA textarea
        try:
            wait_for_token(sb, timeout=300)
        except TimeoutError as e:
            log(str(e))
            full_screenshot(sb, "04_token_timeout.png")
            exit(1)

        full_screenshot(sb, "04_token_received.png")
        time.sleep(2)

        # Click the swal2 Renew confirm button
        log("clicking swal2 Renew confirm...")
        try:
            sb.wait_for_element_visible('.swal2-confirm', timeout=15)
        except Exception:
            log("swal2 confirm button not found")
            full_screenshot(sb, "05_no_swal2.png")
            exit(1)

        full_screenshot(sb, "05_before_swal2.png")
        sb.click('.swal2-confirm')
        time.sleep(2)

        log("waiting for page refresh...")
        time.sleep(5)
        full_screenshot(sb, "06_after_refresh.png")

        expire = get_expire_time(sb)
        log(f"expireDate: {expire}")
        if is_renewed(expire):
            log("✅ renew success!")
            full_screenshot(sb, "99_success.png")
        else:
            log(f"❌ renew failed, expireDate={expire}")
            full_screenshot(sb, "99_failed.png")
            exit(1)


if __name__ == "__main__":
    run_script()
