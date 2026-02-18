import requests
import hashlib
from bs4 import BeautifulSoup
import time
import random
import re 
from urllib.parse import urljoin
import os
import time as _time

# ================= CẤU HÌNH =================
# Mặc định START_URL dùng khi chạy trực tiếp
START_URL = "LINK_CHUONG_DAU_TIEN"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://truyenwikidich.net/'
}

# Supported sites that use JS-rendered chapter lists
SUPPORTED_WIKI_SITES = ['truyenwikidich.net', 'wikicv.net', 'wikidich.net']
# ============================================

def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def get_chapter_list(novel_url):
    """Return list of chapters as [{'title':..., 'url': ...}, ...]

    Tries several selectors: 'a.chapter-name' first, then elements under '.volume-name',
    then a fallback scanning links containing 'chapter' or 'chuong'.
    """
    try:
        # If caller passed an explicit AJAX path (/book/index?...), call it directly
        if '/book/index' in novel_url:
            resp = requests.get(novel_url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        else:
            resp = requests.get(novel_url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Không tải được trang truyện: {e}")

    soup = BeautifulSoup(resp.text, 'html.parser')

    # Prefer common selectors. Several sites use different structures:
    # - <a class="chapter-name">...
    # - <li class="chapter-name"><a class="truncate" href="...">...</a></li>
    # Try them in order and keep fallback options.
    chapter_tags = soup.select('a.chapter-name') or []

    if not chapter_tags:
        # handle the pattern you provided: li.chapter-name > a.truncate
        chapter_tags = soup.select('li.chapter-name a.truncate') or []

    # fallback: find within volume containers
    if not chapter_tags:
        vols = soup.select('.volume-name')
        for vol in vols:
            for a in vol.find_all('a', href=True):
                chapter_tags.append(a)

    # final fallback: scan all links for keywords (chapter/chuong)
    if not chapter_tags:
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            text = (a.get_text() or '').lower()
            if 'chapter' in href or 'chuong' in href or 'chương' in text:
                chapter_tags.append(a)

    # If only 1 or 0 chapters found, it's likely a placeholder — try AJAX / Selenium
    needs_more_fallback = len(chapter_tags) <= 1
    
    # For wiki sites (truyenwikidich, wikicv, wikidich), ALWAYS try Selenium because chapters are JS-rendered
    is_wiki_site = any(site in novel_url for site in SUPPORTED_WIKI_SITES)
    if is_wiki_site:
        needs_more_fallback = True  # Force Selenium approach
        chapter_tags = []  # Clear navigation links

    # If still nothing (or just 1 placeholder), try to call the site's AJAX endpoint.
    if needs_more_fallback:
        # 1) If the page contains an explicit /book/index?... string (as seen in DevTools), call it directly
        m_explicit = re.search(r"(/book/index\?[^'\"\s]+)", resp.text)
        if m_explicit:
            ajax_path = m_explicit.group(1)
            ajax_url = urljoin(novel_url, ajax_path)
            try:
                r = requests.get(ajax_url, headers=HEADERS, timeout=10)
                if r.status_code == 200 and r.text:
                    s2 = BeautifulSoup(r.text, 'html.parser')
                    chapter_tags = s2.select('li.chapter-name a.truncate') or s2.select('a.chapter-name') or chapter_tags
            except Exception:
                pass

        # 2) fallback: try to extract bookId / signKey from the page and calculate sign
        if len(chapter_tags) <= 1:
            book_id = None
            sign_key = None
            sign_val = None
            start_val = 0
            size_val = 2000

            # data-book attributes appear often on page
            m = re.search(r"data-book\s*=\s*['\"]([0-9a-fA-F]+)['\"]", resp.text)
            if m:
                book_id = m.group(1)

            # fallback: look for bookId in JS assignment
            if not book_id:
                m = re.search(r"bookId\s*[:=]\s*['\"]([0-9a-fA-F]+)['\"]", resp.text)
                if m:
                    book_id = m.group(1)

            m = re.search(r"signKey\s*[:=]\s*['\"]([0-9a-fA-F]+)['\"]", resp.text)
            if m:
                sign_key = m.group(1)

            # Always calculate sign using: sign = SHA256(fuzzySign(signKey + start + size))
            # fuzzySign rotates string at position 60
            if sign_key and len(sign_key) >= 60:
                combined = sign_key + str(start_val) + str(size_val)
                fuzzy = combined[60:] + combined[:60]  # fuzzySign
                sign_val = hashlib.sha256(fuzzy.encode('utf-8')).hexdigest()

            if book_id and sign_key and sign_val:
                ajax_url = urljoin(novel_url, '/book/index')
                params = {
                    'bookId': book_id,
                    'start': start_val,
                    'size': size_val,
                    'signKey': sign_key,
                    'sign': sign_val
                }

                try:
                    r = requests.get(ajax_url, headers=HEADERS, params=params, timeout=10)
                    if r.status_code == 200 and r.text:
                        s2 = BeautifulSoup(r.text, 'html.parser')
                        new_tags = s2.select('li.chapter-name a.truncate') or s2.select('a.chapter-name')
                        if new_tags:
                            chapter_tags = new_tags
                except Exception:
                    pass

    # Final fallback: render the page with a headless browser (Selenium) and extract DOM
    if needs_more_fallback and len(chapter_tags) <= 1:
        try:
            # lazy import selenium to avoid hard dependency if not needed
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager

            opts = Options()
            try:
                opts.add_argument('--headless=new')
            except Exception:
                opts.add_argument('--headless')
            opts.add_argument('--no-sandbox')
            opts.add_argument('--disable-dev-shm-usage')
            opts.add_argument('--disable-gpu')

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
            try:
                driver.get(novel_url)
                try:
                    WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'li.chapter-name')))
                except Exception:
                    _time.sleep(1)
                html = driver.page_source
                s3 = BeautifulSoup(html, 'html.parser')
                found = s3.select('li.chapter-name a.truncate') or s3.select('a.chapter-name')
                chapter_tags = found or chapter_tags
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass
        except Exception:
            pass

    chapters = []
    seen = set()
    for a in chapter_tags:
        href = a.get('href')
        if not href:
            continue
        full = urljoin(novel_url, href)
        if full in seen:
            continue
        seen.add(full)
        title = a.get_text(strip=True) or full
        chapters.append({'title': title, 'url': full})

    return chapters


