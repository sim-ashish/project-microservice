// Chat page JavaScript
const CHAT_WS_URL = 'ws://localhost:8001';
const STREAM_API_URL = 'http://localhost:8002';

let ws = null;
let groupId = null;
let accessToken = null;
let userEmail = null;
let groupName = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
let ignoreVideoEvents = false; // Flag to prevent rebroadcast loops
let currentVideoName = null;

document.addEventListener('DOMContentLoaded', () => {
    // Check if user has valid session
    if (!checkSession()) {
        window.location.href = 'index.html';
        return;
    }

    initializePage();
    connectWebSocket();
    loadVideos();
    setupEventListeners();
    setupVideoEventListeners();
});

function checkSession() {
    groupId = localStorage.getItem('groupId');
    accessToken = localStorage.getItem('accessToken');
    userEmail = localStorage.getItem('userEmail');
    groupName = localStorage.getItem('groupName');

    return groupId && accessToken && userEmail;
}

function initializePage() {
    // Update UI with group info
    document.getElementById('groupIdDisplay').textContent = groupId;
    document.getElementById('groupName').textContent = groupName || `Group ${groupId}`;
}

function setupEventListeners() {
    // Back button
    document.getElementById('backBtn').addEventListener('click', () => {
        if (confirm('Are you sure you want to leave this group?')) {
            disconnectWebSocket();
            window.location.href = 'index.html';
        }
    });

    // Logout button
    document.getElementById('logoutBtn').addEventListener('click', () => {
        if (confirm('Are you sure you want to logout?')) {
            localStorage.clear();
            disconnectWebSocket();
            window.location.href = 'index.html';
        }
    });

    // Message form
    const messageForm = document.getElementById('messageForm');
    messageForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage();
    });

    // Select video button
    document.getElementById('selectVideoBtn').addEventListener('click', () => {
        const videoList = document.getElementById('videoList');
        videoList.classList.toggle('hidden');
    });

    // Close video list when clicking outside
    document.addEventListener('click', (e) => {
        const videoList = document.getElementById('videoList');
        const selectBtn = document.getElementById('selectVideoBtn');
        
        if (!videoList.contains(e.target) && !selectBtn.contains(e.target)) {
            videoList.classList.add('hidden');
        }
    });
}

// ============================================
// WebSocket Functions
// ============================================

function connectWebSocket() {
    console.log('Connecting to WebSocket...');
    console.log('Group ID:', groupId);
    console.log('Token length:', accessToken ? accessToken.length : 0);
    
    updateConnectionStatus('connecting');

    try {
        const wsUrl = `${CHAT_WS_URL}/ws/group/${groupId}?token=${accessToken}`;
        console.log('WebSocket URL:', wsUrl.substring(0, 60) + '...');
        
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('✅ WebSocket connected successfully');
            updateConnectionStatus('connected');
            reconnectAttempts = 0;
            addSystemMessage('Connected to group chat', 'success');
        };

        ws.onmessage = (event) => {
            console.log('📩 Received message:', event.data);
            try {
                const data = JSON.parse(event.data);
                handleIncomingMessage(data);
            } catch (error) {
                console.error('Error parsing message:', error);
            }
        };

        ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            updateConnectionStatus('disconnected');
        };

        ws.onclose = (event) => {
            console.log('🔌 WebSocket closed:', event.code, event.reason);
            updateConnectionStatus('disconnected');
            
            // Attempt to reconnect
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                addSystemMessage(`Connection lost. Reconnecting... (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`, 'error');
                setTimeout(connectWebSocket, 3000 * reconnectAttempts);
            } else {
                addSystemMessage('Failed to reconnect. Please refresh the page.', 'error');
            }
        };
    } catch (error) {
        console.error('Error creating WebSocket:', error);
        updateConnectionStatus('disconnected');
    }
}

function disconnectWebSocket() {
    if (ws) {
        ws.close();
        ws = null;
    }
}

function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const text = messageInput.value.trim();

    console.log('sendMessage called with text:', text);

    if (!text) {
        console.log('Empty message, returning');
        return;
    }

    console.log('WebSocket state:', ws ? ws.readyState : 'ws is null');

    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.error('WebSocket not ready. State:', ws ? ws.readyState : 'null');
        addSystemMessage('Not connected. Please wait...', 'error');
        return;
    }

    try {
        const message = {
            text: text,
            group_id: parseInt(groupId)
        };

        console.log('Sending message:', message);
        ws.send(JSON.stringify(message));
        console.log('Message sent successfully');
        
        messageInput.value = '';
        messageInput.focus();
    } catch (error) {
        console.error('Error sending message:', error);
        addSystemMessage('Failed to send message', 'error');
    }
}

