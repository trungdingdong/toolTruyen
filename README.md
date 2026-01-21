# toolTruyen

Công cụ tải truyện từ **truyenwikidich.net** (lưu thành file HTML).

## Tính năng

- **Web UI**: Giao diện web đơn giản để tải truyện
- **Tự động lấy danh sách chương**: Chỉ cần paste URL trang truyện, tool sẽ tự động lấy tất cả các chương
- **Chọn khoảng chương**: Có thể chọn tải từ chương X đến chương Y
- **Hỗ trợ truyenwikidich.net**: Tự động xử lý API và sign để lấy danh sách chương

## Yêu cầu

- Python 3.8+
- Các gói pip:
  - requests
  - beautifulsoup4
  - flask

Cài đặt:
```powershell
pip install -r requirements.txt
```

## Cách sử dụng

### 1. Chạy Web UI (khuyến nghị)

```powershell
python .\web\app.py
```

Mở trình duyệt tại: http://127.0.0.1:5000

**Các bước:**
1. Paste URL trang truyện (ví dụ: `https://truyenwikidich.net/truyen/ten-truyen-abc`)
2. Nhấn **Load chapters** để lấy danh sách chương
3. Chọn khoảng chương muốn tải (từ - đến)
4. Nhấn **Start** để bắt đầu tải
5. File HTML sẽ được lưu trong thư mục `./truyen/`

### 2. Chạy trực tiếp (command line)

Mở `main.py` và sửa `START_URL` thành link **chương đầu tiên** của truyện:

```python
START_URL = "https://truyenwikidich.net/truyen/ten-truyen/phan-1-xxx"
```

Sau đó chạy:
```powershell
python .\main.py
```

## Cấu trúc thư mục

```
toolTruyen/
├── main.py           # Logic chính: lấy chapters, tải nội dung
├── requirements.txt  # Dependencies
├── README.md
├── truyen/           # Thư mục chứa file truyện đã tải
└── web/
    ├── app.py        # Flask web server
    ├── templates/    # HTML templates
    └── static/       # CSS/JS files
```

## Lưu ý

- Tôn trọng điều khoản sử dụng của trang web khi tải nội dung
- Tool có delay giữa các request để tránh bị block
- Nếu trang thay đổi cấu trúc HTML/API, có thể cần cập nhật code