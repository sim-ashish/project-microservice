// Video player elements
const videoPlayer = document.getElementById('videoPlayer');
const videoSource = document.getElementById('videoSource');
const videoInfo = document.getElementById('videoInfo');
const videoList = document.getElementById('videoList');
const refreshBtn = document.getElementById('refreshBtn');
const videoFile = document.getElementById('videoFile');
const uploadBtn = document.getElementById('uploadBtn');
const uploadProgress = document.getElementById('uploadProgress');

let currentVideo = null;

// Load videos on page load
document.addEventListener('DOMContentLoaded', () => {
    loadVideos();
});

// Refresh button click handler
refreshBtn.addEventListener('click', () => {
    loadVideos();
});

// Upload button click handler
uploadBtn.addEventListener('click', async () => {
    const files = videoFile.files;
    
    if (files.length === 0) {
        uploadProgress.innerHTML = '<p style="color: #f44336;">Please select video files to upload</p>';
        return;
    }
    
    uploadBtn.disabled = true;
    uploadProgress.innerHTML = '<p>Uploading...</p>';
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        await uploadVideo(file, i + 1, files.length);
    }
    
    uploadBtn.disabled = false;
    videoFile.value = '';
    
    // Refresh video list after upload
    setTimeout(() => {
        loadVideos();
    }, 1000);
});

// Function to upload a single video
async function uploadVideo(file, index, total) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        uploadProgress.innerHTML = `<p>Uploading ${index}/${total}: ${file.name}...</p>`;
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            uploadProgress.innerHTML = `<p style="color: #4caf50;">✓ ${index}/${total} uploaded: ${file.name}</p>`;
        } else {
            uploadProgress.innerHTML = `<p style="color: #f44336;">✗ Failed to upload ${file.name}: ${result.detail}</p>`;
        }
        
        // Wait a bit before next upload
        await new Promise(resolve => setTimeout(resolve, 500));
        
    } catch (error) {
        console.error('Upload error:', error);
        uploadProgress.innerHTML = `<p style="color: #f44336;">✗ Error uploading ${file.name}</p>`;
    }
}

// Function to load available videos
async function loadVideos() {
    try {
        videoList.innerHTML = '<p class="loading">Loading videos...</p>';
        
        const response = await fetch('/api/videos');
        const data = await response.json();
        
        if (data.videos.length === 0) {
            videoList.innerHTML = `
                <p class="loading">
                    No videos found. Add video files to the videos/ directory.
                </p>
            `;
            return;
        }
        
        // Clear the list
        videoList.innerHTML = '';
        
        // Create video items
        data.videos.forEach(video => {
            const videoItem = createVideoItem(video);
            videoList.appendChild(videoItem);
        });
        
    } catch (error) {
        console.error('Error loading videos:', error);
        videoList.innerHTML = `
            <p class="loading" style="color: #d32f2f;">
                Error loading videos. Make sure the server is running.
            </p>
        `;
    }
}

// Function to create a video list item
function createVideoItem(video) {
    const div = document.createElement('div');
    div.className = 'video-item';
    
    const name = document.createElement('div');
    name.className = 'video-name';
    name.textContent = video.name;
    
    const size = document.createElement('div');
    size.className = 'video-size';
    size.textContent = formatFileSize(video.size);
    
    div.appendChild(name);
    div.appendChild(size);
    
    // Click handler to play video
    div.addEventListener('click', () => {
        playVideo(video.name, div);
    });
    
    return div;
}

// Function to play a video
function playVideo(videoName, itemElement) {
    // Update active state
    document.querySelectorAll('.video-item').forEach(item => {
        item.classList.remove('active');
    });
    itemElement.classList.add('active');
    
    // Update video source with stream endpoint (now supports range)
    const streamUrl = `/api/stream/${encodeURIComponent(videoName)}`;
    videoSource.src = streamUrl;
    
    // Load and play the video
    videoPlayer.load();
    videoPlayer.play().catch(error => {
        console.error('Error playing video:', error);
        updateVideoInfo(`Error: Could not play ${videoName}`);
    });
    
    // Update video info
    currentVideo = videoName;
    updateVideoInfo(`Now playing: ${videoName}`);
}

// Function to update video info display
function updateVideoInfo(message) {
    videoInfo.innerHTML = `<p>${message}</p>`;
}

// Function to format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

// Video event listeners
videoPlayer.addEventListener('loadstart', () => {
    updateVideoInfo(`Loading ${currentVideo}...`);
});

videoPlayer.addEventListener('loadedmetadata', () => {
    const duration = Math.floor(videoPlayer.duration);
    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    updateVideoInfo(`Now playing: ${currentVideo} (${minutes}:${seconds.toString().padStart(2, '0')})`);
});

videoPlayer.addEventListener('error', (e) => {
    console.error('Video error:', e);
    updateVideoInfo(`Error playing ${currentVideo}`);
});

videoPlayer.addEventListener('ended', () => {
    updateVideoInfo(`Finished playing: ${currentVideo}`);
});

// Handle seeking
videoPlayer.addEventListener('seeking', () => {
    console.log('Seeking to:', videoPlayer.currentTime);
});

videoPlayer.addEventListener('seeked', () => {
    console.log('Seeked to:', videoPlayer.currentTime);
});
