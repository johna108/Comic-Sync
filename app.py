from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import threading
import time
import base64
import uuid
from datetime import datetime
import os
import queue
import subprocess
import sys
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configure CORS
CORS(app, origins="*")

# Initialize SocketIO with optimized settings
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',
    ping_timeout=10,
    ping_interval=5,
    logger=False,
    engineio_logger=False
)

# Store room data and browser instances
rooms_data = {}
user_sessions = {}
browser_instances = {}

class VirtualBrowser:
    def __init__(self, room_code, url):
        self.room_code = room_code
        self.url = url
        self.is_running = False
        self.current_screenshot = None
        self.scroll_position = {'x': 0, 'y': 0}
        self.command_queue = queue.Queue()
        self.last_screenshot_time = 0
        
    def start(self):
        """Start the virtual browser using selenium (more reliable)"""
        try:
            print(f"🚀 Starting virtual browser for room {self.room_code}")
            
            # Try to import selenium
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
            except ImportError:
                print("❌ Selenium not installed. Installing...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium", "webdriver-manager"])
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
            
            # Setup Chrome options for maximum performance
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Faster loading
            chrome_options.add_argument('--disable-javascript')  # Remove if JS needed
            chrome_options.add_argument('--window-size=1280,720')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            
            # Try to use webdriver-manager for automatic driver management
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except:
                # Fallback to system chromedriver
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # Set timeouts for faster responses
            self.driver.set_page_load_timeout(10)
            self.driver.implicitly_wait(1)
            
            print(f"📄 Loading URL: {self.url}")
            self.driver.get(self.url)
            
            # Minimal wait for page load
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except:
                pass  # Continue even if page isn't fully loaded
            
            self.is_running = True
            print(f"✅ Virtual browser ready for room {self.room_code}")
            
            # Notify users that browser is ready
            socketio.emit('browser-ready', {'success': True}, room=self.room_code)
            
            # Start screenshot capture with high frequency
            screenshot_thread = threading.Thread(target=self.screenshot_loop, daemon=True)
            screenshot_thread.start()
            
            # Start command processor with high priority
            command_thread = threading.Thread(target=self.process_commands, daemon=True)
            command_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ Error starting virtual browser: {str(e)}")
            socketio.emit('browser-error', {'error': str(e)}, room=self.room_code)
            return False
    
    def screenshot_loop(self):
        """Continuously take screenshots with minimal delay"""
        print(f"📸 Starting high-frequency screenshot loop for room {self.room_code}")
        
        while self.is_running and hasattr(self, 'driver'):
            try:
                current_time = time.time()
                
                # Take screenshot with lower quality for speed
                screenshot_b64 = self.driver.get_screenshot_as_base64()
                self.current_screenshot = screenshot_b64
                
                # Get scroll position quickly
                scroll_info = self.driver.execute_script("""
                    return {
                        x: window.pageXOffset || 0,
                        y: window.pageYOffset || 0,
                        maxX: Math.max(0, (document.documentElement.scrollWidth || 0) - window.innerWidth),
                        maxY: Math.max(0, (document.documentElement.scrollHeight || 0) - window.innerHeight),
                        pageWidth: document.documentElement.scrollWidth || 1280,
                        pageHeight: document.documentElement.scrollHeight || 720
                    };
                """)
                
                self.scroll_position = scroll_info

                # Get current URL
                try:
                    current_url = self.driver.current_url
                    if hasattr(self, 'last_url') and self.last_url != current_url:
                        # URL changed, notify users
                        socketio.emit('url-changed', {'url': current_url}, room=self.room_code)
                        if self.room_code in rooms_data:
                            rooms_data[self.room_code]['webtoon_url'] = current_url
                    self.last_url = current_url
                except:
                    current_url = self.url
                
                # Emit to all users in room immediately
                socketio.emit('screenshot-update', {
                    'screenshot': screenshot_b64,
                    'scrollPosition': scroll_info,
                    'timestamp': current_time
                }, room=self.room_code)
                
                self.last_screenshot_time = current_time
                
                # Much shorter interval for smooth updates (100ms = 10 FPS)
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Screenshot error: {str(e)}")
                time.sleep(0.1)  # Short retry delay
    
    def process_commands(self):
        """Process commands with minimal delay"""
        while self.is_running:
            try:
                # Very short timeout for immediate processing
                command = self.command_queue.get(timeout=0.1)
                
                if command['type'] == 'scroll':
                    # Immediate scroll with no delay
                    self.driver.execute_script(f"window.scrollTo({command['x']}, {command['y']})")
                    print(f"📜 Scrolled to ({command['x']}, {command['y']})")
                    
                elif command['type'] == 'click':
                    x, y = command['x'], command['y']
                    try:
                        # Fast click with immediate execution
                        self.driver.execute_script(f"""
                            var element = document.elementFromPoint({x}, {y});
                            if (element) {{
                                element.click();
                            }}
                        """)
                        print(f"🖱️ Clicked at ({x}, {y})")
                    except Exception as e:
                        print(f"❌ Click error at ({x}, {y}): {e}")
                    
                elif command['type'] == 'navigate':
                    self.driver.get(command['url'])
                    print(f"🔄 Navigated to {command['url']}")
                    
                elif command['type'] == 'key':
                    from selenium.webdriver.common.keys import Keys
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    key = command['key']
                    key_type = command['key_type']
                    
                    # Only process keydown events to avoid duplicates
                    if key_type != 'keydown':
                        continue
                    
                    # Map special keys
                    key_mapping = {
                        'Enter': Keys.ENTER,
                        'Tab': Keys.TAB,
                        'Escape': Keys.ESCAPE,
                        'Backspace': Keys.BACKSPACE,
                        'Delete': Keys.DELETE,
                        'ArrowUp': Keys.ARROW_UP,
                        'ArrowDown': Keys.ARROW_DOWN,
                        'ArrowLeft': Keys.ARROW_LEFT,
                        'ArrowRight': Keys.ARROW_RIGHT,
                        'Space': Keys.SPACE,
                        'Shift': Keys.SHIFT,
                        'Control': Keys.CONTROL,
                        'Alt': Keys.ALT,
                    }
                    
                    # Immediate key execution
                    if key in key_mapping:
                        ActionChains(self.driver).send_keys(key_mapping[key]).perform()
                    elif len(key) == 1:  # Regular character
                        ActionChains(self.driver).send_keys(key).perform()
                    
                    print(f"⌨️ Key: {key}")
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Command error: {str(e)}")
    
    def scroll_to(self, x, y):
        """Add scroll command to queue with high priority"""
        # Clear any pending scroll commands to avoid lag
        temp_queue = queue.Queue()
        while not self.command_queue.empty():
            try:
                cmd = self.command_queue.get_nowait()
                if cmd['type'] != 'scroll':  # Keep non-scroll commands
                    temp_queue.put(cmd)
            except queue.Empty:
                break
        
        # Put back non-scroll commands
        while not temp_queue.empty():
            self.command_queue.put(temp_queue.get())
        
        # Add new scroll command
        self.command_queue.put({'type': 'scroll', 'x': x, 'y': y})
    
    def click_at(self, x, y):
        """Add click command to queue"""
        self.command_queue.put({'type': 'click', 'x': x, 'y': y})
    
    def navigate_to(self, url):
        """Add navigate command to queue"""
        self.command_queue.put({'type': 'navigate', 'url': url})
    
    def send_key(self, key, key_type):
        """Add key command to queue"""
        self.command_queue.put({'type': 'key', 'key': key, 'key_type': key_type})
    
    def stop(self):
        """Stop the virtual browser"""
        self.is_running = False
        
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except:
                pass
        
        print(f"🛑 Virtual browser stopped for room {self.room_code}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/room/<room_code>')
def room_page(room_code):
    return render_template('room.html', room_code=room_code)

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'rooms': len(rooms_data),
        'active_browsers': len(browser_instances),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/room/<room_code>')
def get_room_info(room_code):
    room = rooms_data.get(room_code)
    if room:
        return jsonify({
            'roomCode': room_code,
            'userCount': len(room['users']),
            'contentUrl': room['webtoon_url'],
            'exists': True
        })
    else:
        return jsonify({'error': 'Room not found', 'exists': False}), 404

@socketio.on('connect')
def on_connect():
    print(f'👤 User connected: {request.sid}')

@socketio.on('disconnect')
def on_disconnect():
    print(f'👤 User disconnected: {request.sid}')
    if request.sid in user_sessions:
        user_data = user_sessions[request.sid]
        handle_user_leave(request.sid, user_data.get('room_code'))

@socketio.on('join-room')
def on_join_room(data):
    room_code = data['roomCode']
    user_name = data['userName']
    webtoon_url = data.get('webtoonUrl')
    is_creator = data.get('isCreator', False)
    
    print(f'👤 {user_name} joining room {room_code} (creator: {is_creator})')
    
    # Join the room
    join_room(room_code)
    
    # Store user session
    user_sessions[request.sid] = {
        'user_name': user_name,
        'room_code': room_code,
        'is_creator': is_creator
    }
    
    # Initialize room if creator
    if room_code not in rooms_data:
        if is_creator:
            # Use default URL - users can navigate using the URL bar
            default_url = 'https://www.google.com'
            print(f'🏠 Creating room {room_code} with default URL: {default_url}')
            rooms_data[room_code] = {
                'users': {},
                'messages': [],
                'webtoon_url': default_url,
                'created_at': time.time(),
                'creator': user_name
            }
            
            # Start virtual browser
            browser = VirtualBrowser(room_code, default_url)
            browser_instances[room_code] = browser
            
            # Start browser in separate thread
            def start_browser():
                success = browser.start()
                if not success:
                    # Cleanup on failure
                    if room_code in browser_instances:
                        del browser_instances[room_code]
            
            threading.Thread(target=start_browser, daemon=True).start()
            
        else:
            emit('room-not-found')
            return
    
    # Check if room exists for joiners
    if not is_creator and room_code not in rooms_data:
        emit('room-not-found')
        return
    
    room = rooms_data[room_code]
    
    # Add user to room
    room['users'][request.sid] = {
        'id': request.sid,
        'userName': user_name
    }
    
    # Send room data
    room_users = list(room['users'].values())
    emit('room-users', room_users)
    emit('webtoon-url-update', {'url': room['webtoon_url']})
    
    # Send current screenshot if available
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        if browser.current_screenshot:
            emit('screenshot-update', {
                'screenshot': browser.current_screenshot,
                'scrollPosition': browser.scroll_position,
                'timestamp': time.time()
            })
    
    # Notify others
    emit('user-joined', {'userName': user_name}, room=room_code, include_self=False)
    emit('room-users', room_users, room=room_code, include_self=False)
    
    print(f'✅ Room {room_code} now has {len(room_users)} users')

@socketio.on('browser-scroll')
def on_browser_scroll(data):
    room_code = data['roomCode']
    x = data.get('x', 0)
    y = data.get('y', 0)
    user_name = data.get('userName', 'Unknown')
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.scroll_to(x, y)

@socketio.on('browser-click')
def on_browser_click(data):
    room_code = data['roomCode']
    x = data.get('x', 0)
    y = data.get('y', 0)
    user_name = data.get('userName', 'Unknown')
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.click_at(x, y)

@socketio.on('chat-message')
def on_chat_message(data):
    room_code = data['roomCode']
    message = data['message']
    
    message_with_id = {
        **message,
        'id': str(uuid.uuid4())
    }
    
    if room_code in rooms_data:
        room = rooms_data[room_code]
        room['messages'].append(message_with_id)
        
        # Keep only last 100 messages
        if len(room['messages']) > 100:
            room['messages'] = room['messages'][-100:]
    
    emit('chat-message', message_with_id, room=room_code)

@socketio.on('leave-room')
def on_leave_room(data):
    room_code = data['roomCode']
    handle_user_leave(request.sid, room_code)

@socketio.on('browser-key')
def on_browser_key(data):
    room_code = data['roomCode']
    key = data['key']
    key_type = data['type']  # 'keydown', 'keyup', 'keypress'
    user_name = data.get('userName', 'Unknown')
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.send_key(key, key_type)

@socketio.on('mouse-move')
def on_mouse_move(data):
    room_code = data['roomCode']
    x = data.get('x', 0)
    y = data.get('y', 0)
    user_name = data.get('userName', 'Unknown')
    
    # Broadcast mouse position to all users in room
    emit('mouse-position', {
        'x': x,
        'y': y,
        'userName': user_name
    }, room=room_code, include_self=False)

@socketio.on('browser-navigate')
def on_browser_navigate(data):
    room_code = data['roomCode']
    url = data['url']
    user_name = data.get('userName', 'Unknown')
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.navigate_to(url)
        
        # Update room URL
        if room_code in rooms_data:
            rooms_data[room_code]['webtoon_url'] = url
        
        # Notify all users of URL change
        emit('url-changed', {'url': url}, room=room_code)
        
        # Add to chat
        add_system_message(room_code, f'🌐 {user_name} navigated to {url}')

@socketio.on('browser-navigate-back')
def on_browser_navigate_back(data):
    room_code = data['roomCode']
    user_name = data.get('userName', 'Unknown')
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        try:
            browser.driver.back()
            add_system_message(room_code, f'⬅️ {user_name} navigated back')
        except Exception as e:
            print(f"❌ Back navigation error: {e}")

@socketio.on('browser-navigate-forward')
def on_browser_navigate_forward(data):
    room_code = data['roomCode']
    user_name = data.get('userName', 'Unknown')
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        try:
            browser.driver.forward()
            add_system_message(room_code, f'➡️ {user_name} navigated forward')
        except Exception as e:
            print(f"❌ Forward navigation error: {e}")

@socketio.on('browser-refresh')
def on_browser_refresh(data):
    room_code = data['roomCode']
    user_name = data.get('userName', 'Unknown')
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        try:
            browser.driver.refresh()
            add_system_message(room_code, f'🔄 {user_name} refreshed the page')
        except Exception as e:
            print(f"❌ Refresh error: {e}")

def add_system_message(room_code, text):
    """Add a system message to the room"""
    if room_code in rooms_data:
        message = {
            'id': str(uuid.uuid4()),
            'userName': 'System',
            'message': text,
            'timestamp': int(time.time() * 1000),
            'type': 'system'
        }
        rooms_data[room_code]['messages'].append(message)
        socketio.emit('chat-message', message, room=room_code)

def handle_user_leave(session_id, room_code):
    if not room_code or room_code not in rooms_data:
        return
    
    room = rooms_data[room_code]
    
    if session_id in room['users']:
        user = room['users'][session_id]
        del room['users'][session_id]
        
        emit('user-left', user, room=room_code)
        
        room_users = list(room['users'].values())
        emit('room-users', room_users, room=room_code)
        
        # Clean up empty rooms
        if len(room['users']) == 0:
            # Stop browser
            if room_code in browser_instances:
                browser = browser_instances[room_code]
                browser.stop()
                del browser_instances[room_code]
            
            del rooms_data[room_code]
            print(f'🧹 Room {room_code} cleaned up')
        
        print(f'👋 {user["userName"]} left room {room_code}')
    
    if session_id in user_sessions:
        del user_sessions[session_id]

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print('🚀 Starting High-Performance Virtual Browser Server')
    print(f'📡 Server running on port {port}')
    print('🖥️ Optimized for minimal latency')
    print('⚡ 10 FPS screenshot updates')
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False)  # Debug=False for performance
