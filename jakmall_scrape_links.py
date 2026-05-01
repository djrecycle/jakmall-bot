from playwright.sync_api import sync_playwright
import requests
import subprocess
import os
import time
import re
import json
import urllib.parse
import pandas as pd

DEFAULT_KEYWORDS = [
    "Senar Gitar"
]

SORT_OPTIONS = {
    "1": {"label": "Terpopuler",       "params": ""}, # default jakmall
    "2": {"label": "Terbaru",          "params": "sort=new"},
    "3": {"label": "Harga Terendah",   "params": "sort=cheap"},
    "4": {"label": "Harga Tertinggi",  "params": "sort=expensive"},
    "5": {"label": "Diskon Terbesar",  "params": "sort=discount"},
}

def pilih_mode():
    print("\n🔍 Pilih Mode Scraping Jakmall:")
    print("─" * 30)
    print("  [1] Berdasarkan Kata Kunci (Keyword)")
    print("  [2] Berdasarkan Toko Spesifik (Username/URL)")
    print("─" * 30)
    while True:
        pilihan = input("Masukkan nomor mode (default: 1): ").strip()
        if pilihan == "" or pilihan == "1":
            return "keyword"
        elif pilihan == "2":
            return "toko"
        else:
            print("❌ Pilihan tidak valid, coba lagi.")

def input_target(mode):
    if mode == "keyword":
        print("\n🔑 Masukkan Keyword (pisahkan dengan koma jika lebih dari satu):")
        raw = input("Keyword: ").strip()
        if not raw:
            return DEFAULT_KEYWORDS
        return [k.strip() for k in raw.split(",") if k.strip()]
    else:
        print("\n🏪 Masukkan Username Toko (pisahkan dengan koma):")
        print("Contoh: indo-audio ATAU https://www.jakmall.com/indo-audio")
        raw = input("Toko: ").strip()
        while not raw:
             print("❌ Harus diisi untuk mode toko!")
             raw = input("Toko: ").strip()
        
        targets = [t.strip() for t in raw.split(",") if t.strip()]
        cleaned_targets = []
        for t in targets:
             if "jakmall.com/" in t:
                 username = t.split("jakmall.com/")[-1].split("?")[0].strip("/")
             else:
                 username = t.strip("/")
             cleaned_targets.append(username)
        return cleaned_targets

def input_max_page():
    print("\n📄 Mengambil berapa halaman? (default: 1)")
    raw = input("Max Page: ").strip()
    if not raw:
        return 1
    try:
        val = int(raw)
        return val if val > 0 else 1
    except:
         return 1

def pilih_urutan():
    print("\n📊 Pilih Urutan Pencarian:")
    print("─" * 30)
    for key, opt in SORT_OPTIONS.items():
        print(f"  [{key}] {opt['label']}")
    print("─" * 30)

    while True:
        pilihan = input("Masukkan nomor (default: 1 - Terpopuler): ").strip()
        if pilihan == "":
            pilihan = "1"
        if pilihan in SORT_OPTIONS:
            selected = SORT_OPTIONS[pilihan]
            print(f"✅ Urutan dipilih: {selected['label']}")
            return selected["params"]
        else:
            print("❌ Pilihan tidak valid, coba lagi.")

