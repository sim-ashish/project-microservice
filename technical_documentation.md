# Technical Documentation - Microservice Chat Application

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Services](#services)
4. [Database Schema](#database-schema)
5. [API Documentation](#api-documentation)
6. [WebSocket Communication](#websocket-communication)
7. [Authentication & Authorization](#authentication--authorization)
8. [Video Streaming](#video-streaming)
9. [Deployment](#deployment)
10. [Configuration](#configuration)
11. [Testing](#testing)
12. [Troubleshooting](#troubleshooting)

## Project Overview

A microservices-based real-time chat application with video streaming capabilities. The system consists of multiple independent services that communicate through REST APIs, WebSocket connections, and Redis pub/sub messaging.

### Key Features
- Real-time group chat with WebSocket connections
- JWT-based authentication and authorization
- Group management with member permissions
- Synchronized video streaming within groups
- Video file upload to Azure Blob Storage
- Nginx reverse proxy for unified access
- Redis pub/sub for cross-service communication

### Technology Stack
- **Backend**: FastAPI, Python 3.10+
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Databases**: PostgreSQL (users/groups), MongoDB (messages), Redis (caching/pub-sub)
- **Cloud Storage**: Azure Blob Storage
- **Reverse Proxy**: Nginx
- **Authentication**: JWT tokens
- **WebSocket**: FastAPI WebSocket support

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Nginx (Port 80)                           │
│                        Reverse Proxy                               │
└─────────────────────────────────────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
┌───────▼────────┐    ┌──────────▼─────────┐    ┌──────────▼─────────┐
│   Frontend     │    │    Auth Service    │    │   Chat Service     │
│   (Port 3000)  │    │    (Port 8000)     │    │   (Port 8001)      │
│                │    │                    │    │                    │
│ • HTML/CSS/JS  │    │ • User Management  │    │ • Real-time Chat   │
│ • Static Files │    │ • JWT Auth         │    │ • WebSocket        │
│ • Video Player │    │ • Group Management │    │ • Message Storage  │
└────────────────┘    └────────────────────┘    └────────────────────┘
                               │                          │
                      ┌────────▼────────┐    ┌──────────▼─────────┐
                      │   PostgreSQL    │    │     MongoDB        │
                      │   (Users/Groups)│    │    (Messages)      │
                      └─────────────────┘    └────────────────────┘
                                                        │
┌─────────────────┐   ┌─────────────────────────────────▼─────────┐
│  Stream Service │   │             Redis                         │
│  (Port 8002)    │   │                                          │
│                 │   │ • Pub/Sub Messaging                      │
│ • Video Upload  │   │ • Session Caching                        │
│ • File Streaming│   │ • Cross-service Communication            │
│ • Azure Blob    │   │                                          │
└─────────────────┘   └──────────────────────────────────────────┘
        │
┌───────▼───────┐
│ Azure Blob    │
│ Storage       │
│ (Videos)      │
└───────────────┘
```

## Services

### 1. Auth Service (Port 8000)

**Location**: `auth/`  
**Main File**: `auth/main.py`

#### Responsibilities
- User registration and authentication
- JWT token generation and validation
- Group management (create, add/remove members)
- Authorization for group access

#### Key Components
- **Models**: `auth/models.py` - SQLAlchemy models for User and Group
- **Schemas**: `auth/schemas.py` - Pydantic models for API validation
- **Utils**: `auth/utils.py` - Authentication helpers, password hashing
- **Database**: `auth/database.py` - PostgreSQL connection and session management

#### Database Migrations
- **Alembic**: `auth/alembic/` - Database migration management
- **Configuration**: `auth/alembic.ini`
- **Migration Files**:
  - `a0b1bbf1cf15_initial_migration_users_table.py` - Users table
  - `01e190bd2b55_add_groups_table.py` - Groups table
  - `85ab58fc22e6_add_user_group_relationship.py` - User-Group relationships

### 2. Chat Service (Port 8001)

**Location**: `chat/`  
**Main File**: `chat/main.py`

#### Responsibilities
- Real-time WebSocket messaging
- Message persistence in MongoDB
- Cross-service communication via Redis
- Video synchronization between group members

#### Key Components
- **Connection Manager**: `chat/connection.py` - WebSocket connection management
- **Schemas**: `chat/schemas.py` - Message validation models
- **Redis Client**: `chat/redis_client.py` - Redis pub/sub implementation

#### Message Types
- `message`: Regular chat messages
- `add`: User added to group notifications
- `leave`: User removed from group notifications
- `video_control`: Video synchronization events

### 3. Frontend Service (Port 3000)

**Location**: `frontend/`  
**Server**: `frontend/server.py`

#### Components
- **Login Page**: `frontend/index.html` + `frontend/login.js`
- **Chat Page**: `frontend/chat.html` + `frontend/chat.js`
- **Styles**: `frontend/style.css` - Responsive CSS with animations

#### Features
- JWT token validation before chat access
- Real-time WebSocket messaging
- Video player with group synchronization
- Connection status monitoring
- Auto-reconnect functionality

### 4. Stream Service (Port 8002)

**Location**: `stream/`  
**Main File**: `stream/main.py`

#### Responsibilities
- Video file management and streaming
- Azure Blob Storage integration
- Video player interface
- File upload handling

#### Key Components
- **Static Files**: `stream/static/` - Video player HTML/CSS/JS
- **Videos**: `stream/videos/` - Local video storage (backup)

#### Features
- Video streaming with range requests
- Multiple format support (MP4, WebM, OGG, etc.)
- Azure Blob Storage integration
- Video upload API

## Database Schema

### PostgreSQL (Auth Service)

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    password VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Groups table
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User-Group association table
CREATE TABLE user_group_association (
    user_id INTEGER REFERENCES users(id),
    group_id INTEGER REFERENCES groups(id),
    PRIMARY KEY (user_id, group_id)
);
```

### MongoDB (Chat Service)

```javascript
// Messages collection
{
  _id: ObjectId,
  text: String,
  user: String,           // User email
  group_id: Number,       // Group identifier
  type: String,           // "message", "add", "leave", "video_control"
  video_action: String,   // Optional: "play", "pause", "seek"
  video_name: String,     // Optional: video filename
  video_time: Number,     // Optional: video timestamp
  created_at: Date
}
```

## API Documentation

### Auth Service Endpoints

#### Authentication
```http
POST /register
Content-Type: application/json

{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "securepassword"
}
```

```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword
```

```http
POST /token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=securepassword
```

#### User Management
```http
GET /verify-token
Authorization: Bearer <jwt_token>
```

```http
GET /users/me
Authorization: Bearer <jwt_token>
```

#### Group Management
```http
POST /groups
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "My Group",
  "description": "A sample group"
}
```

```http
GET /groups
Authorization: Bearer <jwt_token>
```

```http
GET /verify-group-access/{group_id}
Authorization: Bearer <jwt_token>
```

```http
POST /groups/{group_id}/members
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "email": "newuser@example.com"
}
```

```http
DELETE /groups/{group_id}/members
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "email": "removeuser@example.com"
}
```

### Chat Service Endpoints

```http
GET /messages?group_id={group_id}&limit={limit}&offset={offset}
Authorization: Bearer <jwt_token>
```

### Stream Service Endpoints

```http
GET /api/videos
```

```http
GET /api/stream/{video_name}
Range: bytes=0-1023
```

```http
POST /api/upload
Content-Type: multipart/form-data

file: <video_file>
```

## WebSocket Communication

### Connection Endpoint
```
ws://localhost:8001/ws/group/{group_id}?token={jwt_token}
```

### Message Formats

#### Regular Message
```json
{
  "type": "message",
  "text": "Hello everyone!",
  "user": "user@example.com",
  "group_id": 1,
  "created_at": "2025-12-18T10:30:00Z"
}
```

#### User Addition Notification
```json
{
  "type": "add",
  "text": "John Doe (john@example.com) was added to My Group",
  "user": "system",
  "group_id": 1,
  "user_email": "john@example.com"
}
```

#### Video Control Synchronization
```json
{
  "type": "video_control",
  "video_action": "play",
  "video_name": "sample.mp4",
  "video_time": 120.5,
  "user": "user@example.com",
  "group_id": 1
}
```

## Authentication & Authorization

### JWT Token Structure
```json
{
  "sub": "user@example.com",
  "exp": 1703761200,
  "iat": 1703674800
}
```

### Security Features
- Password hashing with bcrypt
- JWT tokens with expiration
- Group-based access control
- Token validation middleware
- Secure cookie handling

### Flow
1. User registers/logs in via Auth Service
2. Auth Service returns JWT token
3. Frontend stores token in localStorage
4. All subsequent requests include Authorization header
5. Services validate tokens via Auth Service

## Video Streaming

### Supported Formats
- MP4 (H.264/AAC)
- WebM (VP8/VP9)
- OGG (Theora/Vorbis)
- AVI, MOV, MKV

### Streaming Features
- HTTP range requests for efficient streaming
- Azure Blob Storage integration
- Video synchronization across group members
- Play/pause/seek synchronization
- Multiple quality options

### Video Controls Sync
When a user performs a video action:
1. Frontend sends WebSocket message to Chat Service
2. Chat Service broadcasts to all group members
3. Other clients update their video player accordingly

## Deployment

### Single System Deployment

1. **Start Services**:
   ```bash
   # Auth Service
   cd auth && uvicorn main:app --host 0.0.0.0 --port 8000
   
   # Chat Service
   cd chat && uvicorn main:app --host 0.0.0.0 --port 8001
   
   # Stream Service
   cd stream && uvicorn main:app --host 0.0.0.0 --port 8002
   
   # Frontend Service
   cd frontend && python server.py
   ```

2. **Configure Nginx**:
   ```bash
   # Backup original config
   sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup
   
   # Copy project config
   sudo cp nginx/nginx.conf /etc/nginx/nginx.conf
   
   # Restart Nginx
   sudo nginx -s reload
   ```

3. **Access Application**: `http://127.0.0.1:3001`

### Multi-Computer Deployment

1. Deploy each service on separate servers
2. Configure private network communication
3. Update frontend URLs to match deployment
4. Implement API gateway for external access
5. Set up load balancing if needed

### Docker Deployment (Recommended)

```dockerfile
# Example Dockerfile for Auth Service
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Configuration

### Environment Variables

#### Auth Service
```bash
DATABASE_URL=postgresql://user:password@localhost/chatapp
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### Chat Service
```bash
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=chatapp
REDIS_URL=redis://localhost:6379
AUTH_SERVICE_URL=http://localhost:8000
```

#### Stream Service
```bash
AZURE_STORAGE_CONNECTION_STRING=your-azure-connection-string
AZURE_CONTAINER_NAME=videos
```

### Database Configuration

#### PostgreSQL Setup
```sql
CREATE DATABASE chatapp;
CREATE USER chatuser WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE chatapp TO chatuser;
```

#### MongoDB Setup
```javascript
use chatapp
db.createCollection("messages")
db.messages.createIndex({ "group_id": 1, "created_at": -1 })
```

#### Redis Setup
```bash
# Redis configuration in redis.conf
bind 127.0.0.1
port 6379
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### Nginx Configuration
```nginx
upstream frontend {
    server 127.0.0.1:3000;
}

upstream auth {
    server 127.0.0.1:8000;
}

upstream chat {
    server 127.0.0.1:8001;
}

upstream stream {
    server 127.0.0.1:8002;
}

server {
    listen 3001;
    server_name localhost;

    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /auth/ {
        proxy_pass http://auth/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /chat/ {
        proxy_pass http://chat/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /stream/ {
        proxy_pass http://stream/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Testing

### Test Structure
```
auth/tests/
├── conftest.py              # Test configuration
├── test_auth_login.py       # Login functionality tests
└── test_auth_protected.py   # Protected endpoint tests
```

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run auth service tests
cd auth && python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Test Examples

#### Authentication Test
```python
@pytest.mark.asyncio
async def test_user_registration(client):
    response = await client.post("/register", json={
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

#### WebSocket Test
```python
@pytest.mark.asyncio
async def test_websocket_connection(client):
    with client.websocket_connect("/ws/group/1?token=valid_token") as websocket:
        websocket.send_json({"text": "Hello World!"})
        data = websocket.receive_json()
        assert data["text"] == "Hello World!"
```

## Troubleshooting

### Common Issues

#### 1. WebSocket Connection Fails
**Symptoms**: Chat messages not sending/receiving
**Solutions**:
- Check if Chat Service is running on port 8001
- Verify JWT token is valid and not expired
- Check browser console for WebSocket errors
- Ensure user has access to the group

#### 2. Authentication Errors
**Symptoms**: Login fails, "Invalid token" errors
**Solutions**:
- Verify database connection in Auth Service
- Check JWT secret key configuration
- Ensure password hashing is working correctly
- Verify user exists in database

#### 3. Video Streaming Issues
**Symptoms**: Videos won't load or play
**Solutions**:
- Check Azure Blob Storage configuration
- Verify video file formats are supported
- Check browser network tab for HTTP errors
- Ensure proper CORS headers

#### 4. Database Connection Issues
**Symptoms**: Service startup fails, database errors
**Solutions**:
- Verify database server is running
- Check connection strings in environment variables
- Ensure database and collections exist
- Check user permissions

### Logging and Monitoring

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Monitor WebSocket Connections
```python
# In connection.py
async def connect(self, websocket: WebSocket, group_id: int, user_email: str):
    logger.info(f"User {user_email} connecting to group {group_id}")
    # ... connection logic
```

#### Database Query Monitoring
```python
# Enable SQLAlchemy logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Performance Optimization

#### Database Indexing
```sql
-- PostgreSQL
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_groups_created_by ON groups(created_by);

-- MongoDB
db.messages.createIndex({ "group_id": 1, "created_at": -1 })
```

#### Redis Optimization
```bash
# Increase max memory for Redis
maxmemory 512mb
maxmemory-policy allkeys-lru
```

#### Nginx Optimization
```nginx
# Enable gzip compression
gzip on;
gzip_types text/plain text/css application/json application/javascript;

# Enable caching for static files
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### Monitoring and Health Checks

#### Service Health Endpoints
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

#### Database Connection Check
```python
@app.get("/health/db")
async def db_health_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database unavailable")
```

---

## Contributing

### Development Setup
1. Clone the repository
2. Set up virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Configure environment variables
5. Run database migrations
6. Start services in development mode

### Code Style
- Follow PEP 8 for Python code
- Use type hints for function parameters and returns
- Add docstrings for public functions and classes
- Write unit tests for new features

### Git Workflow
1. Create feature branch from main
2. Make changes and add tests
3. Ensure all tests pass
4. Submit pull request for review

---

*Last Updated: December 18, 2025*