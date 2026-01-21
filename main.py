import requests
from bs4 import BeautifulSoup
import time
import random
import re # Thư viện xử lý Regex để lọc tên file
from urllib.parse import urljoin

# ================= CẤU HÌNH =================
# Link chương đầu tiên
START_URL = "LINK_CHUONG_DAU_TIEN"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://truyenwikidich.net/'
}
# ============================================

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def download_novel():
    current_url = START_URL
    chapter_count = 0
    output_filename = None 
    
    print(f"🚀 Đang kết nối tới: {current_url}")

    while current_url:
        try:
            response = requests.get(current_url, headers=HEADERS, timeout=10)
            
            if response.status_code != 200:
                print(f"❌ Lỗi tải trang (Code {response.status_code}): {current_url}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            if output_filename is None:
                book_title_tag = soup.find('p', class_='book-title')
                
                if book_title_tag:
                    raw_name = book_title_tag.get_text(strip=True)
                    clean_name = clean_filename(raw_name)
                    output_filename = f"{clean_name}.html"
                    print(f"📖 Phát hiện tên truyện: {raw_name}")
                    print(f"💾 Sẽ lưu vào file: {output_filename}")
                else:
                    # Fallback nếu không tìm thấy
                    output_filename = "Truyen_Wikidich.html"
                    print("⚠️ Không tìm thấy tên truyện, dùng tên mặc định.")

                # Tạo file mới và viết Header HTML
                with open(output_filename, "w", encoding="utf-8") as f:
                    f.write(f"<html><head><meta charset='utf-8'><title>{raw_name}</title></head><body>\n")
                    f.write(f"<h1 style='text-align:center; color:blue;'>{raw_name}</h1>\n") # Tiêu đề to đùng đầu sách

            # Lấy tiêu đề chương hiện tại
            chap_tag = soup.find('a', class_='chapter-name')
            if not chap_tag:
                 # Nếu không có thì tìm thẻ khác
                 chap_tag = soup.find('p', class_='book-title', style=lambda v: v and '1.2rem' in v)
            
            chapter_title = chap_tag.get_text(strip=True) if chap_tag else f"Chương {chapter_count + 1}"

            # Lấy nội dung
            content_div = soup.find('div', id='bookContentBody')
            
            if content_div:
                with open(output_filename, "a", encoding="utf-8") as f:
                    f.write(f"<h2>{chapter_title}</h2>\n")
                    for p in content_div.find_all('p'):
                        f.write(f"<p>{p.get_text()}</p>\n")
                    f.write("<hr/>\n")
                
                print(f"✅ Đã tải: {chapter_title}")
                chapter_count += 1
            else:
                print(f"⚠️ Không lấy được nội dung chương này: {current_url}")

            # Tìm link chương sau
            next_btn = soup.find('a', id='btnNextChapter')
            
            if next_btn and 'href' in next_btn.attrs:
                next_link = next_btn['href']
                if "javascript" in next_link or not next_link:
                    print("🏁 Đã đến chương cuối.")
                    break
                current_url = urljoin("https://truyenwikidich.net", next_link)
            else:
                print("🏁 Không thấy nút chương sau. Kết thúc.")
                break

            # Sleep
            sleep_time = random.uniform(2, 4)
            time.sleep(sleep_time)

        except Exception as e:
            print(f"❌ Lỗi: {e}")
            break

    # Đóng thẻ HTML khi hết
    if output_filename:
        with open(output_filename, "a", encoding="utf-8") as f:
            f.write("</body></html>")
        print(f"\n🎉 XONG! Truyện đã lưu tại: {output_filename}")

if __name__ == "__main__":
    download_novel()