#!/usr/bin/env python3
"""
Daily Clock-in Tool
A local web server that tracks daily attendance and syncs to GitHub
"""

import os
import re
import subprocess
from datetime import datetime, date
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
import calendar
import webbrowser
import time
import threading

# Global configuration
AUTO_CLOCK_IN_MODE = True  # Set to True for auto clock-in, False for manual
SERVER_PORT = 7979  # Configure the desired server port here

class ClockInHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            if AUTO_CLOCK_IN_MODE:
                self.handle_auto_clock_in()
            else:
                self.serve_main_page()
        elif parsed_path.path == '/api/clock-in':
            self.handle_clock_in()
        elif parsed_path.path == '/api/status':
            self.check_status()
        else:
            self.send_error(404)
    
    def serve_main_page(self):
        """Serve the main HTML page"""
        html_content = self.get_html_page()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def handle_auto_clock_in(self):
        """Handle automatic clock-in when mode is enabled"""
        today = date.today()
        today_str = today.strftime('%Y-%m-%d')
        
        if self.is_already_clocked_in(today_str):
            response = {
                'success': False,
                'message': 'You have already clocked in today! 🎉',
                'already_checked': True
            }
        else:
            try:
                self.add_attendance_record(today)
                self.commit_and_push(today)
                response = {
                    'success': True,
                    'message': 'Successfully clocked in! ✅',
                    'date': today_str
                }
            except Exception as e:
                response = {
                    'success': False,
                    'message': f'Error during clock-in: {str(e)}',
                    'error': True
                }
        
        # Serve modified HTML with immediate success message
        html_content = self.get_html_page(response)
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def handle_clock_in(self):
        """Handle manual clock-in request"""
        today = date.today()
        today_str = today.strftime('%Y-%m-%d')
        
        if self.is_already_clocked_in(today_str):
            response = {
                'success': False,
                'message': 'You have already clocked in today! 🎉',
                'already_checked': True
            }
        else:
            try:
                self.add_attendance_record(today)
                self.commit_and_push(today)
                response = {
                    'success': True,
                    'message': 'Successfully clocked in! ✅',
                    'date': today_str
                }
            except Exception as e:
                response = {
                    'success': False,
                    'message': f'Error during clock-in: {str(e)}',
                    'error': True
                }
        
        self.send_json_response(response)
    
    def check_status(self):
        """Check if user has already clocked in today"""
        today_str = date.today().strftime('%Y-%m-%d')
        already_clocked = self.is_already_clocked_in(today_str)
        
        response = {
            'already_clocked': already_clocked,
            'date': today_str
        }
        
        self.send_json_response(response)
    
    def is_already_clocked_in(self, date_str):
        """Check if attendance is already recorded for given date"""
        if not os.path.exists('README.md'):
            return False
        
        try:
            with open('README.md', 'r', encoding='utf-8') as f:
                content = f.read()
                return date_str in content
        except:
            return False
    
    def add_attendance_record(self, today):
        """Add attendance record to README.md"""
        readme_content = self.generate_readme_content(today)
        
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def generate_readme_content(self, today):
        """Generate README.md content with calendar view"""
        existing_dates = set()
        if os.path.exists('README.md'):
            try:
                with open('README.md', 'r', encoding='utf-8') as f:
                    content = f.read()
                    date_pattern = r'(\d{4}-\d{2}-\d{2})'
                    existing_dates = set(re.findall(date_pattern, content))
            except:
                pass
        
        today_str = today.strftime('%Y-%m-%d')
        existing_dates.add(today_str)
        
        current_year = today.year
        current_month = today.month
        
        readme_content = f"""# Daily Clock-in Calendar 📅

## {calendar.month_name[current_month]} {current_year}

"""
        
        cal = calendar.monthcalendar(current_year, current_month)
        readme_content += "| Mon | Tue | Wed | Thu | Fri | Sat | Sun |\n"
        readme_content += "|-----|-----|-----|-----|-----|-----|-----|\n"
        
        for week in cal:
            week_row = "|"
            for day in week:
                if day == 0:
                    week_row += "     |"
                else:
                    day_str = f"{current_year}-{current_month:02d}-{day:02d}"
                    if day_str in existing_dates:
                        week_row += f"  ✅{day:2d} |"
                    else:
                        week_row += f"   {day:2d} |"
            readme_content += week_row + "\n"
        
        readme_content += f"\n## Clock-in Records\n\n"
        
        sorted_dates = sorted(existing_dates, reverse=True)
        for date_str in sorted_dates[:30]:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                day_name = date_obj.strftime('%A')
                formatted_date = date_obj.strftime('%B %d, %Y')
                readme_content += f"- ✅ **{formatted_date}** ({day_name})\n"
            except:
                readme_content += f"- ✅ {date_str}\n"
        
        readme_content += f"\n---\n\n**Total Days Clocked In:** {len(existing_dates)} days\n"
        readme_content += f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return readme_content
    
    def commit_and_push(self, today):
        """Commit and push changes to GitHub"""
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        commit_message = f'checked in: {timestamp}'
        
        try:
            subprocess.run(['git', 'add', '.'], check=True, cwd='.')
            subprocess.run(['git', 'commit', '-m', commit_message], check=True, cwd='.')
            subprocess.run(['git', 'push', '-u', 'origin', 'master'], check=True, cwd='.')
        except subprocess.CalledProcessError as e:
            if 'push' in str(e):
                try:
                    subprocess.run(['git', 'push', '-u', 'origin', 'main'], check=True, cwd='.')
                except subprocess.CalledProcessError:
                    raise Exception(f"Failed to push to both 'master' and 'main' branches: {e}")
            else:
                raise Exception(f"Git operation failed: {e}")
    
    def send_json_response(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def get_html_page(self, auto_response=None):
        """Generate the HTML page with optional auto clock-in response"""
        message_class = ''
        message_text = ''
        button_disabled = ''
        button_text = 'Clock In Today'
        
        if auto_response:
            if auto_response.get('success'):
                message_class = 'success show'
                message_text = auto_response['message']
                button_text = 'Successfully Clocked In! ✅'
                button_disabled = 'disabled'
            elif auto_response.get('already_checked'):
                message_class = 'already-checked show'
                message_text = auto_response['message']
                button_text = 'Already Clocked In Today! ✅'
                button_disabled = 'disabled'
            elif auto_response.get('error'):
                message_class = 'error show'
                message_text = auto_response['message']
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Clock-in Tool</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }}
        
        .container {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            text-align: center;
            max-width: 500px;
            width: 90%;
            border: 1px solid rgba(255, 255, 255, 0.18);
        }}
        
        .header {{
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            color: #4a5568;
        }}
        
        .date-display {{
            font-size: 1.2rem;
            color: #718096;
            margin-bottom: 20px;
            font-weight: 500;
        }}
        
        .clock-in-btn {{
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 1.2rem;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4);
            font-weight: 600;
            letter-spacing: 0.5px;
        }}
        
        .clock-in-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(76, 175, 80, 0.6);
        }}
        
        .clock-in-btn:active {{
            transform: translateY(0);
        }}
        
        .clock-in-btn.already-checked {{
            background: linear-gradient(135deg, #FF9800, #F57C00);
            box-shadow: 0 4px 15px rgba(255, 152, 0, 0.4);
            cursor: not-allowed;
        }}
        
        .message {{
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            font-weight: 500;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s ease;
        }}
        
        .message.show {{
            opacity: 1;
            transform: translateY(0);
        }}
        
        .message.success {{
            background: rgba(76, 175, 80, 0.1);
            color: #388e3c;
            border: 1px solid rgba(76, 175, 80, 0.3);
        }}
        
        .message.already-checked {{
            background: rgba(255, 152, 0, 0.1);
            color: #f57c00;
            border: 1px solid rgba(255, 152, 0, 0.3);
        }}
        
        .message.error {{
            background: rgba(244, 67, 54, 0.1);
            color: #d32f2f;
            border: 1px solid rgba(244, 67, 54, 0.3);
        }}
        
        .loading {{
            display: none;
            margin-top: 20px;
        }}
        
        .loading.show {{
            display: block;
        }}
        
        .spinner {{
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .footer {{
            margin-top: 30px;
            font-size: 0.9rem;
            color: #718096;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📅 Daily Clock-in</h1>
            <div class="date-display" id="dateDisplay"></div>
        </div>
        
        <button class="clock-in-btn {'' if not button_disabled else 'already-checked'}" id="clockInBtn" onclick="clockIn()" {button_disabled}>
            {button_text}
        </button>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Processing...</p>
        </div>
        
        <div class="message {message_class}" id="message">{message_text}</div>
        
        <div class="footer">
            <p>Your attendance will be automatically saved to README.md and synced to GitHub</p>
        </div>
    </div>

    <script>
        let alreadyClocked = {str('true' if auto_response and (auto_response.get('success') or auto_response.get('already_checked')) else 'false').lower()};
        
        function updateDateDisplay() {{
            const now = new Date();
            const options = {{ 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            }};
            document.getElementById('dateDisplay').textContent = now.toLocaleDateString('en-US', options);
        }}
        
        async function checkStatus() {{
            if ({str('true' if auto_response else 'false').lower()}) return;
            
            try {{
                const response = await fetch('/api/status');
                const data = await response.json();
                
                if (data.already_clocked) {{
                    alreadyClocked = true;
                    const btn = document.getElementById('clockInBtn');
                    btn.textContent = 'Already Clocked In Today! ✅';
                    btn.classList.add('already-checked');
                    btn.disabled = true;
                    showMessage('You have already clocked in today! Great job! 🎉', 'already-checked');
                }}
            }} catch (error) {{
                console.error('Error checking status:', error);
            }}
        }}
        
        async function clockIn() {{
            if (alreadyClocked) {{
                showMessage('You have already clocked in today! 🎉', 'already-checked');
                return;
            }}
            
            const btn = document.getElementById('clockInBtn');
            const loading = document.getElementById('loading');
            
            btn.disabled = true;
            loading.classList.add('show');
            hideMessage();
            
            try {{
                const response = await fetch('/api/clock-in');
                const data = await response.json();
                
                loading.classList.remove('show');
                
                if (data.success) {{
                    btn.textContent = 'Successfully Clocked In! ✅';
                    btn.classList.add('already-checked');
                    alreadyClocked = true;
                    showMessage(data.message, 'success');
                }} else if (data.already_checked) {{
                    btn.textContent = 'Already Clocked In Today! ✅';
                    btn.classList.add('already-checked');
                    alreadyClocked = true;
                    showMessage(data.message, 'already-checked');
                }} else {{
                    btn.disabled = false;
                    showMessage(data.message, 'error');
                }}
            }} catch (error) {{
                loading.classList.remove('show');
                btn.disabled = false;
                showMessage('Network error. Please try again.', 'error');
                console.error('Error:', error);
            }}
        }}
        
        function showMessage(text, type) {{
            const message = document.getElementById('message');
            message.textContent = text;
            message.className = `message ${type}`;
            setTimeout(() => message.classList.add('show'), 100);
        }}
        
        function hideMessage() {{
            const message = document.getElementById('message');
            message.classList.remove('show');
        }}
        
        updateDateDisplay();
        checkStatus();
        setInterval(updateDateDisplay, 60000);
    </script>
</body>
</html>"""

    def log_message(self, format, *args):
        """Override to customize log messages"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")

def get_local_ip():
    """Get the local IP address for network access"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        return "127.0.0.1"

def is_safe_port(port):
    """Check if port is in safe range (avoid system/privileged ports)"""
    unsafe_ports = set(range(0, 1024))
    unsafe_ports.update([1433, 1521, 3389, 5432, 6379, 27017])
    return port not in unsafe_ports

def find_safe_port(start_port=SERVER_PORT):
    """Find a safe, available port starting from start_port"""
    import socket
    
    for port in range(start_port, start_port + 100):
        if not is_safe_port(port):
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise Exception("No safe ports available in range")

def open_browser():
    """Open browser after a short delay if manual mode"""
    if not AUTO_CLOCK_IN_MODE:
        time.sleep(1)
        local_ip = get_local_ip()
        webbrowser.open(f'http://{local_ip}:{SERVER_PORT}')

def main():
    """Main function to start the server"""
    global SERVER_PORT
    
    print("🚀 Starting Daily Clock-in Server...")
    
    try:
        SERVER_PORT = find_safe_port(SERVER_PORT)
        print(f"🔒 Using safe port: {SERVER_PORT}")
    except Exception as e:
        print(f"❌ Error finding safe port: {e}")
        print(f"🔄 Falling back to port {SERVER_PORT}")
    
    if not os.path.exists('.git'):
        print("⚠️  Warning: Not in a Git repository. Git operations may fail.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Exiting...")
            return
    
    local_ip = get_local_ip()
    server_address = ('0.0.0.0', SERVER_PORT)
    httpd = HTTPServer(server_address, ClockInHandler)
    
    print(f"📡 Server running on all interfaces")
    print(f"🏠 Local access: http://localhost:{SERVER_PORT}")
    print(f"📱 Network access: http://{local_ip}:{SERVER_PORT}")
    print("🌐 Opening browser..." if not AUTO_CLOCK_IN_MODE else "📝 Auto clock-in enabled")
    print("📝 Clock-in data will be saved to README.md")
    print("🔄 Changes will be automatically committed and pushed to GitHub")
    print("\n" + "="*60)
    print("📱 MOBILE/NETWORK ACCESS:")
    print(f"   Access URL: http://{local_ip}:{SERVER_PORT}")
    print(f"   Mode: {'🔄 AUTO CLOCK-IN' if AUTO_CLOCK_IN_MODE else '👆 MANUAL CLICK'}")
    if AUTO_CLOCK_IN_MODE:
        print("   📝 Note: Auto clock-in will occur on page visit")
    print("="*60)
    print(f"\n💡 To change mode: Edit AUTO_CLOCK_IN_MODE = {AUTO_CLOCK_IN_MODE} at top of script")
    print(f"💡 To change port: Edit SERVER_PORT = {SERVER_PORT} at top of script")
    print("Press Ctrl+C to stop the server")
    
    if not AUTO_CLOCK_IN_MODE:
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down server...")
        httpd.shutdown()

if __name__ == '__main__':
    main()