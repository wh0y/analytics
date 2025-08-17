from flask import Flask, jsonify, request, abort
from datetime import datetime
import sqlite3
import os
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_cors import CORS

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
CORS(app, resources={
    r"/track-view": {"origins": ["https://2xwh.pages.dev"]},
    r"/get-*": {"origins": ["https://2xwh.pages.dev"]}
})

GA_MEASUREMENT_ID = os.getenv('GA_MEASUREMENT_ID')
GA_API_SECRET = os.getenv('GA_API_SECRET')

def init_db():
    db_path = os.path.join(os.path.dirname(__file__), 'views.db')
    with sqlite3.connect(db_path) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS views (
                ip TEXT,
                user_agent TEXT,
                date TEXT,
                UNIQUE(ip, user_agent, date)
            )
        ''')
        conn.commit()

@app.before_request
def check_db():
    db_path = os.path.join(os.path.dirname(__file__), 'views.db')
    if not os.path.exists(db_path):
        init_db()

@app.route('/track-view')
def track_view():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    user_agent = request.headers.get('User-Agent', 'unknown')
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        db_path = os.path.join(os.path.dirname(__file__), 'views.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO views (ip, user_agent, date) VALUES (?, ?, ?)",
                (client_ip, user_agent, today)
            )
            conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get-total-views')
def get_total_views():
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'views.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM views WHERE date = ?", 
                         (datetime.now().strftime("%Y-%m-%d"),))
            total_views = cursor.fetchone()[0]
        return jsonify({"total_views": total_views})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get-ga-config')
def get_ga_config():
    if request.headers.get('Origin') != 'https://2xwh.pages.dev':
        abort(403)
    return jsonify({
        "measurement_id": GA_MEASUREMENT_ID,
        "api_secret": GA_API_SECRET
    })

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
