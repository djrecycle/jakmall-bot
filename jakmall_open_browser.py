import subprocess
import os
import sys

def main():
    print("====================================================")
    print("             MEMBUKA BROWSER JAKMALL                ")
    print("====================================================\n")
    print("1. Browser ini digunakan agar bisa Login ke akun Jakmall.")
    print("2. Biarkan browser tetap TERBUKA saat menjalankan script scraping.")
    print("3. Profil disave di folder 'jakmall_debug_profile'.\n")
    
    # Path folder profile untuk menyimpan cookie login dsb
    profile_path = os.path.abspath("jakmall_debug_profile")
    
    cmd = [
        "google-chrome",
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile_path}",
        "--no-first-run",
        "--no-default-browser-check"
    ]
    
    print("Membuka Google Chrome...")
    try:
        # Gunakan subprocess.Popen agar script python bisa langsung selesai (browser jalan di background)
        # Tapi karena ini menu interaktif, lebih baik jika ditahan sebentar
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Browser berhasil dibuka! Silakan Login ke Jakmall jika diperlukan.")
        print("\nJangan tutup browser ini. Anda bisa kembali ke menu utama.")
    except FileNotFoundError:
         print("❌ Gagal membuka Chrome. Pastikan google-chrome sudah terinstall.")
    except Exception as e:
         print(f"❌ Terjadi kesalahan: {e}")

if __name__ == "__main__":
    main()