def pilih_kategori(page, preview_url):
    jakmall_categories = [
        "Smartphone & Tablet", "Aksesoris Handphone", "Smartwatch & Aksesoris",
        "Komputer & Laptop", "Aksesoris Komputer", "Elektronik",
        "Audio", "TV & Media Player", "Kamera & Fotografi",
        "Otomotif", "Olahraga & Outdoor", "Peralatan Rumah Tangga",
        "Perlengkapan Dapur", "Alat Pertukangan", "Ibu, Bayi & Anak",
        "Kesehatan & Kecantikan", "Mainan & Hobi", "Fashion & Perhiasan",
        "Buku & Alat Tulis", "Lain-lain"
    ]

    dynamic_categories = []
    if page and preview_url:
        print("\n🔍 Membuka halaman pencarian untuk mengambil data kategori...")
        try:
            page.goto(preview_url, timeout=30000)
            page.wait_for_timeout(3000)
            # Scroll sedikit agar kategori muncul
            page.mouse.wheel(0, 500)
            page.wait_for_timeout(1000)

            cat_items = page.locator('.pc__categories__item').all()
            seen = set()
            for item in cat_items:
                try:
                    name_el = item.locator('.ellipsis')
                    count_el = item.locator('.pc__categories__count')
                    link_el = item.locator('a')
                    if name_el.count() > 0 and count_el.count() > 0:
                        name = name_el.first.inner_text().strip()
                        count = count_el.first.inner_text().strip().strip('()')
                        href = link_el.first.get_attribute("href") if link_el.count() > 0 else ""
                        if name and name not in seen:
                            seen.add(name)
                            dynamic_categories.append((name, count, href))
                except:
                    continue
        except Exception as e:
            print(f"⚠️ Gagal mengambil kategori dari browser: {e}")

    if dynamic_categories:
        print("\n📂 Pilih Kategori (Berdasarkan Hasil Pencarian):")
        print("─" * 40)
        for i, (cat, count, href) in enumerate(dynamic_categories, 1):
            print(f"  [{i}] {cat} ({count} produk)")
        print(f"  [{len(dynamic_categories) + 1}] ➕ Tulis Kategori Kustom Manual")
        print("─" * 40)
        
        while True:
            pilihan = input("Masukkan nomor pilihan: ").strip()
            try:
                idx = int(pilihan) - 1
                if 0 <= idx < len(dynamic_categories):
                    selected = dynamic_categories[idx][0]
                    href = dynamic_categories[idx][2]
                    cat_slug = ""
                    if href and "category=" in href:
                        try:
                            parsed = urllib.parse.urlparse(href)
                            query_params = urllib.parse.parse_qs(parsed.query)
                            if "category" in query_params:
                                cat_slug = query_params["category"][0]
                        except:
                            pass
                    print(f"✅ Kategori dipilih: {selected}")
                    return selected, cat_slug
                elif idx == len(dynamic_categories):
                    new_cat = input("Masukkan nama kategori khusus: ").strip()
                    if new_cat:
                        clean_cat = re.sub(r'[\\/*?:"<>|]', "", new_cat).strip()
                        if clean_cat:
                            print(f"✅ Kategori dipilih: {clean_cat}")
                            return clean_cat, ""
                        else:
                            print("❌ Nama tidak valid.")
                    else:
                        print("❌ Nama kategori tidak boleh kosong.")
                else:
                    print("❌ Nomor tidak valid.")
            except ValueError:
                print("❌ Input harus berupa angka.")
    else:
        print("\n📂 Pilih Kategori Resmi Jakmall untuk Data Ini:")
        print("─" * 30)
        for i, cat in enumerate(jakmall_categories, 1):
            print(f"  [{i}] {cat}")
        print(f"  [{len(jakmall_categories) + 1}] ➕ Tulis Kategori Kustom Manual")
        print("─" * 30)

        while True:
            pilihan = input("Masukkan nomor pilihan: ").strip()
            try:
                idx = int(pilihan) - 1
                if 0 <= idx < len(jakmall_categories):
                    selected = jakmall_categories[idx]
                    print(f"✅ Kategori dipilih: {selected}")
                    return selected, ""
                elif idx == len(jakmall_categories):
                    new_cat = input("Masukkan nama kategori khusus: ").strip()
                    if new_cat:
                        clean_cat = re.sub(r'[\\/*?:"<>|]', "", new_cat).strip()
                        if clean_cat:
                            print(f"✅ Kategori dipilih: {clean_cat}")
                            return clean_cat, ""
                        else:
                            print("❌ Nama tidak valid.")
                    else:
                        print("❌ Nama kategori tidak boleh kosong.")
                else:
                    print("❌ Nomor tidak valid.")
            except ValueError:
                print("❌ Input harus berupa angka.")

def pilih_status_stok():
    ans = input("\n📦 Hanya Stok Tersedia? (y/n, default: y): ").strip().lower()
    return "in-stock=1" if ans != "n" else ""

def pilih_filter_berdasarkan():
    print("\n🏷️ Filter Berdasarkan:")
    print("  [1] Tanpa Filter")
    print("  [2] Untung Paling Besar")
    print("  [3] Harga Grosir")
    print("  [4] Keduanya")
    ans = input("Masukkan nomor pilihan (default: 1): ").strip()
    filters = []
    if ans == "2" or ans == "4":
        filters.append("untung-paling-besar=1")
    if ans == "3" or ans == "4":
        filters.append("bulk-price=1")
    return "&".join(filters)

