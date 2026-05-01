from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('https://www.jakmall.com/search?q=gitar', timeout=60000)
    page.wait_for_selector('.pi__core', timeout=10000)
    card = page.locator('.pi__core').first
    print(card.inner_html())
    browser.close()
