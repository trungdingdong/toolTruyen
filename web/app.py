import os
import sys
import threading
import uuid
from queue import Queue, Empty
from flask import Flask, render_template, request, jsonify

# Ensure project root (parent of web/) is on sys.path so we can import main.py
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# import the downloader from main
from main import download_novel, get_chapter_list, download_chapters

app = Flask(__name__)

# job store: job_id -> {thread, queue, stop_event}
jobs = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    data = request.get_json() or {}
    url = data.get('url')
    start_idx = data.get('start')  # 1-based
    end_idx = data.get('end')      # 1-based
    if not url:
        return jsonify({'error': 'missing url'}), 400

    job_id = str(uuid.uuid4())
    q = Queue()
    stop_event = threading.Event()

    def progress(msg):
        q.put(msg)

    def worker():
        try:
            # Lấy danh sách chương toàn bộ từ trang truyện
            chap_list = get_chapter_list(url)
            if not chap_list:
                q.put("⚠️ Không tìm thấy chương nào.")
                q.put('__DONE__')
                return

            # normalize indices
            total = len(chap_list)
            s = int(start_idx) if start_idx else 1
            e = int(end_idx) if end_idx else total
            s = max(1, s)
            e = min(total, e)
            if s > e:
                q.put("⚠️ Khoảng chương không hợp lệ.")
                q.put('__DONE__')
                return

            slice_list = chap_list[s-1:e]  # zero-based slice
            q.put(f"ℹ️ Tải từ chương {s} đến {e} (tổng {total}).")
            # gọi hàm download_chapters để tải danh sách
            output = download_chapters(slice_list, progress_callback=progress, stop_event=stop_event)
            q.put(f"🔚 Kết thúc. File: {output}" if output else "🔚 Kết thúc.")
        except Exception as ex:
            q.put(f"❌ Lỗi khi bắt đầu download: {ex}")
        finally:
            q.put('__DONE__')

    t = threading.Thread(target=worker, daemon=True)
    jobs[job_id] = {'thread': t, 'queue': q, 'stop': stop_event}
    t.start()
    return jsonify({'job_id': job_id})


@app.route('/chapters', methods=['POST'])
def chapters():
    data = request.get_json() or {}
    url = data.get('url')
    if not url:
        return jsonify({'error': 'missing url'}), 400
    try:
        chap_list = get_chapter_list(url)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    for i, c in enumerate(chap_list, start=1):
        c['index'] = i
    return jsonify({'chapters': chap_list, 'total': len(chap_list)})

@app.route('/logs')
def logs():
    job_id = request.args.get('job')
    if not job_id or job_id not in jobs:
        return jsonify({'error': 'unknown job'}), 404
    q = jobs[job_id]['queue']
    items = []
    try:
        while True:
            items.append(q.get_nowait())
    except Exception:
        pass
    return jsonify({'logs': items})

@app.route('/stop', methods=['POST'])
def stop():
    data = request.get_json() or {}
    job_id = data.get('job')
    if not job_id or job_id not in jobs:
        return jsonify({'error': 'unknown job'}), 404
    jobs[job_id]['stop'].set()
    return jsonify({'stopped': True})

if __name__ == '__main__':
    app.run(debug=True)