def pilih_kota():
    cities = [
        "DKI Jakarta", "Tangerang", "Bekasi", "Bogor", 
        "Depok", "Bandung", "Semarang", "Surabaya", 
        "Surakarta", "Malang", "Medan", "Batam", 
        "Garut", "Denpasar", "Pekalongan", "Gresik"
    ]
    print("\n🏙️ Filter Kota Asal Toko (Lokasi Seller)")
    print("─" * 30)
    print("  [0] Tanpa Filter Kota (Default)")
    for i, city in enumerate(cities, 1):
        print(f"  [{i}] {city}")
    print("─" * 30)
    
    while True:
        ans = input("Masukkan nomor pilihan kota (0-16): ").strip()
        if ans == "" or ans == "0":
            return ""
        try:
            idx = int(ans) - 1
            if 0 <= idx < len(cities):
                selected = cities[idx]
                print(f"✅ Kota dipilih: {selected}")
                return f"cities[]={urllib.parse.quote(selected)}"
            else:
                print("❌ Pilihan tidak valid.")
        except ValueError:
            print("❌ Input harus berupa angka.")

def pilih_rating_filter():
    print("\n⭐ Filter Rating Produk:")
    print("  [1] Ambil Semua Produk (Default)")
    print("  [2] Hanya Ambil Produk yang Memiliki Rating (> 0)")
    ans = input("Masukkan nomor pilihan (default: 1): ").strip()
    return "hanya_bintang" if ans == "2" else "semua"

