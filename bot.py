import requests
from bs4 import BeautifulSoup
import hashlib
import threading
import logging
from flask import Flask, jsonify
import os
import select
import socket

# Suppress all logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

app = Flask(__name__)

# Configuration from environment variables
USERNAME = os.environ.get('PORTAL_USERNAME', '9339236')
PASSWORD = os.environ.get('PORTAL_PASSWORD', 'GENESYS123')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7783590119:AAGScPFVEreH-fvwSQNTuamGlFOGI-VDK7w')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-1003481016140')

class SMSPortal:
    def __init__(self, username, password):
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.base_url = "https://mysmsportal.com"
        self.seen_hashes = set()
        self.running = True
        
    def login(self):
        try:
            login_url = f"{self.base_url}/index.php?login=1"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            login_data = {'user': self.username, 'password': self.password}
            self.session.headers.update(headers)
            response = self.session.post(login_url, data=login_data, timeout=30)
            return "User name and password needed" not in response.text
        except:
            return False
    
    def fetch_messages(self):
        try:
            summary_url = f"{self.base_url}/index.php?opt=shw_sum"
            response = self.session.get(summary_url, timeout=30)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form')
            
            if not form:
                tables = soup.find_all('table')
                if len(tables) >= 2:
                    return response.text
                return None
            
            form_data = {}
            for hidden in form.find_all('input', type='hidden'):
                name = hidden.get('name')
                value = hidden.get('value')
                if name and value:
                    form_data[name] = value
            
            selects = form.find_all('select')
            for select in selects:
                select_name = select.get('name')
                if select_name:
                    first_option = select.find('option')
                    if first_option:
                        form_data[select_name] = first_option.get('value', '')
            
            form_data['opt'] = 'shw_sum'
            result_response = self.session.post(summary_url, data=form_data, timeout=30)
            if result_response.status_code == 200:
                return result_response.text
            
            return response.text
        except:
            return None
    
    def get_all_messages(self, html_content):
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = soup.find_all('table')
        
        if len(tables) < 2:
            return []
        
        table = tables[1]
        rows = table.find_all('tr')
        messages = []
        
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) >= 5:
                date_time = cells[0].get_text(strip=True)
                range_name = cells[1].get_text(strip=True)
                sender = cells[2].get_text(strip=True)
                receiver = cells[3].get_text(strip=True)
                message_body = cells[4].get_text(strip=True)
                country = range_name.split('-')[0].strip() if '-' in range_name else "Unknown"
                message_string = f"{date_time}_{receiver}_{message_body}"
                message_hash = hashlib.md5(message_string.encode()).hexdigest()
                
                messages.insert(0, {
                    'hash': message_hash,
                    'date_time': date_time,
                    'range': range_name,
                    'country': country,
                    'sender': sender,
                    'receiver': receiver,
                    'message': message_body
                })
        
        return messages
    
    def format_telegram_message(self, message, is_old=False):
        prefix = "📜 OLD MESSAGE" if is_old else "📨 New SMS Received 🏳️"
        return f"""{prefix}
━━━━━━━━━━━━━━━━━━━━━━
🌍 Country: 🏳️ {message['country']}
📱 Number: {message['receiver']}
📌 Sender: ❓ {message['sender']}
📅 Date/Time: {message['date_time']}
🌐 Range: {message['range']}
━━━━━━━━━━━━━━━━━━━━━━
💬 Message:
{message['message']}
━━━━━━━━━━━━━━━━━━━━━━
Panel - Mediatel

<a href="https://t.me/prince_ACTIVE1">👨‍💻 Developer</a>"""
    
    def send_to_telegram(self, message_text):
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': CHAT_ID,
                'text': message_text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            response = requests.post(url, data=payload, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def monitor_continuous(self):
        """Continuous monitoring - NO SLEEP, always checking"""
        if not self.login():
            return
        
        # Send last 5 messages first
        html_content = self.fetch_messages()
        if html_content:
            all_messages = self.get_all_messages(html_content)
            if all_messages:
                last_5 = all_messages[:5] if len(all_messages) >= 5 else all_messages
                for msg in reversed(last_5):
                    if msg['hash'] not in self.seen_hashes:
                        formatted = self.format_telegram_message(msg, is_old=True)
                        self.send_to_telegram(formatted)
                        self.seen_hashes.add(msg['hash'])
        
        # Get initial hash
        last_hash = None
        html_content = self.fetch_messages()
        if html_content:
            all_messages = self.get_all_messages(html_content)
            if all_messages:
                last_hash = all_messages[0]['hash']
                for msg in all_messages:
                    self.seen_hashes.add(msg['hash'])
        
        # Continuous loop - NO SLEEP
        while self.running:
            try:
                html_content = self.fetch_messages()
                if html_content:
                    all_messages = self.get_all_messages(html_content)
                    if all_messages:
                        current_hash = all_messages[0]['hash']
                        if current_hash != last_hash:
                            for msg in all_messages:
                                if msg['hash'] not in self.seen_hashes:
                                    self.seen_hashes.add(msg['hash'])
                                    formatted = self.format_telegram_message(msg, is_old=False)
                                    self.send_to_telegram(formatted)
                            last_hash = current_hash
            except:
                pass  # Silent fail, continue immediately

# Start monitoring in background thread
portal = SMSPortal(USERNAME, PASSWORD)
monitor_thread = threading.Thread(target=portal.monitor_continuous)
monitor_thread.daemon = True
monitor_thread.start()

@app.route('/')
def index():
    return jsonify({
        'status': 'active',
        'message': 'SMS Monitor - Zero Delay Mode',
        'developer': '@prince_ACTIVE1'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'mode': 'continuous'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)
