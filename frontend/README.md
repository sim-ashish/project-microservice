# Frontend - Microservice Chat Application

A simple, vanilla JavaScript frontend for the microservice chat application with video streaming capabilities.

## Features

### 🔐 Authentication
- Group ID and JWT token-based authentication
- Token verification before accessing chat
- Session persistence using localStorage

### 💬 Real-time Chat
- WebSocket-based real-time messaging
- Message type differentiation:
  - **Regular messages** (`type: message`) - User chat messages
  - **Add notifications** (`type: add`) - User added to group
  - **Leave notifications** (`type: leave`) - User removed from group
- Auto-reconnect on connection loss (up to 5 attempts)
- Visual connection status indicator

### 🎥 Video Streaming
- Integrated video player (top half of screen)
- Video selection from available videos
- Synchronized viewing within group

### 🎨 UI/UX
- Clean, modern design with animations
- Fully responsive (mobile-friendly)
- Real-time connection status
- Keyboard shortcuts:
  - `/` - Focus message input
  - `Enter` - Send message

## File Structure

```
frontend/
├── index.html      # Login/Join page
├── chat.html       # Main chat page with video player
├── style.css       # All styles (no framework)
├── login.js        # Login page logic
├── chat.js         # Chat and WebSocket logic
├── server.py       # Simple FastAPI server to serve files
└── README.md       # This file
```

## Setup & Running

### Prerequisites
- Auth service running on `http://localhost:8000`
- Chat service running on `http://localhost:8001`
- Stream service running on `http://localhost:8002`
- Redis server running on `localhost:6379`

### Start the Frontend Server

```bash
cd frontend
uv run uvicorn server:app --host 0.0.0.0 --port 3000 --reload
```

Or use Python directly:

```bash
python server.py
```

### Access the Application

Open your browser and navigate to: `http://localhost:3000`

## Usage Flow

### 1. Get Authentication Token

First, register or login to get an access token:

**Register:**
```bash
curl -X POST "http://localhost:8000/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "name": "John Doe",
    "password": "securepassword"
  }'
```

**Login:**
```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword"
  }'
```

Copy the `access_token` from the response.

### 2. Create or Join a Group

**Create Group:**
```bash
curl -X POST "http://localhost:8000/groups" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Group",
    "description": "A test group"
  }'
```

Note the `id` from the response.

### 3. Access Frontend

1. Open `http://localhost:3000`
2. Enter the **Group ID** and your **Access Token**
3. Click "Join Group"
4. You'll be redirected to the chat page

### 4. Using the Chat

- **Send Messages**: Type in the input box and press Enter or click send
- **View Video**: Click "Select Video" to choose from available videos
- **System Notifications**: See when users are added/removed from the group
- **Connection Status**: Monitor your WebSocket connection in the header

## Architecture

### Services Integration

```
┌─────────────────┐
│   Frontend      │  http://localhost:3000
│   (Port 3000)   │
└────────┬────────┘
         │
         ├──HTTP──> Auth Service (Port 8000)
         │          • Verify token
         │          • Check group membership
         │
         ├──WS───> Chat Service (Port 8001)
         │          • Real-time messaging
         │          • Receive add/leave notifications
         │
         └──HTTP──> Stream Service (Port 8002)
                    • List videos
                    • Stream video files
```

### WebSocket Message Flow

**Outgoing (User → Server):**
```json
{
  "text": "Hello everyone!",
  "group_id": 1
}
```

**Incoming (Server → User):**

*Regular Message:*
```json
{
  "type": "message",
  "text": "Hello everyone!",
  "user": "user@example.com",
  "group_id": 1,
  "created_at": "2025-11-26T10:30:00Z"
}
```

*Add Notification:*
```json
{
  "type": "add",
  "text": "John Doe (john@example.com) was added to My Group",
  "user": "system",
  "group_id": 1,
  "user_email": "john@example.com"
}
```

*Leave Notification:*
```json
{
  "type": "leave",
  "text": "Jane Doe (jane@example.com) was removed from My Group",
  "user": "system",
  "group_id": 1,
  "user_email": "jane@example.com"
}
```

## API Endpoints Used

### Auth Service (Port 8000)
- `GET /verify-group-access/{group_id}` - Verify user's group membership

### Chat Service (Port 8001)
- `WebSocket /ws/group/{group_id}` - Real-time chat connection

### Stream Service (Port 8002)
- `GET /api/videos` - List available videos
- `GET /api/stream/{video_name}` - Stream video file

## Customization

### Change Service URLs

Edit the URLs in the JavaScript files:

**login.js:**
```javascript
const API_BASE_URL = 'http://localhost:8000';
```

**chat.js:**
```javascript
const CHAT_WS_URL = 'ws://localhost:8001';
const STREAM_API_URL = 'http://localhost:8002';
```

### Modify Styles

All styles are in `style.css` using CSS variables for easy theming:

```css
:root {
    --primary: #6366f1;
    --primary-dark: #4f46e5;
    --success: #10b981;
    --danger: #ef4444;
    /* ... more variables ... */
}
```

## Browser Compatibility

- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers

Requires:
- WebSocket support
- localStorage support
- ES6+ JavaScript

## Troubleshooting

### Cannot Connect to Services

1. Verify all services are running:
   ```bash
   # Auth service
   curl http://localhost:8000/docs
   
   # Chat service
   curl http://localhost:8001/docs
   
   # Stream service
   curl http://localhost:8002/docs
   ```

2. Check Redis is running:
   ```bash
   redis-cli ping  # Should return "PONG"
   ```

### WebSocket Connection Fails

1. Check the browser console for errors
2. Verify your token is valid (not expired)
3. Ensure you're a member of the group
4. Check CORS settings in backend services

### Video Not Playing

1. Ensure stream service is running
2. Check videos exist in `stream/videos/` directory
3. Verify video format is supported (MP4, WebM, OGG)

## Security Notes

- Tokens are stored in localStorage (consider sessionStorage for more security)
- Always use HTTPS in production
- Implement token refresh mechanism for long sessions
- Validate all user inputs
- Add rate limiting for messages

## Future Enhancements

- [ ] File/image sharing in chat
- [ ] Typing indicators
- [ ] Read receipts
- [ ] User avatars
- [ ] Emoji picker
- [ ] Message reactions
- [ ] Dark mode toggle
- [ ] Video synchronization (watch together)
- [ ] Voice/video calls
- [ ] Desktop notifications