function handleIncomingMessage(data) {
    console.log('Received message:', data);

    const type = data.type || 'message';

    if (type === 'message') {
        // Regular chat message
        addChatMessage(data);
    } else if (type === 'add') {
        // User added to group
        addSystemMessage(data.text, 'add');
    } else if (type === 'leave') {
        // User removed from group
        addSystemMessage(data.text, 'leave');
    } else if (type === 'user_left') {
        // User disconnected
        addSystemMessage(data.message, 'warning');
    } else if (type === 'video_control') {
        // Handle video synchronization
        handleVideoControl(data);
    } else if (type === 'video_sync') {
        // Handle initial video sync when joining
        handleVideoSync(data);
    }
}

function handleVideoControl(data) {
    // Ignore our own video control messages to prevent loops
    if (data.user === userEmail) {
        return;
    }

    const videoPlayer = document.getElementById('videoPlayer');
    const action = data.video_action;
    
    console.log('📹 Video control received:', action, 'from', data.user);
    
    // Set flag to ignore events triggered by us
    ignoreVideoEvents = true;
    
    try {
        switch (action) {
            case 'play':
                if (data.video_time !== undefined && data.video_time !== null) {
                    videoPlayer.currentTime = data.video_time;
                }
                videoPlayer.play().catch(e => console.error('Error playing video:', e));
                addSystemMessage(`${data.user} played the video`, 'info');
                break;
                
            case 'pause':
                if (data.video_time !== undefined && data.video_time !== null) {
                    videoPlayer.currentTime = data.video_time;
                }
                videoPlayer.pause();
                addSystemMessage(`${data.user} paused the video`, 'info');
                break;
                
            case 'seek':
                if (data.video_time !== undefined && data.video_time !== null) {
                    videoPlayer.currentTime = data.video_time;
                    addSystemMessage(`${data.user} seeked to ${formatVideoTime(data.video_time)}`, 'info');
                }
                break;
                
            case 'change_video':
                if (data.video_name) {
                    const videoSource = videoPlayer.querySelector('source');
                    videoSource.src = `${STREAM_API_URL}/api/stream/${data.video_name}`;
                    videoPlayer.load();
                    if (data.video_time !== undefined && data.video_time !== null) {
                        videoPlayer.currentTime = data.video_time;
                    }
                    currentVideoName = data.video_name;
                    addSystemMessage(`${data.user} changed video to: ${data.video_name}`, 'info');
                }
                break;
        }
    } finally {
        // Reset flag after a short delay to allow the action to complete
        setTimeout(() => {
            ignoreVideoEvents = false;
        }, 500);
    }
}

function handleVideoSync(data) {
    const videoPlayer = document.getElementById('videoPlayer');
    
    console.log('🎬 Syncing with group video:', data.video_name, 'at', data.video_time, 'playing:', data.is_playing);
    
    // Set flag to ignore events triggered by us
    ignoreVideoEvents = true;
    
    if (!data.video_name) {
        console.warn('No video name in sync data');
        ignoreVideoEvents = false;
        return;
    }
    
    const videoSource = videoPlayer.querySelector('source');
    videoSource.src = `${STREAM_API_URL}/api/stream/${data.video_name}`;
    currentVideoName = data.video_name;
    
    videoPlayer.load();
    
    // Function to apply video state
    const applyVideoState = () => {
        console.log('Applying video state: time=', data.video_time, 'playing=', data.is_playing);
        
        if (data.video_time !== undefined && data.video_time !== null) {
            videoPlayer.currentTime = data.video_time;
            console.log('Set video time to:', data.video_time);
        }
        
        if (data.is_playing) {
            console.log('Auto-playing video...');
            videoPlayer.play()
                .then(() => console.log('✅ Video playing successfully'))
                .catch(e => {
                    console.error('❌ Error auto-playing video:', e);
                    addSystemMessage('Click the video to start playback (browser autoplay policy)', 'warning');
                });
        } else {
            console.log('Video is paused, not auto-playing');
        }
        
        // Reset flag after a delay
        setTimeout(() => {
            ignoreVideoEvents = false;
            console.log('Video sync complete, re-enabled event broadcasting');
        }, 1000);
    };
    
    // Wait for video to be ready
    if (videoPlayer.readyState >= 1) {
        // Metadata already loaded
        console.log('Video metadata already loaded, applying state immediately');
        applyVideoState();
    } else {
        // Wait for metadata to load
        console.log('Waiting for video metadata to load...');
        videoPlayer.addEventListener('loadedmetadata', applyVideoState, { once: true });
        
        // Fallback timeout in case loadedmetadata doesn't fire
        setTimeout(() => {
            if (ignoreVideoEvents) {
                console.log('Timeout reached, forcing video state apply');
                applyVideoState();
            }
        }, 3000);
    }
    
    addSystemMessage(`Synced to group video: ${data.video_name}`, 'success');
}

// ============================================
// UI Functions
// ============================================

function updateConnectionStatus(status) {
    const statusElement = document.getElementById('connectionStatus');
    const statusText = statusElement.querySelector('.status-text');

    statusElement.className = 'connection-status ' + status;

    switch (status) {
        case 'connected':
            statusText.textContent = 'Connected';
            break;
        case 'connecting':
            statusText.textContent = 'Connecting...';
            break;
        case 'disconnected':
            statusText.textContent = 'Disconnected';
            break;
    }
}

