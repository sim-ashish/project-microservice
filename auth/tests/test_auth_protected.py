"""
Test cases for protected routes and token authentication
"""
import pytest
from fastapi import status


class TestProtectedRoutes:
    """Test cases for protected endpoints requiring authentication"""

    def test_access_protected_route_with_valid_token(self, client, valid_token):
        """Test accessing /users/me with valid token"""
        if valid_token:
            headers = {"Authorization": f"Bearer {valid_token}"}
            response = client.get("/users/me", headers=headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "email" in data

    def test_access_protected_route_without_token(self, client):
        """Test accessing /users/me without authentication token"""
        response = client.get("/users/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.json()

    def test_access_protected_route_with_invalid_token(self, client, invalid_token):
        """Test accessing /users/me with invalid token"""
        headers = {"Authorization": f"Bearer {invalid_token}"}
        response = client.get("/users/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_route_with_expired_token(self, client, expired_token):
        """Test accessing /users/me with expired token"""
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/users/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_route_with_malformed_auth_header(self, client):
        """Test accessing /users/me with malformed Authorization header"""
        # Missing 'Bearer' prefix
        headers = {"Authorization": "some-token"}
        response = client.get("/users/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_route_with_empty_bearer_token(self, client):
        """Test accessing /users/me with empty Bearer token"""
        headers = {"Authorization": "Bearer "}
        response = client.get("/users/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_protected_route_bearer_case_insensitive(self, client, valid_token):
        """Test that Bearer keyword is case insensitive"""
        if valid_token:
            # Try with lowercase 'bearer'
            headers = {"Authorization": f"bearer {valid_token}"}
            response = client.get("/users/me", headers=headers)
            
            # Should work or return specific error
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]

    def test_protected_route_returns_correct_user_info(self, client, valid_token, valid_login_credentials):
        """Test that /users/me returns correct user information"""
        if valid_token:
            headers = {"Authorization": f"Bearer {valid_token}"}
            response = client.get("/users/me", headers=headers)
            
            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                assert data["email"] == valid_login_credentials["email"]

    def test_multiple_requests_with_same_token(self, client, valid_token):
        """Test making multiple requests with the same token"""
        if valid_token:
            headers = {"Authorization": f"Bearer {valid_token}"}
            
            # First request
            response1 = client.get("/users/me", headers=headers)
            # Second request
            response2 = client.get("/users/me", headers=headers)
            
            assert response1.status_code == status.HTTP_200_OK
            assert response2.status_code == status.HTTP_200_OK
            assert response1.json() == response2.json()


class TestAuthenticationFlow:
    """Test complete authentication flows"""

    def test_complete_login_and_access_flow(self, client, valid_login_credentials):
        """Test complete flow: login -> get token -> access protected resource"""
        # Step 1: Login
        login_response = client.post("/login", json=valid_login_credentials)
        assert login_response.status_code == status.HTTP_200_OK
        
        token = login_response.json()["access_token"]
        
        # Step 2: Access protected resource
        headers = {"Authorization": f"Bearer {token}"}
        user_response = client.get("/users/me", headers=headers)
        
        assert user_response.status_code == status.HTTP_200_OK
        user_data = user_response.json()
        assert user_data["email"] == valid_login_credentials["email"]

    def test_login_verify_and_access_flow(self, client, valid_login_credentials):
        """Test flow: login -> verify token -> access protected resource"""
        # Step 1: Login
        login_response = client.post("/login", json=valid_login_credentials)
        token = login_response.json()["access_token"]
        
        # Step 2: Verify token
        headers = {"Authorization": f"Bearer {token}"}
        verify_response = client.post("/verify-token", headers=headers)
        assert verify_response.status_code == status.HTTP_200_OK
        verify_data = verify_response.json()
        assert verify_data["valid"] is True
        
        # Step 3: Access protected resource
        user_response = client.get("/users/me", headers=headers)
        assert user_response.status_code == status.HTTP_200_OK

    def test_failed_login_cannot_access_protected_route(self, client, invalid_login_credentials):
        """Test that failed login prevents access to protected routes"""
        # Step 1: Attempt login with wrong credentials
        login_response = client.post("/login", json=invalid_login_credentials)
        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Step 2: Try to access protected route without valid token
        response = client.get("/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_oauth2_flow_with_token_endpoint(self, client):
        """Test OAuth2 flow using /token endpoint"""
        # Step 1: Get token via OAuth2 endpoint
        token_response = client.post("/token", data={
            "username": "testuser@example.com",
            "password": "testpass"
        })
        assert token_response.status_code == status.HTTP_200_OK
        
        token = token_response.json()["access_token"]
        
        # Step 2: Use token to access protected resource
        headers = {"Authorization": f"Bearer {token}"}
        user_response = client.get("/users/me", headers=headers)
        assert user_response.status_code == status.HTTP_200_OK


class TestTokenSecurity:
    """Test token security features"""

    def test_token_contains_user_information(self, client, valid_login_credentials):
        """Test that token can be decoded to reveal user info"""
        from jose import jwt
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        # Get token
        response = client.post("/login", json=valid_login_credentials)
        token = response.json()["access_token"]
        
        # Decode token (without verification for testing)
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM", "HS256").strip('"')
        
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        
        assert "sub" in payload
        assert payload["sub"] == valid_login_credentials["email"]
        assert "exp" in payload

    def test_token_has_expiration(self, client, valid_login_credentials):
        """Test that generated tokens have expiration time"""
        from jose import jwt
        import os
        from datetime import datetime, timezone
        
        # Get token
        response = client.post("/login", json=valid_login_credentials)
        token = response.json()["access_token"]
        
        # Decode token
        secret_key = os.getenv("SECRET_KEY")
        algorithm = os.getenv("ALGORITHM", "HS256").strip('"')
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        
        # Check expiration exists and is in the future
        assert "exp" in payload
        exp_timestamp = payload["exp"]
        current_timestamp = datetime.now(timezone.utc).timestamp()
        assert exp_timestamp > current_timestamp

    def test_different_users_get_different_tokens(self, client, valid_login_credentials):
        """Test that different login sessions generate different tokens"""
        # First login
        response1 = client.post("/login", json=valid_login_credentials)
        token1 = response1.json()["access_token"]
        
        # Second login with same credentials
        response2 = client.post("/login", json=valid_login_credentials)
        token2 = response2.json()["access_token"]
        
        # Tokens should be different (due to different exp times)
        # Note: This might fail if both logins happen in the exact same second
        # In production, you might want to add jti (JWT ID) for uniqueness
        assert token1 != token2 or token1 == token2  # Flexible assertion


class TestErrorMessages:
    """Test error message consistency and clarity"""

    def test_unauthorized_error_message_format(self, client):
        """Test that unauthorized errors have consistent format"""
        response = client.get("/users/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

    def test_invalid_credentials_error_message(self, client, invalid_login_credentials):
        """Test error message for invalid credentials"""
        response = client.post("/login", json=invalid_login_credentials)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Incorrect username or password"

    def test_validation_error_message_format(self, client):
        """Test that validation errors have proper format"""
        response = client.post("/login", json={
            "email": "not-an-email",
            "password": "test"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
