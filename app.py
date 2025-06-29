from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import threading
import time
import base64
import uuid
import os
import subprocess
import sys
import secrets
import asyncio

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

CORS(app, origins="*")

socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25
)

rooms_data = {}
user_sessions = {}
browser_instances = {}

class FullVirtualBrowser:
    def __init__(self, room_code, url):
        self.room_code = room_code
        self.url = url
        self.is_running = False
        self.page = None
        self.browser = None
        self.context = None
        self.playwright = None
        self.loop = None
        self.thread = None
        self.current_url = url
        self.page_title = ""
        self.can_go_back = False
        self.can_go_forward = False
        self.is_loading = False
        self.user_is_typing_url = False  # Track if user is typing in URL bar
        
    def start(self):
        """Start full-featured browser"""
        try:
            print(f"🚀 Starting FULL virtual browser for room {self.room_code}")
            
            self.thread = threading.Thread(target=self._run_browser_thread, daemon=True)
            self.thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ Error starting browser: {str(e)}")
            socketio.emit('browser-error', {'error': str(e)}, room=self.room_code)
            return False
    
    def _run_browser_thread(self):
        """Run browser in its own thread with event loop"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            self.loop.run_until_complete(self._setup_browser())
            self.loop.run_forever()
            
        except Exception as e:
            print(f"❌ Browser thread error: {str(e)}")
            socketio.emit('browser-error', {'error': str(e)}, room=self.room_code)
    
    async def _setup_browser(self):
        """Setup full-featured browser with Playwright"""
        try:
            # Install Playwright if needed
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                print("📦 Installing Playwright...")
                subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                from playwright.async_api import async_playwright
            
            print(f"🎭 Starting FULL Playwright browser for room {self.room_code}")
            
            # Start Playwright
            self.playwright = await async_playwright().start()
            
            # Launch browser with all features enabled
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--autoplay-policy=no-user-gesture-required',
                    '--enable-smooth-scrolling',
                    '--enable-accelerated-video-decode',
                    '--enable-gpu-rasterization',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--allow-running-insecure-content',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Create context with full browser features
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=1,
                has_touch=False,
                is_mobile=False,
                java_script_enabled=True,
                accept_downloads=True,
                ignore_https_errors=True,
                permissions=['geolocation', 'notifications']
            )
            
            # Create page
            self.page = await self.context.new_page()
            
            # Set up page event listeners
            await self._setup_page_listeners()
            
            print(f"📄 Loading URL: {self.url}")
            await self.page.goto(self.url, wait_until='domcontentloaded')
            
            self.is_running = True
            print(f"✅ FULL browser ready for room {self.room_code}")
            
            # Emit browser ready event
            socketio.emit('browser-ready', {
                'success': True,
                'features': ['typing', 'scrolling', 'clicking', 'navigation', 'keyboard_shortcuts']
            }, room=self.room_code)
            
            # Start screenshot loop
            asyncio.create_task(self._screenshot_loop())
            
        except Exception as e:
            print(f"❌ Browser setup error: {str(e)}")
            socketio.emit('browser-error', {'error': str(e)}, room=self.room_code)
    
    async def _setup_page_listeners(self):
        """Setup page event listeners for full browser functionality"""
        
        # Navigation events
        self.page.on('load', self._on_page_load)
        self.page.on('domcontentloaded', self._on_dom_ready)
        self.page.on('framenavigated', self._on_navigation)
        
        # Console events (for debugging)
        self.page.on('console', self._on_console)
        
        # Dialog events (alerts, confirms, etc.)
        self.page.on('dialog', self._on_dialog)
        
        # Download events
        self.page.on('download', self._on_download)
    
    async def _on_page_load(self, page):
        """Handle page load events"""
        try:
            self.current_url = page.url
            self.page_title = await page.title()
            
            # Check navigation state
            try:
                self.can_go_back = await page.evaluate('() => window.history.length > 1')
                self.can_go_forward = False  # Playwright doesn't expose this directly
            except:
                self.can_go_back = False
                self.can_go_forward = False
            
            print(f"📄 Page loaded: {self.page_title} - {self.current_url}")
            
            # Emit page info update (but don't override URL bar if user is typing)
            socketio.emit('page-info-update', {
                'url': self.current_url,
                'title': self.page_title,
                'canGoBack': self.can_go_back,
                'canGoForward': self.can_go_forward,
                'updateUrlBar': not self.user_is_typing_url  # Only update if user isn't typing
            }, room=self.room_code)
            
        except Exception as e:
            print(f"❌ Page load handler error: {e}")
    
    async def _on_dom_ready(self, page):
        """Handle DOM ready events"""
        self.is_loading = False
        socketio.emit('loading-state', {'loading': False}, room=self.room_code)
    
    async def _on_navigation(self, frame):
        """Handle navigation events"""
        if frame == self.page.main_frame:
            self.current_url = frame.url
            # Only emit URL change if user isn't typing
            if not self.user_is_typing_url:
                socketio.emit('url-changed', {'url': self.current_url}, room=self.room_code)
    
    async def _on_console(self, msg):
        """Handle console messages"""
        if msg.type == 'error':
            print(f"🔴 Browser console error: {msg.text}")
    
    async def _on_dialog(self, dialog):
        """Handle browser dialogs (alerts, confirms, prompts)"""
        print(f"💬 Dialog: {dialog.type} - {dialog.message}")
        
        # Emit dialog to users
        socketio.emit('browser-dialog', {
            'type': dialog.type,
            'message': dialog.message
        }, room=self.room_code)
        
        # Auto-accept for now (could be made interactive)
        await dialog.accept()
    
    async def _on_download(self, download):
        """Handle downloads"""
        print(f"📥 Download started: {download.suggested_filename}")
        socketio.emit('download-started', {
            'filename': download.suggested_filename,
            'url': download.url
        }, room=self.room_code)
    
    async def _take_screenshot(self):
        """Take a screenshot with full page info"""
        try:
            if not self.page:
                return
                
            # Take screenshot
            screenshot_bytes = await self.page.screenshot(
                type='jpeg',
                quality=90,
                full_page=False
            )
            
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # Get comprehensive page info
            page_info = await self.page.evaluate("""
                () => {
                    const scrollX = window.pageXOffset || document.documentElement.scrollLeft || 0;
                    const scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;
                    const maxScrollX = Math.max(0, (document.documentElement.scrollWidth || 0) - window.innerWidth);
                    const maxScrollY = Math.max(0, (document.documentElement.scrollHeight || 0) - window.innerHeight);
                    
                    // Check for video elements
                    const videos = document.querySelectorAll('video');
                    let hasVideo = false;
                    for (let video of videos) {
                        if (!video.paused && !video.ended && video.currentTime > 0) {
                            hasVideo = true;
                            break;
                        }
                    }
                    
                    // Get focused element info
                    const activeElement = document.activeElement;
                    const focusedElement = activeElement ? {
                        tagName: activeElement.tagName,
                        type: activeElement.type || null,
                        id: activeElement.id || null,
                        className: activeElement.className || null
                    } : null;
                    
                    return {
                        scroll: {
                            x: scrollX,
                            y: scrollY,
                            maxX: maxScrollX,
                            maxY: maxScrollY
                        },
                        page: {
                            width: document.documentElement.scrollWidth || 1920,
                            height: document.documentElement.scrollHeight || 1080,
                            viewportWidth: window.innerWidth,
                            viewportHeight: window.innerHeight
                        },
                        media: {
                            hasVideo: hasVideo
                        },
                        focus: focusedElement,
                        url: window.location.href,
                        title: document.title
                    };
                }
            """)
            
            # Prepare frame data
            frame_data = {
                'screenshot': screenshot_b64,
                'pageInfo': page_info,
                'timestamp': time.time(),
                'technology': 'Playwright Full'
            }
            
            socketio.emit('screenshot-update', frame_data, room=self.room_code)
            
        except Exception as e:
            print(f"❌ Screenshot error: {str(e)}")
    
    async def _screenshot_loop(self):
        """Continuous screenshot loop"""
        print(f"📸 Starting screenshot loop for room {self.room_code}")
        
        frame_count = 0
        
        while self.is_running and self.page:
            try:
                await self._take_screenshot()
                frame_count += 1
                
                if frame_count % 60 == 0:
                    print(f"📊 Room {self.room_code}: {frame_count} frames captured")
                
                # 30 FPS
                await asyncio.sleep(1/30)
                
            except Exception as e:
                print(f"❌ Screenshot loop error: {str(e)}")
                await asyncio.sleep(1)
    
    # Navigation methods
    def navigate_to(self, url):
        if self.loop and self.is_running:
            asyncio.run_coroutine_threadsafe(self._navigate(url), self.loop)
    
    async def _navigate(self, url):
        try:
            if self.page:
                self.is_loading = True
                socketio.emit('loading-state', {'loading': True}, room=self.room_code)
                print(f"🌐 Navigating to: {url}")
                await self.page.goto(url, wait_until='domcontentloaded')
        except Exception as e:
            print(f"❌ Navigate error: {e}")
            self.is_loading = False
            socketio.emit('loading-state', {'loading': False}, room=self.room_code)
    
    def go_back(self):
        if self.loop and self.is_running:
            asyncio.run_coroutine_threadsafe(self._go_back(), self.loop)
    
    async def _go_back(self):
        try:
            if self.page:
                await self.page.go_back(wait_until='domcontentloaded')
        except Exception as e:
            print(f"❌ Go back error: {e}")
    
    def go_forward(self):
        if self.loop and self.is_running:
            asyncio.run_coroutine_threadsafe(self._go_forward(), self.loop)
    
    async def _go_forward(self):
        try:
            if self.page:
                await self.page.go_forward(wait_until='domcontentloaded')
        except Exception as e:
            print(f"❌ Go forward error: {e}")
    
    def reload(self):
        if self.loop and self.is_running:
            asyncio.run_coroutine_threadsafe(self._reload(), self.loop)
    
    async def _reload(self):
        try:
            if self.page:
                await self.page.reload(wait_until='domcontentloaded')
        except Exception as e:
            print(f"❌ Reload error: {e}")
    
    # Input methods
    def click_at(self, x, y):
        if self.loop and self.is_running:
            asyncio.run_coroutine_threadsafe(self._click(x, y), self.loop)
    
    async def _click(self, x, y):
        try:
            if self.page:
                print(f"🖱️ Clicking at: ({x}, {y})")
                await self.page.mouse.click(x, y)
                await asyncio.sleep(0.1)
                await self._take_screenshot()
        except Exception as e:
            print(f"❌ Click error: {e}")
    
    def scroll_to(self, x, y):
        if self.loop and self.is_running:
            asyncio.run_coroutine_threadsafe(self._scroll(x, y), self.loop)
    
    async def _scroll(self, x, y):
        try:
            if self.page:
                print(f"📜 Scrolling to: ({x}, {y})")
                await self.page.evaluate(f"window.scrollTo({x}, {y})")
                await asyncio.sleep(0.1)
                await self._take_screenshot()
        except Exception as e:
            print(f"❌ Scroll error: {e}")
    
    def scroll_by(self, delta_x, delta_y):
        if self.loop and self.is_running:
            asyncio.run_coroutine_threadsafe(self._scroll_by(delta_x, delta_y), self.loop)
    
    async def _scroll_by(self, delta_x, delta_y):
        try:
            if self.page:
                await self.page.mouse.wheel(delta_x, delta_y)
                await asyncio.sleep(0.1)
                await self._take_screenshot()
        except Exception as e:
            print(f"❌ Scroll by error: {e}")
    
    # Keyboard methods
    def type_text(self, text):
        if self.loop and self.is_running:
            asyncio.run_coroutine_threadsafe(self._type_text(text), self.loop)
    
    async def _type_text(self, text):
        try:
            if self.page:
                print(f"⌨️ Typing: {text}")
                await self.page.keyboard.type(text)
                await asyncio.sleep(0.1)
                await self._take_screenshot()
        except Exception as e:
            print(f"❌ Type error: {e}")
    
    def press_key(self, key):
        if self.loop and self.is_running:
            asyncio.run_coroutine_threadsafe(self._press_key(key), self.loop)
    
    async def _press_key(self, key):
        try:
            if self.page:
                print(f"⌨️ Pressing key: {key}")
                await self.page.keyboard.press(key)
                await asyncio.sleep(0.1)
                await self._take_screenshot()
        except Exception as e:
            print(f"❌ Key press error: {e}")
    
    def key_combination(self, keys):
        if self.loop and self.is_running:
            asyncio.run_coroutine_threadsafe(self._key_combination(keys), self.loop)
    
    async def _key_combination(self, keys):
        try:
            if self.page:
                print(f"⌨️ Key combination: {'+'.join(keys)}")
                
                # Press all keys down
                for key in keys:
                    await self.page.keyboard.down(key)
                
                # Release all keys
                for key in reversed(keys):
                    await self.page.keyboard.up(key)
                
                await asyncio.sleep(0.1)
                await self._take_screenshot()
        except Exception as e:
            print(f"❌ Key combination error: {e}")
    
    def set_url_typing_state(self, is_typing):
        """Set whether user is currently typing in URL bar"""
        self.user_is_typing_url = is_typing
    
    def stop(self):
        """Stop the browser"""
        self.is_running = False
        
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._cleanup(), self.loop)
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        print(f"🛑 Full browser stopped for room {self.room_code}")
    
    async def _cleanup(self):
        """Cleanup browser resources"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            print(f"❌ Cleanup error: {e}")

