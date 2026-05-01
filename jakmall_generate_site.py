import os
import json
import webbrowser

def parse_markdown(content):
    parsed = {
        "Judul": "",
        "Harga": "",
        "Link Toko": "",
        "Link Produk": "",
        "Spesifikasi": "",
        "Deskripsi": "",
        "Variasi": ""
    }
    
    lines = content.split('\n')
    current_section = None
    section_content = []
    
    for line in lines:
        if line.startswith('# '):
            parsed["Judul"] = line[2:].strip()
        elif line.startswith('## '):
            if current_section and current_section in parsed:
                parsed[current_section] = '\n'.join(section_content).strip()
            
            section_name = line[3:].strip()
            if 'Harga' in section_name: current_section = "Harga"
            elif 'Link Toko' in section_name: current_section = "Link Toko"
            elif 'Link Produk' in section_name: current_section = "Link Produk"
            elif 'Spesifikasi' in section_name: current_section = "Spesifikasi"
            elif 'Deskripsi' in section_name: current_section = "Deskripsi"
            elif 'Variasi' in section_name: current_section = "Variasi"
            elif 'Gambar' in section_name: current_section = "Gambar"
            else: current_section = section_name
            section_content = []
        else:
            if current_section:
                section_content.append(line)
                
    if current_section and current_section in parsed:
        parsed[current_section] = '\n'.join(section_content).strip()
        
    return parsed

