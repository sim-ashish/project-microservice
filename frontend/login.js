// Login page JavaScript
const API_BASE_URL = 'http://localhost:8000';
const CHAT_WS_URL = 'ws://localhost:8001';

document.addEventListener('DOMContentLoaded', () => {
    const joinForm = document.getElementById('joinForm');
    const errorMessage = document.getElementById('errorMessage');
    const groupIdInput = document.getElementById('groupId');
    const accessTokenInput = document.getElementById('accessToken');

    // Load saved values from localStorage
    const savedGroupId = localStorage.getItem('groupId');
    const savedToken = localStorage.getItem('accessToken');
    
    if (savedGroupId) {
        groupIdInput.value = savedGroupId;
    }
    
    if (savedToken) {
        accessTokenInput.value = savedToken;
    }

    joinForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const groupId = groupIdInput.value.trim();
        const accessToken = accessTokenInput.value.trim();
        
        // Validate inputs
        if (!groupId || !accessToken) {
            showError('Please fill in all fields');
            return;
        }

        // Disable form while verifying
        const submitBtn = joinForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span>Verifying...</span>';
        
        try {
            // Verify token and group access
            const isValid = await verifyGroupAccess(groupId, accessToken);
            
            if (isValid) {
                // Save to localStorage
                localStorage.setItem('groupId', groupId);
                localStorage.setItem('accessToken', accessToken);
                
                // Redirect to chat page
                window.location.href = `chat.html`;
            } else {
                showError('Invalid credentials or you are not a member of this group');
            }
        } catch (error) {
            console.error('Error verifying access:', error);
            showError(error.message || 'Failed to verify access. Please check your credentials.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `
                <span>Join Group</span>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M4 10H16M16 10L11 5M16 10L11 15" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            `;
        }
    });

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.add('show');
        
        setTimeout(() => {
            errorMessage.classList.remove('show');
        }, 5000);
    }

    async function verifyGroupAccess(groupId, token) {
        try {
            const response = await fetch(`${API_BASE_URL}/verify-group-access/${groupId}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                // Save user info for later use
                localStorage.setItem('userEmail', data.user);
                localStorage.setItem('groupName', data.group_name);
                return true;
            } else if (response.status === 403) {
                throw new Error('You are not a member of this group');
            } else if (response.status === 401) {
                throw new Error('Invalid or expired token');
            } else if (response.status === 404) {
                throw new Error('Group not found');
            } else {
                throw new Error('Failed to verify access');
            }
        } catch (error) {
            if (error.message) {
                throw error;
            }
            throw new Error('Cannot connect to auth service. Please ensure it is running.');
        }
    }

    // Add input validation and formatting
    groupIdInput.addEventListener('input', (e) => {
        // Only allow positive integers
        e.target.value = e.target.value.replace(/[^0-9]/g, '');
    });

    accessTokenInput.addEventListener('paste', (e) => {
        // Clean up pasted token (remove quotes if any)
        setTimeout(() => {
            let token = e.target.value.trim();
            token = token.replace(/^["']|["']$/g, '');
            e.target.value = token;
        }, 0);
    });
});