def start_chrome():
    print("🔍 Cek Chrome debugging...")
    try:
        requests.get("http://localhost:9222/json/version", timeout=2)
        print("✅ Chrome sudah berjalan")
    except:
        print("🚀 Membuka Chrome baru...")
        chrome_profile = os.path.abspath("jakmall_debug_profile")
        subprocess.Popen([
            "google-chrome",
            "--remote-debugging-port=9222",
            f"--user-data-dir={chrome_profile}",
            "--no-first-run"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)

def scrape_links():
    print("🔥 Mulai scraping Jakmall...")
    mode = pilih_mode()
    targets = input_target(mode)
    max_page = input_max_page()
    sort_params = pilih_urutan()
    filter_stok = pilih_status_stok()
    filter_berdasarkan = pilih_filter_berdasarkan()
    filter_kota = pilih_kota()
    filter_rating = pilih_rating_filter()

    # Bangun preview URL dari target pertama + filter
    first_target = targets[0] if targets else ""
    preview_url = ""
    if first_target:
        extra_params = [p for p in [sort_params, filter_stok, filter_berdasarkan, filter_kota] if p]
        params_str = "&".join(extra_params)
        if mode == "keyword":
            base_url = f"https://www.jakmall.com/search?q={urllib.parse.quote(first_target)}"
            preview_url = f"{base_url}&{params_str}" if params_str else base_url
        else:
            base_url = f"https://www.jakmall.com/{first_target}"
            preview_url = f"{base_url}?{params_str}" if params_str else base_url

    # Start Chrome lebih awal supaya bisa dipakai untuk ambil kategori
    start_chrome()

    with sync_playwright() as p:
        print("🔗 Connect ke Chrome...")
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            print("✅ Berhasil connect")
        except Exception as e:
            print("❌ Gagal connect:", e)
            return

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()

        # Ambil kategori secara dinamis menggunakan browser
        kategori_pilihan, kategori_slug = pilih_kategori(page, preview_url)

        all_links = []

        for target_index, target in enumerate(targets):
            print(f"\n{'='*50}")
            
            extra_params = [p for p in [sort_params, filter_stok, filter_berdasarkan, filter_kota] if p]
            if kategori_slug:
                extra_params.append(f"category={kategori_slug}")
            params_str = "&".join(extra_params)
            
            if mode == "keyword":
                print(f"🔑 Target [{target_index+1}/{len(targets)}] (Keyword): {target}")
                base_url = f"https://www.jakmall.com/search?q={urllib.parse.quote(target)}"
                url = f"{base_url}&{params_str}" if params_str else base_url
            else:
                print(f"🏪 Target [{target_index+1}/{len(targets)}] (Toko): {target}")
                base_url = f"https://www.jakmall.com/{target}"
                url = f"{base_url}?{params_str}" if params_str else base_url
            print(f"{'='*50}")

            print(f"🌐 Buka URL: {url}...")
            page.goto(url, timeout=60000)
            page.wait_for_timeout(5000)

            product_found = False
            for sel in ['.pi__core', '.pi']:
                try:
                    page.wait_for_selector(sel, timeout=10000)
                    count = page.locator(sel).count()
                    if count > 0:
                        print(f"✅ Produk ditemukan ({count} elemen)")
                        product_found = True
                        break
                except:
                    continue

            if not product_found:
                print(f"❌ Produk tidak ditemukan untuk target '{target}'!")
                continue

            keyword_links = []

            for page_num in range(max_page):
                print(f"\n📄 Halaman {page_num+1}")

                # Scroll supaya load gambar/lazy load
                for i in range(8):
                    page.mouse.wheel(0, 2000)
                    page.wait_for_timeout(1000)

                page.mouse.wheel(0, -1000)
                page.wait_for_timeout(1000)

                product_cards = page.locator('.pi__core').all()
                page_links = []
                
                for card in product_cards:
                    try:
                        # Cari tag <a> untuk produk
                        link_el = card.locator('a.pi__name').first
                        if not link_el.is_visible():
                            # Fallback
                            link_el = card.locator('a').first
                        
                        href = link_el.get_attribute("href")
                        if href:
                            full_link = href.split("?")[0] # hapus tracking
                            
                            # Coba ambil rating dari card produk berdasarkan jumlah star
                            rating_val = 0.0
                            try:
                                # Cari wrapper bintang
                                stars_wrapper = card.locator('.rating__stars').first
                                if stars_wrapper.count() > 0 and stars_wrapper.is_visible():
                                    # Hitung bintang penuh
                                    full_stars = stars_wrapper.locator('i:has-text("star")').count()
                                    # Hitung setengah bintang (pastikan text-nya persis "star_half")
                                    # Karena :has-text("star") juga match "star_half", kita bisa cek inner_text semua <i>
                                    i_elements = stars_wrapper.locator('i').all()
                                    for i_el in i_elements:
                                        try:
                                            icon_txt = i_el.inner_text().strip()
                                            if icon_txt == "star":
                                                rating_val += 1.0
                                            elif icon_txt == "star_half":
                                                rating_val += 0.5
                                        except:
                                            pass
                            except:
                                pass
                                
                            page_links.append({"link": full_link, "rating": f"⭐ {rating_val}"})
                    except Exception as e:
                        continue

                print(f"🔎 Link produk di halaman ini: {len(page_links)}")
                keyword_links.extend(page_links)

                if page_num < max_page - 1:
                    try:
                        # Pagination on Jakmall
                        # Look for next page button
                        next_btn = page.locator('a[aria-label="Berikutnya"], a[rel="next"], .pagination__next a').first
                        if next_btn.is_visible():
                            print("➡️ Pindah ke halaman berikutnya...")
                            next_btn.click()
                            page.wait_for_timeout(5000)
                        else:
                            print("⛔ Tidak ada tombol next, ini halaman terakhir.")
                            break
                    except Exception as e:
                        print("❌ Gagal klik next:", e)
                        break

            seen = set()
            for item in keyword_links:
                if item["link"] not in seen:
                    # Filter rating jika user memilih hanya yang berbintang
                    if filter_rating == "hanya_bintang":
                        try:
                            # Parse angka dari format "⭐ 4.5"
                            val = float(item["rating"].replace("⭐", "").strip())
                            if val == 0.0:
                                continue # Skip produk ini
                        except:
                            continue # Skip jika error parsing

                    seen.add(item["link"])
                    keyword_label = target if mode == "keyword" else f"Toko: {target}"
                    all_links.append({
                        "Kategori": kategori_pilihan,
                        "Keyword": keyword_label,
                        "Lokasi": "", # Not implemented for Jakmall yet
                        "Link Produk": item["link"],
                        "Rating": item["rating"],
                        "Status Chat": "",
                        "Status": ""
                    })

            print(f"\n✅ Target '{target}' selesai: {len(seen)} link unik.")

        print(f"\n{'='*50}")
        print("💾 Menyimpan ke CSV...")

        df = pd.DataFrame(all_links)
        csv_file = "jakmall_links.csv"
        if os.path.exists(csv_file):
            try:
                old_df = pd.read_csv(csv_file)
                df = pd.concat([old_df, df], ignore_index=True)
            except Exception as e:
                print(f"⚠️ Gagal membaca CSV yang sudah ada: {e}")

        if not df.empty:
            df = df.drop_duplicates(subset="Link Produk", keep="last")
            desired_columns = ["Kategori", "Keyword", "Lokasi", "Link Produk", "Rating", "Status Chat", "Status"]
            for col in df.columns:
                if col not in desired_columns:
                    desired_columns.append(col)
            df = df.reindex(columns=desired_columns)
            df.to_csv(csv_file, index=False)
            print(f"✅ SELESAI! Total link unik di database: {len(df)}")
            print(f"📁 File: {csv_file}")
            
            print("\n📊 Ringkasan:")
            summary = df.groupby("Keyword").size()
            for kw, count in summary.items():
                print(f"   • {kw}: {count} link")
        else:
            print("❌ Tidak ada data yang disimpan.")

if __name__ == "__main__":
    scrape_links()
