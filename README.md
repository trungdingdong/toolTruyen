# toolTruyen

Công cụ đơn giản để tải truyện từ trang truyenwikidich (lưu thành file HTML).

## Yêu cầu
- Python 3.8+
- Gói pip:
  - requests
  - beautifulsoup4
  - (Tùy chọn) lxml hoặc html5lib để cải thiện parser

Bạn có thể cài bằng:
```powershell
pip install -r .\requirements.txt
```

## Cấu hình
- Mở `main.py` và sửa `START_URL` thành link chương đầu tiên của truyện.
- HEADERS đã được cấu hình sẵn; nếu cần, chỉnh User-Agent hoặc Referer.

## Cách chạy (Windows)
```powershell
python .\main.py
```

Kết quả: một file `.html` sẽ được tạo trong thư mục dự án chứa tiêu đề và các chương đã tải.

## Lưu ý
- Tôn trọng điều khoản sử dụng của trang web khi tải nội dung.
- Nếu trang thay đổi cấu trúc HTML, có thể cần chỉnh lại các selector