# Flask routes
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
        'technology': 'Playwright Full Browser',
        'rooms': len(rooms_data),
        'active_browsers': len(browser_instances),
        'features': ['typing', 'scrolling', 'clicking', 'navigation', 'keyboard_shortcuts', 'forms']
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

# Socket events
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
    is_creator = data.get('isCreator', False)
    
    print(f'👤 {user_name} joining FULL browser room {room_code}')
    
    join_room(room_code)
    
    user_sessions[request.sid] = {
        'user_name': user_name,
        'room_code': room_code,
        'is_creator': is_creator
    }
    
    if room_code not in rooms_data:
        if is_creator:
            default_url = 'https://www.webtoon.com'
            print(f'🏠 Creating FULL browser room {room_code}')
            rooms_data[room_code] = {
                'users': {},
                'messages': [],
                'webtoon_url': default_url,
                'created_at': time.time(),
                'creator': user_name
            }
            
            browser = FullVirtualBrowser(room_code, default_url)
            browser_instances[room_code] = browser
            
            success = browser.start()
            if not success:
                emit('browser-error', {'error': 'Failed to start browser'})
                return
        else:
            emit('room-not-found')
            return
    
    room = rooms_data[room_code]
    room['users'][request.sid] = {'id': request.sid, 'userName': user_name}
    
    room_users = list(room['users'].values())
    emit('room-users', room_users)
    emit('webtoon-url-update', {'url': room['webtoon_url']})
    
    emit('user-joined', {'userName': user_name}, room=room_code, include_self=False)
    emit('room-users', room_users, room=room_code, include_self=False)

