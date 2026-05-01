from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.jakmall.com/go-market/taffstudio-gantungan-gitar-dinding-guitar-holder-bracket-wall-mount-xg-05")
    page.wait_for_timeout(5000)
    
    # Extract Title
    title = page.locator('h1').first.inner_text() if page.locator('h1').count() > 0 else "NO_TITLE"
    print(f"Title: {title}")
    
    # Extract Price
    price = page.locator('.pd__price, .price').first.inner_text() if page.locator('.pd__price, .price').count() > 0 else "NO_PRICE"
    print(f"Price: {price}")
    
    with open("jakmall_product.html", "w") as f:
         f.write(page.content())
    browser.close()