def download_chapters(chapters, progress_callback=None, stop_event=None, output_path=None):
    """Download a list of chapters (each {'title','url'}) into a single HTML file.

    Returns output_path or None.
    """
    def log(msg):
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception:
                pass
        else:
            print(msg)

    if not chapters:
        log("⚠️ Danh sách chương rỗng.")
        return None

    # attempt to get book title from first chapter page
    raw_name = chapters[0].get('title', 'Truyen')
    try:
        r = requests.get(chapters[0]['url'], headers=HEADERS, timeout=10)
        r.raise_for_status()
        s = BeautifulSoup(r.text, 'html.parser')
        bt = s.find('p', class_='book-title')
        if bt:
            raw_name = bt.get_text(strip=True)
    except Exception:
        pass

    clean_name = clean_filename(raw_name)
    if not output_path:
        output_path = f"./truyen/{clean_name}.html"

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"<html><head><meta charset='utf-8'><title>{raw_name}</title></head><body>\n")
        f.write(f"<h1>{raw_name}</h1>\n")

    total = len(chapters)
    for idx, ch in enumerate(chapters, start=1):
        if stop_event and stop_event.is_set():
            log('⏹️ Đã hủy bởi người dùng.')
            break
        try:
            log(f"🔄 Đang tải chương {idx}/{total}: {ch.get('title')}")
            resp = requests.get(ch['url'], headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                log(f"❌ Lỗi tải chương (Code {resp.status_code}): {ch['url']}")
                continue
            soup = BeautifulSoup(resp.text, 'html.parser')
            chap_title_tag = soup.find('a', class_='chapter-name') or soup.find(['h1','h2','h3'])
            chap_title = chap_title_tag.get_text(strip=True) if chap_title_tag else ch.get('title')

            content_div = soup.find('div', id='bookContentBody') or soup.find('div', class_='chapter-content') or soup.find('div', class_='entry-content')
            content_html = content_div.decode_contents() if content_div else '<p>(Không tìm thấy nội dung)</p>'

            with open(output_path, 'a', encoding='utf-8') as f:
                f.write(f"<h2>{chap_title}</h2>\n")
                f.write(content_html)
                f.write('\n<hr/>\n')

            time.sleep(random.uniform(1.5, 3.0))
        except Exception as e:
            log(f"❌ Lỗi khi tải/chèn chương: {e}")
            continue

    with open(output_path, 'a', encoding='utf-8') as f:
        f.write('</body></html>')
    log(f"🎉 XONG! Truyện đã lưu tại: {output_path}")
    return output_path


def download_chapters_epub(chapters, progress_callback=None, stop_event=None, output_path=None):
    """Download chapters and create EPUB file with proper chapter structure for Kindle.
    
    Each chapter becomes a separate section in the EPUB with Table of Contents.
    """
    from ebooklib import epub
    
    def log(msg):
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception:
                pass
        else:
            print(msg)

    if not chapters:
        log("⚠️ Danh sách chương rỗng.")
        return None

    # Get book title from first chapter page
    raw_name = chapters[0].get('title', 'Truyen')
    try:
        r = requests.get(chapters[0]['url'], headers=HEADERS, timeout=10)
        r.raise_for_status()
        s = BeautifulSoup(r.text, 'html.parser')
        bt = s.find('p', class_='book-title')
        if bt:
            raw_name = bt.get_text(strip=True)
    except Exception:
        pass

    clean_name = clean_filename(raw_name)
    if not output_path:
        output_path = f"./truyen/{clean_name}.epub"
    
    # Ensure .epub extension
    if not output_path.endswith('.epub'):
        output_path = output_path.rsplit('.', 1)[0] + '.epub'

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # Create EPUB book
    book = epub.EpubBook()
    book.set_identifier(f'id_{clean_name}_{random.randint(1000,9999)}')
    book.set_title(raw_name)
    book.set_language('vi')
    book.add_author('Truyện Wiki Dịch')

    # CSS for chapters
    style = '''
    body { font-family: Georgia, serif; line-height: 1.6; margin: 1em; }
    h1, h2 { text-align: center; margin-bottom: 1em; }
    p { text-indent: 1.5em; margin: 0.5em 0; }
    '''
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)

    epub_chapters = []
    toc = []
    spine = ['nav']

    total = len(chapters)
    for idx, ch in enumerate(chapters, start=1):
        if stop_event and stop_event.is_set():
            log('⏹️ Đã hủy bởi người dùng.')
            break
        try:
            log(f"🔄 Đang tải chương {idx}/{total}: {ch.get('title')}")
            resp = requests.get(ch['url'], headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                log(f"❌ Lỗi tải chương (Code {resp.status_code}): {ch['url']}")
                continue
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            chap_title_tag = soup.find('a', class_='chapter-name') or soup.find(['h1','h2','h3'])
            chap_title = chap_title_tag.get_text(strip=True) if chap_title_tag else ch.get('title')

            content_div = soup.find('div', id='bookContentBody') or soup.find('div', class_='chapter-content') or soup.find('div', class_='entry-content')
            
            # Clean content - keep only text paragraphs
            if content_div:
                # Remove scripts, styles
                for tag in content_div.find_all(['script', 'style', 'iframe']):
                    tag.decompose()
                content_html = content_div.decode_contents()
            else:
                content_html = '<p>(Không tìm thấy nội dung)</p>'

            # Create EPUB chapter
            chapter_file = epub.EpubHtml(title=chap_title, file_name=f'chap_{idx:04d}.xhtml', lang='vi')
            chapter_file.content = f'''
            <html xmlns="http://www.w3.org/1999/xhtml">
            <head><title>{chap_title}</title></head>
            <body>
                <h2>{chap_title}</h2>
                {content_html}
            </body>
            </html>
            '''
            chapter_file.add_item(nav_css)
            
            book.add_item(chapter_file)
            epub_chapters.append(chapter_file)
            toc.append(epub.Link(f'chap_{idx:04d}.xhtml', chap_title, f'chap_{idx}'))
            spine.append(chapter_file)

            time.sleep(random.uniform(1.5, 3.0))
        except Exception as e:
            log(f"❌ Lỗi khi tải chương: {e}")
            continue

    # Create Table of Contents
    book.toc = toc
    
    # Add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Set spine (reading order)
    book.spine = spine

    # Write EPUB file
    epub.write_epub(output_path, book, {})
    
    log(f"🎉 XONG! EPUB đã lưu tại: {output_path}")
    log(f"📚 Tổng số chương: {len(epub_chapters)}")
    log(f"💡 File EPUB này có mục lục, Kindle sẽ hiển thị từng chương riêng biệt!")
    return output_path


def download_novel(start_url, progress_callback=None, stop_event=None):
    """Download the novel starting from start_url.

    progress_callback: optional function(message: str) called for each log line.
    """
    def log(msg):
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception:
                pass
        else:
            print(msg)

    current_url = start_url
    chapter_count = 0
    output_filename = None 
    
    log(f"🚀 Đang kết nối tới: {current_url}")

    while current_url:
        if stop_event and stop_event.is_set():
            log("⏹️ Đã hủy bởi người dùng.")
            break
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
                    output_filename = f"./truyen/{clean_name}.html"
                    log(f"📖 Phát hiện tên truyện: {raw_name}")
                    log(f"💾 Sẽ lưu vào file: {output_filename}")
                else:
                    raw_name = "Truyen Wikidich"
                    output_filename = "Truyen_Wikidich.html"
                    log("⚠️ Không tìm thấy tên truyện, dùng tên mặc định.")

                with open(output_filename, "w", encoding="utf-8") as f:
                    f.write(f"<html><head><meta charset='utf-8'><title>{raw_name}</title></head><body>\n")
                    f.write(f"<h1 style='text-align:center; color:blue;'>{raw_name}</h1>\n")

            chap_tag = soup.find('a', class_='chapter-name')
            if not chap_tag:
                 chap_tag = soup.find('p', class_='book-title', style=lambda v: v and '1.2rem' in v)
            
            chapter_title = chap_tag.get_text(strip=True) if chap_tag else f"Chương {chapter_count + 1}"

            content_div = soup.find('div', id='bookContentBody')
            
            if content_div:
                with open(output_filename, "a", encoding="utf-8") as f:
                    f.write(f"<h2>{chapter_title}</h2>\n")
                    for p in content_div.find_all('p'):
                        f.write(f"<p>{p.get_text()}</p>\n")
                    f.write("<hr/>\n")
                
                log(f"✅ Đã tải: {chapter_title}")
                chapter_count += 1
            else:
                log(f"⚠️ Không lấy được nội dung chương này: {current_url}")

            # Find next chapter button - try multiple selectors for different sites
            # wikicv.net uses: a.btn-bot (the ">" button)
            # truyenwikidich.net uses: a#btnNextChapter
            next_btn = soup.find('a', id='btnNextChapter')
            
            if not next_btn:
                # wikicv.net: find the second btn-bot (first is "Mục lục", second is ">")
                btn_bots = soup.select('a.btn-bot')
                for btn in btn_bots:
                    # Look for the ">" button (next chapter)
                    icon = btn.find('i', class_='fa-angle-right')
                    if icon:
                        next_btn = btn
                        break
                # If still not found, try the last btn-bot (often the next button)
                if not next_btn and len(btn_bots) >= 2:
                    next_btn = btn_bots[-1]

            if next_btn and 'href' in next_btn.attrs:
                next_link = next_btn['href']
                if "javascript" in next_link or not next_link:
                    log("🏁 Đã đến chương cuối.")
                    break
                # Use the correct base URL based on current URL
                current_url = urljoin(current_url, next_link)
            else:
                log("🏁 Không thấy nút chương sau. Kết thúc.")
                break

            sleep_time = random.uniform(2, 4)
            if stop_event and stop_event.is_set():
                log("⏹️ Đã hủy bởi người dùng.")
                break
            time.sleep(sleep_time)

        except Exception as e:
            log(f"❌ Lỗi: {e}")
            break

    if output_filename:
        with open(output_filename, "a", encoding="utf-8") as f:
            f.write("</body></html>")
        log(f"\n🎉 XONG! Truyện đã lưu tại: {output_filename}")

if __name__ == "__main__":
    download_novel(START_URL)