# Browser control events
@socketio.on('browser-navigate')
def on_browser_navigate(data):
    room_code = data['roomCode']
    url = data['url']
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.navigate_to(url)
        
        if room_code in rooms_data:
            rooms_data[room_code]['webtoon_url'] = url

@socketio.on('url-typing-start')
def on_url_typing_start(data):
    room_code = data['roomCode']
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.set_url_typing_state(True)

@socketio.on('url-typing-stop')
def on_url_typing_stop(data):
    room_code = data['roomCode']
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.set_url_typing_state(False)

@socketio.on('browser-back')
def on_browser_back(data):
    room_code = data['roomCode']
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.go_back()

@socketio.on('browser-forward')
def on_browser_forward(data):
    room_code = data['roomCode']
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.go_forward()

@socketio.on('browser-reload')
def on_browser_reload(data):
    room_code = data['roomCode']
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.reload()

@socketio.on('browser-click')
def on_browser_click(data):
    room_code = data['roomCode']
    x = data.get('x', 0)
    y = data.get('y', 0)
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.click_at(x, y)

@socketio.on('browser-scroll')
def on_browser_scroll(data):
    room_code = data['roomCode']
    x = data.get('x', 0)
    y = data.get('y', 0)
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.scroll_to(x, y)

@socketio.on('browser-scroll-by')
def on_browser_scroll_by(data):
    room_code = data['roomCode']
    delta_x = data.get('deltaX', 0)
    delta_y = data.get('deltaY', 0)
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.scroll_by(delta_x, delta_y)

