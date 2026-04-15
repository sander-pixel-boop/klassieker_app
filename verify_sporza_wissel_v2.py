from playwright.sync_api import sync_playwright

def run_cuj(page):
    page.goto("http://localhost:8501")
    page.wait_for_timeout(3000)

    try:
        page.get_by_role("button", name="🚪 Doorgaan als gast (zonder cloud-opslag)").click(timeout=3000)
        page.wait_for_timeout(2000)
    except Exception:
        pass

    try:
        page.goto("http://localhost:8501/sporza_klassiekers")
        page.wait_for_timeout(3000)
    except Exception:
        pass

    try:
        page.get_by_role("button", name="🚀 BEREKEN SPORZA TEAM").click(timeout=5000)
        page.wait_for_timeout(10000)
    except Exception as e:
        print("bereken button fail", e)

    try:
        page.get_by_text("✏️ Handmatige Wissel Toevoegen").click(timeout=2000)
        page.wait_for_timeout(2000)
    except Exception as e:
        print("expander fail", e)

    page.screenshot(path="verification2.png")
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="videos2",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
