import time, re, os
from seleniumbase import SB

SERVER_ID  = "daa4eb9e-8398-47f1-a8a5-9b6654e2d3ef"
RENEW_URL  = f"https://host2play.gratis/server/renew?i={SERVER_ID}"
LOCAL_PROXY = "http://127.0.0.1:8080"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def shot(sb, name):
    sb.execute_script("window.scrollTo(0,0)")
    time.sleep(0.2)
    sb.save_screenshot(name, folder=".")
    log(f"screenshot: {name}")

def find_ext_path():
    base = os.path.abspath("./nopecha_ext")
    if os.path.exists(os.path.join(base, "manifest.json")):
        return base
    for e in os.listdir(base):
        sub = os.path.join(base, e)
        if os.path.isdir(sub) and os.path.exists(os.path.join(sub, "manifest.json")):
            return sub
    raise FileNotFoundError(f"manifest.json not found under {base}")

def get_expire(sb):
    try:
        return sb.execute_script("return document.getElementById('expireDate')?.innerText||''") or ""
    except:
        return ""

def is_renewed(t):
    m = re.match(r'(\d+):(\d+):\d+', t.strip())
    if not m: return False
    h, mn = int(m.group(1)), int(m.group(2))
    return h > 7 or (h == 7 and mn >= 59)

def wait_token(sb, timeout=120):          # ← 改成120s，扩展OK后应该很快
    log("waiting for NopeCHA token...")
    for i in range(timeout * 2):
        tok = sb.execute_script(
            "return document.querySelector('textarea[name=\"g-recaptcha-response\"]')?.value||''"
        )
        if tok and len(tok) > 20:
            log(f"token OK (len={len(tok)})")
            return tok
        if i > 0 and i % 60 == 0:
            shot(sb, f"waiting_{i//60}min.png")
        time.sleep(0.5)
    raise TimeoutError(f"token not received in {timeout}s")

def remove_ads(sb):
    sb.execute_script("""
        ['ins.adsbygoogle','#google-anno-sa','#ad-msg',
         'iframe[id^="aswift"]','iframe[src*="doubleclick"]',
         'iframe[src*="googlesyndication"]','ins[data-vignette-loaded]'
        ].forEach(s=>document.querySelectorAll(s).forEach(e=>e.remove()));
    """)
    time.sleep(0.5)

def run():
    log("starting...")
    ext_path = find_ext_path()
    log(f"extension: {ext_path}")

    with SB(uc=True, test=True, proxy=LOCAL_PROXY, extension_dir=ext_path) as sb:

        # 激活扩展
        sb.open("https://nopecha.com/setup#")
        time.sleep(3)

        # 打开续期页
        log("opening renew page...")
        sb.uc_open_with_reconnect(RENEW_URL, reconnect_time=4)
        time.sleep(2)
        remove_ads(sb)
        shot(sb, "01_page.png")

        # 点击 Renew server
        log("clicking Renew server...")
        sb.wait_for_element_visible('button[onclick*="renew"]', timeout=10)
        sb.execute_script(
            'document.querySelector(\'button[onclick*="renew"]\').scrollIntoView({block:"center"})'
        )
        time.sleep(0.5)
        shot(sb, "02_before_click.png")
        sb.click('button[onclick*="renew"]')
        time.sleep(2)
        shot(sb, "03_after_click.png")

        # 等token
        try:
            wait_token(sb, timeout=120)
        except TimeoutError as e:
            log(str(e))
            shot(sb, "04_timeout.png")
            exit(1)
        shot(sb, "04_token_ok.png")
        time.sleep(1)

        # 点swal2确认
        log("clicking swal2 confirm...")
        sb.wait_for_element_visible('.swal2-confirm', timeout=10)
        shot(sb, "05_swal2.png")
        sb.click('.swal2-confirm')
        time.sleep(5)
        shot(sb, "06_result.png")

        expire = get_expire(sb)
        log(f"expireDate: {expire}")
        if is_renewed(expire):
            log("✅ success!")
        else:
            log(f"❌ failed, expire={expire}")
            exit(1)

if __name__ == "__main__":
    run()
