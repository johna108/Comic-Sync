# Comic Sync - Virtual Browser Sync

A real-time synchronized virtual browser application built with **Python Flask and Playwright**, enabling multiple users to browse the web together with optimized performance for comics, manga, and video content.

## 🐍 Technology Stack

- **Backend**: Python Flask + Flask-SocketIO
- **Virtual Browser**: Playwright with Chromium
- **Frontend**: HTML/CSS/JavaScript with Tailwind CSS
- **Real-time Communication**: WebSocket via SocketIO
- **Performance**: Optimized for 30 FPS with video detection

## 🚀 Features

- **Real-time Browser Sync**: Multiple users can view and interact with the same browser session
- **Full Browser Functionality**: Complete web browsing experience with navigation, clicking, scrolling, and typing
- **Live Chat**: Real-time messaging between users in each room
- **Interactive Controls**: Click, scroll, type, and navigate with full synchronization
- **Video Optimization**: Automatic detection and optimization for video content
- **Room Management**: Create and join rooms with 6-digit alphanumeric codes
- **Responsive Design**: Works on desktop and mobile devices
- **Performance Monitoring**: Real-time FPS and connection status indicators

## 🎯 Use Cases

- **Collaborative Comic/Manga Reading**: Perfect for Webtoon, MangaPark, MangaDex
- **Video Sharing**: Optimized for YouTube and video streaming
- **Remote Presentations**: Share web content during meetings
- **Educational Sessions**: Group web exploration and learning
- **Content Review**: Collaborative content browsing and discussion

## 🛠️ Setup

### Prerequisites

- Python 3.8+
- 2GB+ RAM recommended
- Stable internet connection

### Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo>
   cd comic-sync
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers** (automatic on first run):
   ```bash
   python -m playwright install chromium
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Open your browser**:
   Go to [http://localhost:5000](http://localhost:5000)

## 📁 Project Structure

```
├── app.py                 # Main Flask application with Playwright integration
├── requirements.txt       # Python dependencies
├── templates/            # HTML templates
│   ├── index.html        # Home page (create/join rooms)
│   ├── room.html         # Main room interface with virtual browser
│   └── full_room.html    # Alternative room layout
├── venv/                # Python virtual environment
└── README.md
```

## 🎮 Usage

1. **Start the Server**: Run `python app.py`
2. **Create Room**: Enter your name and click "Create Room"
3. **Join Room**: Enter your name and a 6-digit room code
4. **Navigate**: Use the URL bar or quick navigation buttons
5. **Interact**: Click, scroll, and type - all synchronized across users
6. **Chat**: Use the chat panel to communicate with other users
7. **Monitor Performance**: Watch the performance indicator for FPS and video detection

## 🎬 Performance Features

### Video Optimization
- **Automatic Detection**: Detects playing video content
- **Performance Monitoring**: Real-time FPS tracking
- **GPU Acceleration**: Hardware-accelerated video decoding
- **Optimized Screenshots**: Efficient capture and transmission

### Browser Features
- **Full Navigation**: Back, forward, reload functionality
- **Keyboard Support**: Text typing and special key combinations
- **Mouse Interaction**: Click and scroll synchronization
- **URL Management**: Smart URL bar with typing state detection
- **Page State Tracking**: Scroll position, focus state, and more

## 🔧 Configuration

### Environment Variables

```bash
export PORT=5000                    # Server port (default: 5000)
export SECRET_KEY=your-secret-key   # Flask secret key (auto-generated)
```

### Browser Configuration

The application uses optimized Chrome flags for performance:

```python
# Performance optimizations
'--enable-accelerated-video-decode',
'--enable-gpu-rasterization',
'--disable-background-timer-throttling',
'--disable-backgrounding-occluded-windows'
```

## 📊 Performance Monitoring

### Real-time Indicators
- **FPS Display**: Current frame rate
- **Video Detection**: Shows when video content is playing
- **Focus State**: Indicates browser focus for keyboard input
- **Connection Status**: WebSocket connection health

### Expected Performance
- **Frame Rate**: 30 FPS base, optimized for video content
- **Latency**: <100ms for user interactions
- **Memory Usage**: ~100-200MB per browser instance
- **Concurrent Users**: Limited by server resources

## 🎯 Quick Navigation

The application includes quick navigation buttons for popular sites:
- 🔍 **Webtoon**: https://www.webtoon.com
- 📺 **YouTube**: https://www.youtube.com
- 💻 **MangaPark**: https://mangapark.net
- 📚 **MangaDex**: https://mangadex.org/

## 🔍 API Endpoints

- `GET /` - Home page
- `GET /room/<room_code>` - Room interface
- `GET /health` - Health check endpoint
- `GET /api/room/<room_code>` - Room information

## 🛡️ Security Notes

- **Development Mode**: CORS is open for development
- **Public Rooms**: No authentication required
- **Browser Security**: Some Chrome security features are disabled for functionality

## 🚀 Deployment

### Production Considerations
- Set proper `SECRET_KEY` environment variable
- Configure CORS for production domains
- Use a production WSGI server (Gunicorn, uWSGI)
- Consider reverse proxy (Nginx) for load balancing
- Monitor memory usage for multiple concurrent rooms

### Docker Deployment (Future)
```dockerfile
# Example Dockerfile for future implementation
FROM python:3.9-slim
RUN apt-get update && apt-get install -y chromium
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is open source. Please check the repository for license information.

## 🆘 Troubleshooting

### Common Issues

**Browser won't start:**
- Ensure Playwright is installed: `python -m playwright install chromium`
- Check available memory (2GB+ recommended)
- Verify Python version (3.8+)

**Performance issues:**
- Close other browser instances
- Check network connection
- Monitor server resources

**Connection problems:**
- Verify WebSocket support in browser
- Check firewall settings
- Ensure port 5000 is available

## 🔮 Future Enhancements

- [ ] User authentication and room permissions
- [ ] Persistent room states and chat history
- [ ] Advanced video streaming with WebRTC
- [ ] Mobile app support
- [ ] Plugin system for extended functionality
- [ ] Analytics and usage tracking
- [ ] Multi-language support
- [ ] File upload and drag-and-drop support

---

**Built with ❤️ using Python, Flask, Playwright, and SocketIO**
