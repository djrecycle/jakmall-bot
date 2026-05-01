from playwright.sync_api import sync_playwright
import requests
import os
import time
import subprocess
import re
import pandas as pd
from difflib import SequenceMatcher

URL_FILE = "jakmall_links.csv"
MAX_URLS = 2

def load_urls():
    import sys
    is_update_mode = "--update" in sys.argv
    
    prompt_msg = "\nMasukkan URL Jakmall yang ingin di-update" if is_update_mode else "\nMasukkan URL Jakmall yang ingin discrape"
    prompt_msg += " (pisahkan dengan koma jika >1, biarkan kosong untuk mengambil dari CSV): "
    
    user_url = input(prompt_msg).strip()
    if user_url:
        urls = [u.strip() for u in user_url.split(",") if u.strip()]
        print(f"📋 Memproses {len(urls)} URL dari input manual.")
        return [{"url": u, "kategori": "Uncategorized"} for u in urls]

    try:
        df = pd.read_csv(URL_FILE, dtype={"Status": str}) if "Status" in pd.read_csv(URL_FILE, nrows=0).columns else pd.read_csv(URL_FILE)
    except FileNotFoundError:
        print(f"❌ File {URL_FILE} tidak ditemukan. Silakan jalankan jakmall_scrape_links.py terlebih dahulu.")
        exit()
    
    if "Status" not in df.columns:
        df["Status"] = ""
    else:
        df["Status"] = df["Status"].fillna("")
        
    if is_update_mode:
        unscraped_df = df
    else:
        unscraped_df = df[~df["Status"].isin(["Done", "Skip", "Failed"])]

    if unscraped_df.empty:
        if is_update_mode:
            print(f"🎉 Tidak ada URL sama sekali di {URL_FILE}!")
        else:
            print(f"🎉 Semua URL di {URL_FILE} sudah selesai discrape!")
        exit()

    if "Keyword" in df.columns:
        keywords = unscraped_df["Keyword"].value_counts()
        print("\n📂 Pilih kelompok URL yang ingin diproses:")
        print("─" * 30)
        print("  [0] Semua Keyword/Toko (Campur)")
        
        kw_list = list(keywords.items())
        for i, (kw, count) in enumerate(kw_list, 1):
            print(f"  [{i}] {kw} ({count} url)")
        print("─" * 30)
        
        while True:
            pilihan = input("Masukkan nomor pilihan (default: 0): ").strip()
            if pilihan == "" or pilihan == "0":
                print("✅ Memilih semua URL yang tersisa.")
                break
            try:
                idx = int(pilihan) - 1
                if 0 <= idx < len(kw_list):
                    selected_kw = kw_list[idx][0]
                    unscraped_df = unscraped_df[unscraped_df["Keyword"] == selected_kw]
                    print(f"✅ Memilih URL dengan target: {selected_kw}")
                    break
                else:
                    print("❌ Nomor tidak valid.")
            except ValueError:
                print("❌ Input harus berupa angka.")

    urls = unscraped_df["Link Produk"].dropna().tolist()

    if not urls:
        print("🎉 Tidak ada URL tersedia pada pilihan tersebut!")
        exit()

    urls = urls[:MAX_URLS]
    print(f"📋 Akan memproses: {len(urls)} URL pada batch ini (max {MAX_URLS})")
    
    result = []
    for link in urls:
        row = unscraped_df[unscraped_df["Link Produk"] == link].iloc[0]
        cat = getattr(row, "Kategori", "Uncategorized") if "Kategori" in df.columns else "Uncategorized"
        if pd.isna(cat) or not str(cat).strip():
            cat = "Uncategorized"
        result.append({"url": link, "kategori": str(cat)})
        
    return result

def calculate_upload_price(price_int):
    if not price_int:
        return "Tidak ditemukan"
    try:
        up_val = int(price_int * 1.2) # Markup 20%
        return f"Rp {up_val:,}".replace(',', '.')
    except:
        return str(price_int)

