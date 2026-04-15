from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('http://localhost:3001', timeout=60000)
    page.wait_for_selector('h1')
    page.screenshot(path='test_theme_screenshot.png')
    browser.close()