def generate_site():
    print("🌐 Memulai pembuatan website preview Jakmall...")
    
    hasil_md_dir = "jakmall_hasil_md"
    if not os.path.exists(hasil_md_dir):
        print(f"❌ Folder '{hasil_md_dir}' tidak ditemukan. Silakan jalankan scraper terlebih dahulu.")
        return

    # Scan data
    data = {}
    categories = sorted([d for d in os.listdir(hasil_md_dir) if os.path.isdir(os.path.join(hasil_md_dir, d))])
    
    for cat in categories:
        data[cat] = []
        cat_path = os.path.join(hasil_md_dir, cat)
        files = sorted([f for f in os.listdir(cat_path) if f.endswith(".md")])
        
        for f in files:
            file_path = os.path.join(cat_path, f)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                data[cat].append({
                    "name": f.replace(".md", ""),
                    "content": content,
                    "parsed": parse_markdown(content)
                })
            except Exception as e:
                print(f"⚠️ Gagal membaca {f}: {e}")

    try:
        with open("template_dump.json", "r") as f:
            template_headers_json = f.read()
    except:
        template_headers_json = "[]"

    html_template = f"""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Preview JakmallBot</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.sheetjs.com/xlsx-latest/package/dist/xlsx.full.min.js"></script>
    <style>
        :root {{
            --jakmall-blue: #0088cc; /* Jakmall Blue */
            --bg-dark: #0f0f12;
            --sidebar-bg: rgba(25, 25, 30, 0.8);
            --card-bg: #1e1e24;
            --text-primary: #e0e0e0;
            --text-secondary: #a0a0a0;
            --accent: #33b5e5;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Inter', sans-serif; background-color: var(--bg-dark); color: var(--text-primary); display: flex; height: 100vh; overflow: hidden; }}

        /* Sidebar Style */
        .sidebar {{ width: 320px; background: var(--sidebar-bg); backdrop-filter: blur(12px); border-right: 1px solid rgba(255, 255, 255, 0.05); display: flex; flex-direction: column; transition: all 0.3s ease; z-index: 100; }}
        .sidebar-header {{ padding: 30px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }}
        .sidebar-header h1 {{ font-size: 1.5rem; font-weight: 700; color: var(--jakmall-blue); display: flex; align-items: center; gap: 10px; }}
        .search-container {{ padding: 15px 25px; }}
        .search-input {{ width: 100%; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); padding: 12px 15px; border-radius: 8px; color: white; outline: none; transition: border 0.3s; }}
        .search-input:focus {{ border-color: var(--jakmall-blue); }}
        .nav-content {{ flex: 1; overflow-y: auto; padding: 10px 0; }}
        .category-group {{ margin-bottom: 15px; }}
        .category-title {{ padding: 12px 25px; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; color: white; font-weight: 700; cursor: pointer; display: flex; justify-content: space-between; align-items: center; background: rgba(255, 255, 255, 0.02); transition: background 0.2s; }}
        .category-title:hover {{ background: rgba(255, 255, 255, 0.05); }}
        .category-title::after {{ content: '▼'; font-size: 0.6rem; transition: transform 0.3s; color: var(--jakmall-blue); }}
        .category-group.collapsed .category-title::after {{ transform: rotate(-90deg); }}
        .category-items {{ max-height: 1000px; overflow: hidden; transition: max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1); }}
        .category-group.collapsed .category-items {{ max-height: 0; }}
        .file-item {{ padding: 12px 25px; cursor: pointer; transition: all 0.2s; font-size: 0.9rem; border-left: 3px solid transparent; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .file-item:hover {{ background: rgba(255, 255, 255, 0.03); color: white; }}
        .file-item.active {{ background: rgba(0, 136, 204, 0.1); color: var(--jakmall-blue); border-left-color: var(--jakmall-blue); font-weight: 600; }}

        /* Buttons */
        .btn {{ background: var(--jakmall-blue); color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 600; transition: background 0.3s; display: flex; align-items: center; gap: 5px; }}
        .btn:hover {{ background: #006699; }}
        .btn-small {{ padding: 4px 8px; font-size: 0.7rem; }}
        .export-all-container {{ padding: 0 25px 15px 25px; }}
        
        .markup-control {{ padding: 15px 25px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }}
        .markup-control label {{ font-size: 0.8rem; color: var(--text-secondary); display: block; margin-bottom: 8px; }}
        .markup-control .markup-row {{ display: flex; align-items: center; gap: 10px; }}
        .markup-control input[type="range"] {{ flex: 1; accent-color: var(--jakmall-blue); cursor: pointer; height: 6px; -webkit-appearance: none; appearance: none; background: rgba(255,255,255,0.1); border-radius: 3px; outline: none; }}
        .markup-control input[type="range"]::-webkit-slider-thumb {{ -webkit-appearance: none; appearance: none; width: 18px; height: 18px; border-radius: 50%; background: var(--jakmall-blue); cursor: pointer; box-shadow: 0 2px 6px rgba(0,136,204,0.4); transition: transform 0.15s; }}
        .markup-control input[type="range"]::-webkit-slider-thumb:hover {{ transform: scale(1.2); }}
        .markup-control .pct-input {{ width: 60px; background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); padding: 6px 8px; border-radius: 6px; color: #4cff88; font-weight: 700; font-size: 0.9rem; text-align: center; outline: none; transition: border 0.3s; }}
        .markup-control .pct-input:focus {{ border-color: var(--jakmall-blue); }}
        .markup-control .pct-label {{ color: #4cff88; font-weight: 700; font-size: 0.9rem; min-width: 15px; }}

        .product-actions {{ display: flex; justify-content: flex-end; margin-bottom: 20px; }}

        /* Main Content Style */
        .main-content {{ flex: 1; overflow-y: auto; padding: 40px; background: radial-gradient(circle at top right, rgba(0, 136, 204, 0.05), transparent); }}
        .content-container {{ max-width: 900px; margin: 0 auto; background: var(--card-bg); padding: 50px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); min-height: 80vh; }}
        .welcome-screen {{ height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: var(--text-secondary); }}
        .welcome-screen h1 {{ color: var(--jakmall-blue); margin-bottom: 20px; font-size: 2.5rem; }}

        /* Markdown Rendering Overrides */
        #rendered-content h1 {{ margin-bottom: 30px; color: var(--jakmall-blue); line-height: 1.2; }}
        #rendered-content h2 {{ margin-top: 40px; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; }}
        #rendered-content p {{ margin-bottom: 15px; line-height: 1.6; }}
        #rendered-content ul, #rendered-content ol {{ margin-bottom: 20px; padding-left: 20px; }}
        #rendered-content li {{ margin-bottom: 8px; }}
        #rendered-content img {{ max-width: 100%; border-radius: 12px; margin: 20px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.2); transition: transform 0.3s; cursor: zoom-in; }}
        #rendered-content img:hover {{ transform: scale(1.02); }}
        #rendered-content a {{ color: var(--accent); text-decoration: none; }}
        #rendered-content a:hover {{ text-decoration: underline; }}
        #rendered-content blockquote {{ border-left: 4px solid var(--jakmall-blue); padding-left: 20px; color: var(--text-secondary); font-style: italic; margin-bottom: 20px; }}
        #rendered-content table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        #rendered-content th, #rendered-content td {{ border: 1px solid rgba(255,255,255,0.1); padding: 12px; text-align: left; }}
        #rendered-content th {{ background: rgba(255,255,255,0.05); }}

        ::-webkit-scrollbar {{ width: 8px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.1); border-radius: 10px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: rgba(255,255,255,0.2); }}

        @media (max-width: 768px) {{
            body {{ flex-direction: column; }}
            .sidebar {{ width: 100%; height: auto; max-height: 40vh; }}
            .main-content {{ padding: 20px; }}
            .content-container {{ padding: 25px; }}
        }}
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="sidebar-header">
            <h1>🛍️ JakmallBot</h1>
            <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 5px;">Dashboard Preview Produk</p>
        </div>
        
        <div class="search-container">
            <input type="text" id="search-input" class="search-input" placeholder="Cari nama produk...">
        </div>
        
        <div class="export-all-container">
            <button class="btn" onclick="exportAll()" style="width: 100%; justify-content: center;">📊 Export Semua ke Excel</button>
        </div>

        <div class="markup-control">
            <label>💹 Persentase Harga Upload</label>
            <div class="markup-row">
                <input type="range" id="markup-slider" min="0" max="100" value="20" step="1">
                <input type="number" id="markup-input" class="pct-input" min="0" max="100" value="20" step="1">
                <span class="pct-label">%</span>
            </div>
        </div>

        <div class="nav-content" id="nav-content">
        </div>
    </div>

    <div class="main-content">
        <div class="content-container" id="content-container">
            <div id="welcome-screen" class="welcome-screen">
                <h1>Selamat Datang!</h1>
                <p>Silakan pilih kategori dan produk di sebelah kiri untuk melihat detail hasil scraping dari Jakmall.</p>
                <div style="margin-top: 40px; font-size: 3rem; opacity: 0.5;">📦</div>
            </div>
            <div id="rendered-content" style="display: none;"></div>
        </div>
    </div>

    <script>
        const appData = {json.dumps(data)};
        const templateHeaders = {template_headers_json};
        let currentMarkupPct = 20;

        const markupSlider = document.getElementById('markup-slider');
        const markupInput = document.getElementById('markup-input');

        function syncMarkup(val) {{
            val = Math.max(0, Math.min(100, parseInt(val) || 0));
            currentMarkupPct = val;
            markupSlider.value = val;
            markupInput.value = val;
            recalcUploadPrices();
        }}

        markupSlider.addEventListener('input', (e) => syncMarkup(e.target.value));
        markupInput.addEventListener('input', (e) => syncMarkup(e.target.value));

        function calcUploadPrice(originalStr) {{
            if (!originalStr || originalStr === '-' || originalStr === 'Tidak ditemukan') return originalStr;
            try {{
                const parts = originalStr.split('-');
                const results = parts.map(p => {{
                    const numStr = p.replace(/[^0-9]/g, '');
                    if (!numStr) return p.trim();
                    const val = parseInt(numStr);
                    const upVal = Math.round(val * (1 + currentMarkupPct / 100));
                    return 'Rp' + upVal.toLocaleString('id-ID').replace(/,/g, '.');
                }});
                return results.join(' - ');
            }} catch {{
                return originalStr;
            }}
        }}

        function recalcUploadPrices() {{
            document.querySelectorAll('[data-upload-price]').forEach(el => {{
                const original = el.getAttribute('data-original-price');
                const newPrice = calcUploadPrice(original);
                if (el.hasAttribute('data-is-variant')) {{
                    el.textContent = `(Upload: ${{newPrice}})`;
                }} else {{
                    el.textContent = `Harga Upload: ${{newPrice}}`;
                }}
            }});
        }}

        const navContent = document.getElementById('nav-content');
        const searchInput = document.getElementById('search-input');
        const renderedDiv = document.getElementById('rendered-content');
        const welcomeScreen = document.getElementById('welcome-screen');

        function getExportRows(product) {{
            let rows = [];
            
            const imgRegex = /!\\[.*?\\]\\((.*?)\\)/g;
            let images = [];
            let match;
            while ((match = imgRegex.exec(product.parsed["Gambar"] || "")) !== null) {{
                images.push(match[1]);
            }}
            
            let variasiText = product.parsed["Variasi"] || "";
            let variations = [];
            if (!variasiText.includes("- Tidak ada variasi")) {{
                let varLines = variasiText.split('\\n');
                varLines.forEach(line => {{
                    if (line.startsWith('- ')) {{
                        line = line.substring(2);
                        let parts = line.split(' : ');
                        if (parts.length >= 2) {{
                            let varNameVal = parts[0]; 
                            let nameValSplit = varNameVal.split(': ');
                            let namaVar = nameValSplit[0] || "Variasi";
                            let varianVar = nameValSplit.slice(1).join(': ') || varNameVal;
                            
                            let priceImg = parts.slice(1).join(' : ');
                            let priceParts = priceImg.split(' | ');
                            let rawPriceString = priceParts[0];
                            let uploadMatch = rawPriceString.match(/Upload: Rp([\\d\\.]+)/);
                            let price = "";
                            if (uploadMatch) {{
                                price = uploadMatch[1].replace(/[^0-9]/g, '');
                            }} else {{
                                price = rawPriceString.replace(/[^0-9]/g, '');
                            }}
                            
                            let imgUrl = "";
                            let imgMatch = priceImg.match(/\\]\\((.*?)\\)/);
                            if (imgMatch) imgUrl = imgMatch[1];
                            
                            variations.push({{
                                namaVar: namaVar.trim(),
                                varianVar: varianVar.trim(),
                                price: price,
                                imgUrl: imgUrl
                            }});
                        }}
                    }}
                }});
            }}

            let kodeKategoriMatch = product.parsed["Spesifikasi"] ? product.parsed["Spesifikasi"].match(/\\|\\s*\\*\\*Kode Kategori\\*\\*\\s*\\|\\s*(.*?)\\s*\\|/) : null;
            let kodeKategori = kodeKategoriMatch ? kodeKategoriMatch[1].trim() : product.category;

            if (variations.length === 0) {{
                let row = new Array(41).fill("");
                row[1] = kodeKategori; 
                row[2] = product.parsed["Judul"] || ""; 
                row[3] = product.parsed["Deskripsi"] || ""; 
                
                let rawPriceString = product.parsed["Harga"] || "";
                let uploadMatch = rawPriceString.match(/Harga Upload: Rp([\\d\\.]+)/);
                let rawPrice = "";
                if (uploadMatch) {{
                    rawPrice = uploadMatch[1].replace(/[^0-9]/g, '');
                }} else {{
                    rawPrice = rawPriceString.replace(/[^0-9]/g, '');
                }}
                row[17] = rawPrice; 
                row[18] = "100"; 
                
                for (let i=0; i<images.length && i<9; i++) {{
                    row[23+i] = images[i];
                }}
                
                row[32] = "1000";
                row[36] = "Aktif"; 
                row[37] = "Aktif"; 
                rows.push(row);
            }} else {{
                let baseTitle = product.parsed["Judul"] || "";
                let kodeIntegrasi = "VAR_" + baseTitle.substring(0, 10).replace(/[^a-zA-Z0-9]/g, '');
                
                for (let i=0; i<variations.length; i++) {{
                    let v = variations[i];
                    let row = new Array(41).fill("");
                    if (i === 0) {{
                        row[1] = kodeKategori;
                        row[2] = baseTitle;
                        row[3] = product.parsed["Deskripsi"] || "";
                        
                        for (let j=0; j<images.length && j<9; j++) {{
                            row[23+j] = images[j];
                        }}
                        row[32] = "1000";
                        row[36] = "Aktif";
                        row[37] = "Aktif";
                    }}
                    
                    row[11] = kodeIntegrasi;
                    row[12] = v.namaVar; 
                    row[13] = v.varianVar;
                    row[14] = v.imgUrl; 
                    row[17] = v.price; 
                    row[18] = "100"; 
                    
                    rows.push(row);
                }}
            }}
            return rows;
        }}

        function exportToExcel(dataRows, filename) {{
            const finalData = [];
            if (templateHeaders && templateHeaders.length > 0) {{
                finalData.push(templateHeaders[0]);
            }} else {{
                finalData.push(["Produk Data..."]); 
            }}
            
            dataRows.forEach(r => finalData.push(r));
            
            const ws = XLSX.utils.aoa_to_sheet(finalData);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, "Template");
            XLSX.writeFile(wb, filename + ".xlsx");
        }}

        window.exportAll = function() {{
            let rows = [];
            for (const category in appData) {{
                appData[category].forEach(p => {{
                    const productRows = getExportRows({{...p, category}});
                    productRows.forEach(r => rows.push(r));
                }});
            }}
            if (rows.length > 0) exportToExcel(rows, "Template_Semua_Produk_Jakmall");
            else alert("Tidak ada data untuk diexport");
        }};

        window.exportCategory = function(category) {{
            let rows = [];
            if (appData[category]) {{
                appData[category].forEach(p => {{
                    const productRows = getExportRows({{...p, category}});
                    productRows.forEach(r => rows.push(r));
                }});
            }}
            if (rows.length > 0) exportToExcel(rows, `Template_Kategori_${{category}}`);
            else alert("Tidak ada data untuk diexport");
        }};

        window.exportProduct = function(category, name) {{
            const product = appData[category]?.find(p => p.name === name);
            if (product) {{
                const productRows = getExportRows({{...product, category}});
                exportToExcel(productRows, `Template_${{name}}`);
            }}
        }};

        function renderNav(filter = '') {{
            navContent.innerHTML = '';
            
            for (const category in appData) {{
                const filteredProducts = appData[category].filter(p => 
                    p.name.toLowerCase().includes(filter.toLowerCase())
                );

                if (filteredProducts.length === 0) continue;

                const group = document.createElement('div');
                group.className = 'category-group';
                if (filter === '') group.classList.add('collapsed');
                
                const title = document.createElement('div');
                title.className = 'category-title';
                
                const textSpan = document.createElement('span');
                textSpan.innerText = category;
                
                const actionDiv = document.createElement('div');
                actionDiv.style.display = "flex";
                actionDiv.style.alignItems = "center";
                actionDiv.style.gap = "10px";
                
                const exportBtn = document.createElement('button');
                exportBtn.className = 'btn btn-small';
                exportBtn.innerText = '📊 Export';
                exportBtn.title = 'Export Kategori ke Excel';
                exportBtn.onclick = (e) => {{
                    e.stopPropagation();
                    exportCategory(category);
                }};
                
                const arrowSpan = document.createElement('span');
                arrowSpan.className = 'arrow';
                
                actionDiv.appendChild(exportBtn);
                actionDiv.appendChild(arrowSpan);
                
                title.appendChild(textSpan);
                title.appendChild(actionDiv);
                title.onclick = () => group.classList.toggle('collapsed');
                group.appendChild(title);

                const itemsContainer = document.createElement('div');
                itemsContainer.className = 'category-items';

                filteredProducts.forEach(product => {{
                    const item = document.createElement('div');
                    item.className = 'file-item';
                    item.innerText = product.name;
                    item.title = product.name;
                    item.onclick = (e) => {{
                        e.stopPropagation();
                        showContent(category, product.name, item);
                    }};
                    itemsContainer.appendChild(item);
                }});

                if (filter !== '') group.classList.remove('collapsed');

                group.appendChild(itemsContainer);
                navContent.appendChild(group);
            }}
        }}

        function showContent(category, name, element) {{
            document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
            element.classList.add('active');

            const product = appData[category].find(p => p.name === name);
            if (!product) return;

            welcomeScreen.style.display = 'none';
            renderedDiv.style.display = 'block';
            
            const safeCat = category.replace(/'/g, "\\'").replace(/"/g, "&quot;");
            const safeName = name.replace(/'/g, "\\'").replace(/"/g, "&quot;");
            
            let htmlContent = `
                <div class="product-actions">
                    <button class="btn" onclick="exportProduct('${{safeCat}}', '${{safeName}}')">📊 Export Produk ke Excel</button>
                </div>
            `;
            htmlContent += marked.parse(product.content);
            renderedDiv.innerHTML = htmlContent;

            renderedDiv.querySelectorAll('span').forEach(span => {{
                const text = span.textContent.trim();
                const mainMatch = text.match(/^Harga Upload: Rp([\\d\\.]+)$/);
                if (mainMatch) {{
                    const parentEl = span.parentElement;
                    const parentText = parentEl ? parentEl.textContent : '';
                    const origMatch = parentText.match(/Harga Asli: Rp([\\d\\.]+)/);
                    if (origMatch) {{
                        span.setAttribute('data-upload-price', 'true');
                        span.setAttribute('data-original-price', 'Rp' + origMatch[1]);
                    }}
                }}
                const varMatch = text.match(/^\\(Upload: Rp([\\d\\.]+)\\)$/);
                if (varMatch) {{
                    const li = span.closest('li') || span.parentElement;
                    if (li) {{
                        const liText = li.textContent;
                        const origVarMatch = liText.match(/: Rp([\\d\\.]+)\\s*\\(Upload:/);
                        if (origVarMatch) {{
                            span.setAttribute('data-upload-price', 'true');
                            span.setAttribute('data-is-variant', 'true');
                            span.setAttribute('data-original-price', 'Rp' + origVarMatch[1]);
                        }}
                    }}
                }}
            }});

            recalcUploadPrices();
            document.querySelector('.main-content').scrollTop = 0;
        }}

        searchInput.oninput = (e) => renderNav(e.target.value);
        renderNav();
    </script>
</body>
</html>
"""

    output_file = "jakmall_preview.html"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"✅ Website preview Berhasil dibuat: {output_file}")
        
        file_url = "file://" + os.path.abspath(output_file)
        print(f"🚀 Membuka {output_file} di browser...")
        webbrowser.open(file_url)
    except Exception as e:
        print(f"❌ Gagal menyimpan file preview: {e}")

if __name__ == "__main__":
    generate_site()
