import requests
from bs4 import BeautifulSoup
import hashlib
import threading
import time
import logging
import os
from flask import Flask, jsonify

# Suppress all logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

app = Flask(__name__)

# Configuration from environment variables
USERNAME = os.environ.get('PORTAL_USERNAME', '3202')
PASSWORD = os.environ.get('PORTAL_PASSWORD', 'xoxo')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8956255769:AAFOd4Opa2-v3WFdaVJCERP1U5fjL4LrLKQ')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-1003909386800')  # Supergroup with -100 prefix

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
    
    def submit_form_and_get_table2(self, form, form_action, form_method, form_data):
        try:
            if form_action:
                if form_action.startswith('/'):
                    submit_url = f"{self.base_url}{form_action}"
                elif form_action.startswith('http'):
                    submit_url = form_action
                else:
                    submit_url = f"{self.base_url}/{form_action}"
            else:
                submit_url = f"{self.base_url}/index.php?opt=shw_sum"
            
            if form_method == 'POST':
                response = self.session.post(submit_url, data=form_data, timeout=30)
            else:
                response = self.session.get(submit_url, params=form_data, timeout=30)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
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
                    
                    messages.append({
                        'hash': message_hash,
                        'date_time': date_time,
                        'range': range_name,
                        'country': country,
                        'sender': sender,
                        'receiver': receiver,
                        'message': message_body
                    })
            return messages
        except:
            return []
    
    def get_all_forms_and_submit(self, html_content):
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        forms = soup.find_all('form')
        
        if not forms:
            return []
        
        all_messages = []
        
        for form in forms:
            form_action = form.get('action', '')
            form_method = form.get('method', 'POST').upper()
            
            base_form_data = {}
            for inp in form.find_all('input', type='hidden'):
                name = inp.get('name')
                value = inp.get('value', '')
                if name:
                    base_form_data[name] = value
            
            selects = form.find_all('select')
            
            if selects:
                for select in selects:
                    select_name = select.get('name')
                    if select_name:
                        options = select.find_all('option')
                        for option in options:
                            opt_value = option.get('value', '')
                            if opt_value:
                                form_data = base_form_data.copy()
                                form_data[select_name] = opt_value
                                
                                submit_btn = form.find(['button', 'input'], type='submit')
                                if submit_btn:
                                    btn_name = submit_btn.get('name')
                                    btn_value = submit_btn.get('value', 'Submit')
                                    if btn_name:
                                        form_data[btn_name] = btn_value
                                
                                messages = self.submit_form_and_get_table2(
                                    form, form_action, form_method, form_data
                                )
                                all_messages.extend(messages)
            else:
                submit_btn = form.find(['button', 'input'], type='submit')
                if submit_btn:
                    btn_name = submit_btn.get('name')
                    btn_value = submit_btn.get('value', 'Submit')
                    if btn_name:
                        base_form_data[btn_name] = btn_value
                
                messages = self.submit_form_and_get_table2(
                    form, form_action, form_method, base_form_data
                )
                all_messages.extend(messages)
        
        return all_messages
    
    def get_all_messages_from_all_forms(self):
        summary_url = f"{self.base_url}/index.php?opt=shw_sum"
        response = self.session.get(summary_url, timeout=30)
        
        if response.status_code != 200:
            return []
        
        all_messages = []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tables = soup.find_all('table')
        if len(tables) >= 2:
            table = tables[1]
            rows = table.find_all('tr')
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
                    
                    all_messages.append({
                        'hash': message_hash,
                        'date_time': date_time,
                        'range': range_name,
                        'country': country,
                        'sender': sender,
                        'receiver': receiver,
                        'message': message_body
                    })
        
        form_messages = self.get_all_forms_and_submit(response.text)
        all_messages.extend(form_messages)
        
        seen = set()
        unique_messages = []
        for msg in all_messages:
            if msg['hash'] not in seen:
                seen.add(msg['hash'])
                unique_messages.append(msg)
        
        unique_messages.sort(key=lambda x: x['date_time'], reverse=True)
        return unique_messages
    
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
    
    def send_to_telegram(self, message):
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': CHAT_ID,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            response = requests.post(url, data=payload, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def send_old_messages(self, count=5):
        all_messages = self.get_all_messages_from_all_forms()
        if not all_messages:
            return 0
        
        last_messages = all_messages[:count] if len(all_messages) >= count else all_messages
        
        sent_count = 0
        for msg in last_messages:
            formatted_msg = self.format_telegram_message(msg, is_old=True)
            if self.send_to_telegram(formatted_msg):
                sent_count += 1
                self.seen_hashes.add(msg['hash'])
            time.sleep(0.5)
        
        for msg in all_messages:
            self.seen_hashes.add(msg['hash'])
        
        return sent_count
    
    def monitor_forever(self):
        last_hash = None
        all_messages = self.get_all_messages_from_all_forms()
        if all_messages:
            last_hash = all_messages[0]['hash']
            for msg in all_messages:
                self.seen_hashes.add(msg['hash'])
        
        while self.running:
            try:
                fresh_messages = self.get_all_messages_from_all_forms()
                if fresh_messages:
                    current_hash = fresh_messages[0]['hash']
                    if current_hash != last_hash:
                        for msg in fresh_messages:
                            if msg['hash'] not in self.seen_hashes:
                                self.seen_hashes.add(msg['hash'])
                                formatted_msg = self.format_telegram_message(msg, is_old=False)
                                self.send_to_telegram(formatted_msg)
                        last_hash = current_hash
            except:
                pass

# Start monitoring in background
portal = SMSPortal(USERNAME, PASSWORD)
if portal.login():
    portal.send_old_messages(5)
    monitor_thread = threading.Thread(target=portal.monitor_forever)
    monitor_thread.daemon = True
    monitor_thread.start()

@app.route('/')
def index():
    return jsonify({
        'status': 'active',
        'service': 'SMS Monitor - All Forms',
        'developer': '@prince_ACTIVE1',
        'mode': 'zero-delay'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
