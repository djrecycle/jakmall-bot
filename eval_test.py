from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.jakmall.com/go-market/taffstudio-gantungan-gitar-dinding-guitar-holder-bracket-wall-mount-xg-05")
    page.wait_for_timeout(5000)
    
    # Try to evaluate window.spdt
    try:
        spdt = page.evaluate("() => window.spdt")
        if spdt:
            print("Successfully extracted spdt JSON:")
            print(f"SKU keys: {list(spdt.get('sku', {}).keys())}")
            # get the first sku data
            first_sku_key = list(spdt['sku'].keys())[0]
            sku_data = spdt['sku'][first_sku_key]
            print(f"Price: {sku_data.get('price', {}).get('final')}")
            print(f"Store Name: {spdt.get('store', {}).get('name')}")
        else:
            print("window.spdt is null/undefined")
    except Exception as e:
        print(f"Error evaluating spdt: {e}")
        
    browser.close()
