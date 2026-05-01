from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.jakmall.com/search?q=senar+gitar")
    page.wait_for_timeout(5000)
    
    # Try to find product links
    links = page.locator('a[href]').all()
    print(f"Total links: {len(links)}")
    
    # Look for common product wrappers
    product_wrappers = page.locator('div.product-card, div.product, a.product-card').all()
    print(f"Product wrappers found: {len(product_wrappers)}")
    
    # Just print the first 5 hrefs that look like products
    product_links = []
    for link in links:
        try:
            href = link.get_attribute('href')
            if href and 'jakmall.com' in href and not 'search' in href:
                 product_links.append(href)
        except:
            pass
            
    print("Sample Links:")
    for l in product_links[:10]:
         print(l)
         
    # Save the whole page content to investigate if needed
    with open("jakmall_search.html", "w") as f:
         f.write(page.content())
    
    browser.close()