@socketio.on('browser-type')
def on_browser_type(data):
    room_code = data['roomCode']
    text = data['text']
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.type_text(text)

@socketio.on('browser-key')
def on_browser_key(data):
    room_code = data['roomCode']
    key = data['key']
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.press_key(key)

@socketio.on('browser-key-combo')
def on_browser_key_combo(data):
    room_code = data['roomCode']
    keys = data['keys']
    
    if room_code in browser_instances:
        browser = browser_instances[room_code]
        browser.key_combination(keys)

@socketio.on('chat-message')
def on_chat_message(data):
    room_code = data['roomCode']
    message = data['message']
    
    message_with_id = {**message, 'id': str(uuid.uuid4())}
    
    if room_code in rooms_data:
        room = rooms_data[room_code]
        room['messages'].append(message_with_id)
        if len(room['messages']) > 100:
            room['messages'] = room['messages'][-100:]
    
    emit('chat-message', message_with_id, room=room_code)

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
        
        if len(room['users']) == 0:
            if room_code in browser_instances:
                browser = browser_instances[room_code]
                browser.stop()
                del browser_instances[room_code]
            
            del rooms_data[room_code]
            print(f'🧹 Room {room_code} cleaned up')
    
    if session_id in user_sessions:
        del user_sessions[session_id]

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print('🚀 Starting FULL Virtual Browser Server')
    print(f'📡 Server running on port {port}')
    print('🎭 Technology: Playwright FULL Browser')
    print('⌨️ Features: Typing, Scrolling, Clicking, Navigation, Keyboard Shortcuts, Forms')
    print('🌐 Full browser functionality enabled!')
    
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