function addChatMessage(data) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    
    const isOwnMessage = data.user === userEmail;
    messageDiv.className = `message ${isOwnMessage ? 'user' : 'other'}`;

    const time = data.created_at ? formatTime(data.created_at) : formatTime(new Date().toISOString());
    
    messageDiv.innerHTML = `
        <div class="message-header">
            <span class="message-sender">${isOwnMessage ? 'You' : data.user}</span>
            <span class="message-time">${time}</span>
        </div>
        <div class="message-text">${escapeHtml(data.text)}</div>
    `;

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function addSystemMessage(text, type = 'info') {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    
    messageDiv.className = `message system ${type}`;
    messageDiv.innerHTML = `<div class="message-text">${escapeHtml(text)}</div>`;

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function scrollToBottom() {
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function formatTime(isoString) {
    const date = new Date(isoString);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// Video Functions
// ============================================

async function loadVideos() {
    try {
        const response = await fetch(`${STREAM_API_URL}/api/videos`);
        
        if (!response.ok) {
            console.error('Failed to load videos');
            return;
        }

        const data = await response.json();
        displayVideos(data.videos);
    } catch (error) {
        console.error('Error loading videos:', error);
    }
}

function displayVideos(videos) {
    const videoItems = document.getElementById('videoItems');
    
    if (!videos || videos.length === 0) {
        videoItems.innerHTML = '<p style="color: #64748b; font-size: 14px;">No videos available</p>';
        return;
    }

    videoItems.innerHTML = '';
    
    videos.forEach(video => {
        const videoItem = document.createElement('div');
        videoItem.className = 'video-item';
        videoItem.innerHTML = `
            <div class="video-item-name">${video.name}</div>
            <div class="video-item-size">${formatFileSize(video.size)}</div>
        `;
        
        videoItem.addEventListener('click', () => {
            selectVideo(video.name);
        });
        
        videoItems.appendChild(videoItem);
    });
}

function selectVideo(videoName) {
    const videoPlayer = document.getElementById('videoPlayer');
    const videoSource = videoPlayer.querySelector('source');
    
    videoSource.src = `${STREAM_API_URL}/api/stream/${videoName}`;
    videoPlayer.load();
    videoPlayer.play();
    
    currentVideoName = videoName;
    
    // Hide video list
    document.getElementById('videoList').classList.add('hidden');
    
    addSystemMessage(`Now playing: ${videoName}`, 'info');
    
    // Broadcast video change to group
    sendVideoControl('change_video', 0, videoName);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

// ============================================
// Video Synchronization Functions
// ============================================

function setupVideoEventListeners() {
    const videoPlayer = document.getElementById('videoPlayer');
    
    // Play event
    videoPlayer.addEventListener('play', () => {
        console.log('🎬 Video play event, ignoreVideoEvents:', ignoreVideoEvents);
        if (!ignoreVideoEvents) {
            console.log('Broadcasting play event to group');
            sendVideoControl('play', videoPlayer.currentTime, currentVideoName);
        } else {
            console.log('Ignoring play event (sync in progress)');
        }
    });
    
    // Pause event
    videoPlayer.addEventListener('pause', () => {
        console.log('⏸️ Video pause event, ignoreVideoEvents:', ignoreVideoEvents);
        if (!ignoreVideoEvents) {
            console.log('Broadcasting pause event to group');
            sendVideoControl('pause', videoPlayer.currentTime, currentVideoName);
        } else {
            console.log('Ignoring pause event (sync in progress)');
        }
    });
    
    // Seeked event (user jumps to different time)
    videoPlayer.addEventListener('seeked', () => {
        console.log('⏩ Video seeked event, ignoreVideoEvents:', ignoreVideoEvents);
        if (!ignoreVideoEvents) {
            console.log('Broadcasting seek event to group');
            sendVideoControl('seek', videoPlayer.currentTime, currentVideoName);
        } else {
            console.log('Ignoring seek event (sync in progress)');
        }
    });
}

function sendVideoControl(action, videoTime, videoName = null) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.warn('WebSocket not ready, cannot send video control');
        return;
    }
    
    try {
        const message = {
            type: 'video_control',
            video_action: action,
            video_time: videoTime,
            video_name: videoName || currentVideoName,
            group_id: parseInt(groupId)
        };
        
        console.log('📹 Sending video control:', message);
        ws.send(JSON.stringify(message));
    } catch (error) {
        console.error('Error sending video control:', error);
    }
}

function formatVideoTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// ============================================
// Keyboard Shortcuts
// ============================================

document.addEventListener('keydown', (e) => {
    // Focus message input on '/' key
    if (e.key === '/' && document.activeElement.id !== 'messageInput') {
        e.preventDefault();
        document.getElementById('messageInput').focus();
    }
    
    // Send message on Enter (without shift)
    if (e.key === 'Enter' && !e.shiftKey && document.activeElement.id === 'messageInput') {
        e.preventDefault();
        sendMessage();
    }
});
