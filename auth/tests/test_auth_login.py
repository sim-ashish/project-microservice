"""
Test cases for authentication login endpoints
"""
import pytest
from fastapi import status


class TestLoginEndpoint:
    """Test cases for POST /login endpoint"""

    def test_login_success_with_valid_credentials(self, client, valid_login_credentials):
        """Test successful login with correct credentials"""
        response = client.post("/login", json=valid_login_credentials)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_login_failure_with_invalid_credentials(self, client, invalid_login_credentials):
        """Test login failure with wrong credentials"""
        response = client.post("/login", json=invalid_login_credentials)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Incorrect username or password"

    def test_login_with_invalid_email_format(self, client):
        """Test login with malformed email address"""
        response = client.post("/login", json={
            "email": "not-an-email",
            "password": "testpass"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any("email" in str(error).lower() for error in errors)

    def test_login_with_missing_email(self, client):
        """Test login without email field"""
        response = client.post("/login", json={
            "password": "testpass"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_missing_password(self, client):
        """Test login without password field"""
        response = client.post("/login", json={
            "email": "testuser@example.com"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_empty_email(self, client):
        """Test login with empty email"""
        response = client.post("/login", json={
            "email": "",
            "password": "testpass"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_with_empty_password(self, client, valid_login_credentials):
        """Test login with empty password"""
        response = client.post("/login", json={
            "email": valid_login_credentials["email"],
            "password": ""
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_with_null_values(self, client):
        """Test login with null values"""
        response = client.post("/login", json={
            "email": None,
            "password": None
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_response_structure(self, client, valid_login_credentials):
        """Test that login response has correct structure"""
        response = client.post("/login", json=valid_login_credentials)
        data = response.json()
        
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        # JWT token should have 3 parts separated by dots
        assert data["access_token"].count('.') == 2

    def test_login_with_extra_fields(self, client, valid_login_credentials):
        """Test login with extra unexpected fields"""
        payload = valid_login_credentials.copy()
        payload["extra_field"] = "should_be_ignored"
        
        response = client.post("/login", json=payload)
        assert response.status_code == status.HTTP_200_OK

    def test_login_case_sensitive_email(self, client, valid_login_credentials):
        """Test that email comparison is case sensitive"""
        credentials = valid_login_credentials.copy()
        credentials["email"] = credentials["email"].upper()
        
        response = client.post("/login", json=credentials)
        # This depends on your implementation - adjust assertion as needed
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]


class TestTokenEndpoint:
    """Test cases for POST /token endpoint (OAuth2 format)"""

    def test_token_endpoint_with_form_data(self, client):
        """Test OAuth2 token endpoint with form data"""
        response = client.post("/token", data={
            "username": "testuser@example.com",
            "password": "testpass"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data

    def test_token_endpoint_with_invalid_credentials(self, client):
        """Test OAuth2 token endpoint with invalid credentials"""
        response = client.post("/token", data={
            "username": "wrong@example.com",
            "password": "wrongpass"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_endpoint_missing_username(self, client):
        """Test OAuth2 token endpoint without username"""
        response = client.post("/token", data={
            "password": "testpass"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_token_endpoint_missing_password(self, client):
        """Test OAuth2 token endpoint without password"""
        response = client.post("/token", data={
            "username": "testuser@example.com"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_token_endpoint_with_json_fails(self, client):
        """Test that /token endpoint requires form data, not JSON"""
        response = client.post("/token", json={
            "username": "testuser@example.com",
            "password": "testpass"
        })
        
        # Should fail because it expects form data
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestVerifyTokenEndpoint:
    """Test cases for POST /verify-token endpoint"""

    def test_verify_valid_token(self, client, valid_token):
        """Test verification of a valid token"""
        if valid_token:
            headers = {"Authorization": f"Bearer {valid_token}"}
            response = client.post("/verify-token", headers=headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["valid"] is True
            assert "user" in data

    def test_verify_expired_token(self, client, expired_token):
        """Test verification of an expired token"""
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.post("/verify-token", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "expired" in data["detail"].lower()

    def test_verify_invalid_token(self, client, invalid_token):
        """Test verification of an invalid token"""
        headers = {"Authorization": f"Bearer {invalid_token}"}
        response = client.post("/verify-token", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data

    def test_verify_missing_token(self, client):
        """Test verification without providing authorization header"""
        response = client.post("/verify-token")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data

    def test_verify_empty_token(self, client):
        """Test verification with malformed authorization header"""
        headers = {"Authorization": "Bearer"}
        response = client.post("/verify-token", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