def update_status(url, status):
    try:
        df = pd.read_csv(URL_FILE, dtype={"Status": str}) if "Status" in pd.read_csv(URL_FILE, nrows=0).columns else pd.read_csv(URL_FILE)
        if "Status" not in df.columns:
            df["Status"] = ""
        else:
            df["Status"] = df["Status"].fillna("")
            
        df.loc[df["Link Produk"] == url, "Status"] = status
        df.to_csv(URL_FILE, index=False)
    except Exception as e:
        print(f"⚠️ Gagal mengupdate status CSV: {e}")

def scrape_jakmall():
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

    with sync_playwright() as p:
        print("🔗 Connect ke Chrome...")
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
        except Exception as e:
            print("❌ Gagal connect:", e)
            return

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()

        urls_data = load_urls()

        for idx, item in enumerate(urls_data, 1):
            url = item["url"]
            category = item["kategori"]
            
            save_dir = os.path.join("jakmall_hasil_md", category)
            os.makedirs(save_dir, exist_ok=True)

            print(f"\n{'='*50}")
            print(f"[{idx}/{len(urls_data)}] Membuka: {url}")

            page.goto(url, timeout=60000)
            page.wait_for_timeout(3000)

            # Scroll down to load images and other elements
            for _ in range(4):
                page.mouse.wheel(0, 600)
                page.wait_for_timeout(800)

            # ========================
            # EXTRACT DATA VIA SPDT
            # ========================
            try:
                spdt = page.evaluate("() => window.spdt")
                if not spdt:
                    raise ValueError("spdt not found")
            except Exception as e:
                print(f"❌ Gagal mengambil data produk via spdt: {e}")
                update_status(url, "Failed")
                continue

            # Basic Info
            try:
                title = page.locator('h1').first.inner_text().strip()
            except:
                title = url.split("/")[-1].replace("-", " ").title()

            store_name = spdt.get("store", {}).get("name", "Tidak ditemukan")
            store_url = spdt.get("store", {}).get("url", "")

            # Rating Toko
            try:
                rating_el = page.locator('div.si__review__rating')
                if rating_el.count() > 0:
                    rating_text = rating_el.first.inner_text().strip()
                    rating_str = f"⭐ {rating_text}"
                else:
                    rating_str = "Tidak ditemukan"
            except:
                rating_str = "Tidak ditemukan"
            
            # Harga Asli (Take first SKU)
            skus = spdt.get("sku", {})
            if not skus:
                print("❌ SKU tidak ditemukan")
                update_status(url, "Failed")
                continue
                
            first_sku_key = list(skus.keys())[0]
            first_sku = skus[first_sku_key]
            price_int = first_sku.get("price", {}).get("final", 0)
            price_str = f"Rp {price_int:,}".replace(',', '.')
            harga_upload = calculate_upload_price(price_int)

            # Kode SKU — SELALU ambil dari DOM dulu (bukan dari spdt.sku yang isinya kode internal seller)
            # HTML asli: <span class="dp__tab__content__label">Kode SKU</span>
            #            <span class="dp__tab__content__content">2968589018648</span>
            sku_code = ""
            try:
                labels = page.locator('span.dp__tab__content__label').all()
                for label in labels:
                    try:
                        if 'Kode SKU' in label.inner_text():
                            content_el = label.locator('xpath=following-sibling::span[contains(@class,"dp__tab__content__content")]')
                            if content_el.count() > 0:
                                sku_code = content_el.first.inner_text().strip()
                                break
                    except:
                        continue
            except:
                pass

            # Fallback ke spdt jika DOM gagal
            if not sku_code:
                sku_code = first_sku.get("sku", "") or first_sku.get("code", "") or "Tidak ditemukan"

            # Variasi
            variants_dict = spdt.get("variants", {})
            variant_results = []
            
            # Extract Variants from Matrix
            matrix = spdt.get("matrix", {})
            if matrix:
                for var_id_combo, sku_id in matrix.items():
                    sku_data = skus.get(str(sku_id), {})
                    if not sku_data:
                        continue
                        
                    # find variant names for this combo
                    combo_names = []
                    # Jakmall spdt.variants structure is complex, we will simplify:
                    for var_type_key, var_data in variants_dict.items():
                        for val_key, val_name in var_data.get("values", {}).items():
                            if val_key in var_id_combo:
                                combo_names.append(f"{var_data.get('name', 'Variasi')}: {val_name}")
                                
                    v_name = " | ".join(combo_names) if combo_names else "Default"
                    v_price_int = sku_data.get("price", {}).get("final", price_int)
                    v_price_str = f"Rp {v_price_int:,}".replace(',', '.')
                    v_price_up = calculate_upload_price(v_price_int)
                    
                    variant_results.append({
                        "variasi": v_name,
                        "harga": v_price_str,
                        "harga_up": v_price_up
                    })
                    
            # Gambar
            images_list = first_sku.get("images", [])
            img_urls = [img.get("detail") or img.get("thumbnail") for img in images_list if img.get("detail") or img.get("thumbnail")]
            
            # Save Images
            safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)[:30]
            folder = f"jakmall_gambar/{category}/{safe_title}"
            os.makedirs(folder, exist_ok=True)
            
            print(f"Total gambar: {len(img_urls)}")
            for i, url_img in enumerate(img_urls[:10]):
                if url_img.startswith("//"):
                    url_img = "https:" + url_img
                try:
                    img_data = requests.get(url_img, timeout=10).content
                    with open(f"{folder}/img_{i}.jpg", "wb") as f:
                        f.write(img_data)
                except Exception as e:
                    pass

            # ========================
            # EXTRACT DESC & SPECS
            # ========================
            try:
                description = page.locator('.dp__info').first.inner_text().strip()
                # Clean up repeated spaces/newlines
                description = re.sub(r'\n{3,}', '\n\n', description)
            except:
                description = "Tidak ditemukan"
                
            try:
                kelengkapan = page.locator('.dp__boxItem__values').first.inner_text().strip()
                if kelengkapan:
                    description += f"\n\n**Kelengkapan Produk:**\n{kelengkapan}"
            except:
                pass

            try:
                spec_rows = page.locator('.dp__spec__row').all()
                spec_table_md = "| Spesifikasi | Detail |\n| :--- | :--- |\n"
                has_specs = False
                for row in spec_rows:
                    cols = row.locator('.dp__spec__column').all()
                    if len(cols) == 2:
                        key = cols[0].inner_text().strip()
                        val = cols[1].inner_text().strip().replace("\n", " ").replace("|", "&#124;")
                        spec_table_md += f"| **{key}** | {val} |\n"
                        has_specs = True
                
                specification = spec_table_md if has_specs else "Tidak ditemukan"
            except:
                specification = "Tidak ditemukan"

            # ========================
            # INFO PRODUK (Brand, Garansi, dll)
            # ========================
            info_produk_md = ""
            try:
                # Klik tab Info Produk jika ada
                info_tab = page.locator('text=Info Produk').first
                if info_tab.is_visible():
                    info_tab.click()
                    page.wait_for_timeout(1500)

                info_rows = page.locator('.dp__info__row, .dp__specDetail__row, table.dp__table tr').all()
                if not info_rows:
                    # Coba selector lain
                    info_rows = page.locator('.dp__spec__row').all()

                if info_rows:
                    info_produk_md = "| Informasi | Detail |\n| :--- | :--- |\n"
                    for row in info_rows:
                        cols = row.locator('td, .dp__spec__column').all()
                        if len(cols) >= 2:
                            k = cols[0].inner_text().strip()
                            v = cols[1].inner_text().strip().replace("\n", " ").replace("|", "&#124;")
                            if k and v:
                                info_produk_md += f"| **{k}** | {v} |\n"
            except Exception as e:
                pass

            # ========================
            # INFO PENGIRIMAN (dari popup modal)
            # ========================
            shipping_info = {}
            couriers = []
            try:
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(600)

                # Klik tombol "Pilihan Pengiriman yang Tersedia" — bukan "Kebijakan Pengiriman"
                # Harus filter via teks karena ada banyak button.flex--simple di halaman
                ship_btn = page.locator('div.dp__si__doc button.flex--simple:has-text("Pilihan Pengiriman yang Tersedia")').first
                if ship_btn.count() == 0:
                    ship_btn = page.locator('button.flex--simple:has-text("Pilihan Pengiriman yang Tersedia")').first
                if ship_btn.count() == 0:
                    ship_btn = page.locator('button:has(span:has-text("Pilihan Pengiriman yang Tersedia"))').first

                if ship_btn.count() > 0 and ship_btn.is_visible():
                    ship_btn.click()
                    print("   🔗 Membuka popup Pilihan Pengiriman...")
                    page.wait_for_timeout(1500)  # Tunggu popup mulai render

                    # Tunggu elemen kurir muncul di halaman
                    try:
                        page.wait_for_selector('div.dp__warehouse-shipment__list', timeout=8000)
                        page.wait_for_timeout(1000)  # Tunggu semua baris kurir selesai render
                    except:
                        page.wait_for_timeout(2500)  # Fallback jika selector tidak ketemu

                    # Ambil "Dikirim dari" — cari elemen yang teksnya mengandung "Dikirim dari"
                    try:
                        dikirim_els = page.locator('*:has-text("Dikirim dari")').all()
                        for el in reversed(dikirim_els):  # Dari elemen terdalam
                            try:
                                raw = el.inner_text().strip()
                                lines = [l.strip() for l in raw.split('\n') if l.strip()]
                                for line in lines:
                                    if 'Dikirim dari' in line:
                                        dikirim_dari = line.replace('Dikirim dari', '').strip()
                                        if dikirim_dari and len(dikirim_dari) < 100:
                                            shipping_info['Dikirim dari'] = dikirim_dari
                                            break
                                if shipping_info.get('Dikirim dari'):
                                    break
                            except:
                                continue
                    except:
                        pass

                    # Mapping nama kurir dari filename logo
                    COURIER_MAP = {
                        'jne': 'JNE',
                        'sicepat': 'SiCepat',
                        'go-send': 'GoSend',
                        'gosend': 'GoSend',
                        'j&t': 'J&T Express',
                        'jnt': 'J&T Express',
                        'grab-express': 'GrabExpress',
                        'grabexpress': 'GrabExpress',
                        'ninja': 'Ninja Xpress',
                        'shopee': 'ShopeeExpress',
                        'anteraja': 'AnterAja',
                        'lion': 'Lion Parcel',
                        'pos': 'Pos Indonesia',
                        'tiki': 'TIKI',
                        'rpx': 'RPX',
                    }

                    # Ambil setiap item kurir dari popup
                    # <div class="dp__warehouse-shipment__list-item">
                    #   <div class="dp__warehouse-shipment__item-logo"><img src="...logo-jne.png?2"></div>
                    #   <div class="dp__warehouse-shipment__item-text"><span>REG ,</span><span>YES ,</span>...</div>
                    # </div>
                    items = page.locator('div.dp__warehouse-shipment__list-item').all()
                    print(f"   📦 Ditemukan {len(items)} baris kurir")

                    for item_el in items:
                        try:
                            # Nama kurir dari src logo
                            img_src = item_el.locator('img').first.get_attribute('src') or ''
                            courier_name = ''
                            if img_src:
                                filename = img_src.split('/')[-1].split('?')[0].replace('logo-', '').replace('.png', '').replace('.jpg', '').lower()
                                # Cek mapping
                                courier_name = COURIER_MAP.get(filename, '')
                                if not courier_name:
                                    # Fallback: capitalize setiap kata
                                    courier_name = ' '.join(
                                        w.upper() if len(w) <= 3 else w.capitalize()
                                        for w in filename.replace('&amp;', '&').split('-')
                                    )

                            # Layanan dari span-span di item-text
                            spans = item_el.locator('div.dp__warehouse-shipment__item-text span').all()
                            services = []
                            for span in spans:
                                svc = span.inner_text().strip().rstrip(',').strip()
                                if svc:
                                    services.append(svc)
                            services_str = ' , '.join(services)

                            if courier_name:
                                entry = f"{courier_name} — {services_str}" if services_str else courier_name
                                if entry not in couriers:
                                    couriers.append(entry)
                        except:
                            continue

                    print(f"   ✅ Ditemukan {len(couriers)} kurir")

                    # Tutup popup dengan Escape
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                else:
                    print("   ⚠️ Tombol Pilihan Pengiriman tidak ditemukan")

            except Exception as e:
                print(f"   ⚠️ Gagal ambil info pengiriman: {e}")


            # ========================
            # SIMPAN KE MARKDOWN
            # ========================
            print(f"\n📋 Hasil scraping:")
            print(f"   Judul  : {title[:60]}")
            print(f"   Harga  : {price_str}")
            print(f"   Rating : {rating_str}")
            print(f"   SKU    : {sku_code}")
            print(f"   Variasi: {len(variant_results)} item")
            print(f"   Gambar : {len(img_urls)} file")
            print(f"   Ekspedisi: {len(couriers)} pilihan")

            clean_title = re.sub(r'[\\/*?:"<>|]', "", title)
            clean_title = re.sub(r'[^\x00-\x7f]', r'', clean_title)
            filename = clean_title.strip()[:50].strip() or "produk"

            md_content = f"""# {title}

## 💰 Harga
Harga Asli: {price_str}
<span style="color: green; font-weight: bold;">Harga Upload: {harga_upload}</span>

## 🏠 Info Toko
| | |
| :--- | :--- |
| **Toko** | [{store_name}]({store_url}) |
| **Rating** | {rating_str} |
| **SKU** | {sku_code} |

## 🔗 Link Produk
{url}

## 🚚 Info Pengiriman
"""
            if shipping_info:
                md_content += "| Info | Detail |\n| :--- | :--- |\n"
                for k, v in shipping_info.items():
                    md_content += f"| **{k}** | {v} |\n"
            else:
                md_content += "Tidak ditemukan\n"

            if couriers:
                md_content += "\n**Pilihan Ekspedisi:**\n"
                for c in couriers:
                    md_content += f"- {c}\n"

            md_content += f"""
## 📋 Spesifikasi
{specification}

## 📄 Info Produk
{info_produk_md if info_produk_md else 'Tidak ditemukan'}

## 📝 Deskripsi
{description}
"""

            md_content += "\n## 🔧 Variasi Produk\n"

            if variant_results:
                for v in variant_results:
                    md_content += f"- {v['variasi']} : {v['harga']} <span style='color: green; font-weight: bold;'>(Upload: {v['harga_up']})</span>\n"
            else:
                md_content += "- Tidak ada variasi\n"

            md_content += "\n## 🖼️ Gambar Produk\n"

            for i, img in enumerate(img_urls):
                if img.startswith("//"):
                    img = "https:" + img
                md_content += f"\n![Gambar {i+1}]({img})\n"

            file_path = os.path.join(save_dir, f"{filename}.md")

            if os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                print(f"🔄 Diupdate: {filename}.md (ditimpa dengan data baru)")
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                print(f"✔ Disimpan: {filename}.md")
                
            update_status(url, "Done")

        print(f"\n{'='*50}")
        print("🏁 Selesai scraping Jakmall!")

if __name__ == "__main__":
    scrape_jakmall()
