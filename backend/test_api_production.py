#!/usr/bin/env python3
"""
Comprehensive API Test Suite for UnderwritePro SaaS
Tests all endpoints, security features, and edge cases
"""
import requests
import json
import time
from typing import Optional

BASE_URL = "http://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class APITester:
    def __init__(self):
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.org_id: Optional[str] = None
        self.borrower_id: Optional[str] = None
        self.deal_id: Optional[str] = None
        
        self.passed = 0
        self.failed = 0
        self.total = 0
    
    def test(self, name: str, func):
        """Run a test and track results"""
        self.total += 1
        print(f"\n{Colors.BLUE}[TEST {self.total}]{Colors.END} {name}")
        try:
            func()
            self.passed += 1
            print(f"{Colors.GREEN}✓ PASSED{Colors.END}")
            return True
        except AssertionError as e:
            self.failed += 1
            print(f"{Colors.RED}✗ FAILED: {e}{Colors.END}")
            return False
        except Exception as e:
            self.failed += 1
            print(f"{Colors.RED}✗ ERROR: {e}{Colors.END}")
            return False
    
    def assert_status(self, response, expected_status):
        """Assert response status code"""
        if response.status_code != expected_status:
            raise AssertionError(
                f"Expected status {expected_status}, got {response.status_code}. "
                f"Response: {response.text}"
            )
    
    def assert_has_keys(self, data: dict, keys: list):
        """Assert dictionary has required keys"""
        for key in keys:
            if key not in data:
                raise AssertionError(f"Missing key: {key}")
    
    # ==================== Health & Monitoring Tests ====================
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        self.assert_status(response, 200)
        data = response.json()
        self.assert_has_keys(data, ["status", "timestamp", "database"])
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
    
    # ==================== Authentication Tests ====================
    
    def test_register_user(self):
        """Test user registration"""
        timestamp = int(time.time())
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": f"test_{timestamp}@example.com",
                "password": "SecurePass123",
                "full_name": "Test User",
                "organization_name": "Test Organization"
            }
        )
        self.assert_status(response, 201)
        data = response.json()
        self.assert_has_keys(data, ["id", "email", "full_name", "role", "organization_id"])
        self.user_id = data["id"]
        self.org_id = data["organization_id"]
        self.test_email = f"test_{timestamp}@example.com"
        self.test_password = "SecurePass123"
    
    def test_register_duplicate_email(self):
        """Test registration with duplicate email"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": self.test_email,
                "password": "AnotherPass123",
                "full_name": "Another User",
                "organization_name": "Another Org"
            }
        )
        self.assert_status(response, 400)
        data = response.json()
        assert "already registered" in data["detail"].lower()
    
    def test_register_weak_password(self):
        """Test registration with weak password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak",
                "full_name": "Weak User",
                "organization_name": "Weak Org"
            }
        )
        self.assert_status(response, 400)
    
    def test_login(self):
        """Test user login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data={
                "username": self.test_email,
                "password": self.test_password
            }
        )
        self.assert_status(response, 200)
        data = response.json()
        self.assert_has_keys(data, ["access_token", "token_type"])
        assert data["token_type"] == "bearer"
        self.token = data["access_token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data={
                "username": self.test_email,
                "password": "WrongPassword123"
            }
        )
        self.assert_status(response, 401)
    
    def test_get_current_user(self):
        """Test getting current user info"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assert_status(response, 200)
        data = response.json()
        self.assert_has_keys(data, ["id", "email", "full_name", "role", "organization_id"])
        assert data["email"] == self.test_email
    
    def test_unauthorized_access(self):
        """Test accessing protected endpoint without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        self.assert_status(response, 401)
    
    def test_invalid_token(self):
        """Test accessing protected endpoint with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        self.assert_status(response, 401)
    
    # ==================== Borrower Tests ====================
    
    def test_create_borrower(self):
        """Test creating a borrower"""
        response = requests.post(
            f"{BASE_URL}/api/borrowers",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "name": "Test Borrower LLC",
                "entity_type": "llc",
                "tax_id": "12-3456789",
                "email": "borrower@example.com"
            }
        )
        self.assert_status(response, 201)
        data = response.json()
        self.assert_has_keys(data, ["id", "name"])
        self.borrower_id = data["id"]
    
    def test_list_borrowers(self):
        """Test listing borrowers"""
        response = requests.get(
            f"{BASE_URL}/api/borrowers",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assert_status(response, 200)
        data = response.json()
        self.assert_has_keys(data, ["items"])
        assert isinstance(data["items"], list)
    
    def test_create_borrower_invalid_entity_type(self):
        """Test creating borrower with invalid entity type"""
        response = requests.post(
            f"{BASE_URL}/api/borrowers",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "name": "Invalid Borrower",
                "entity_type": "invalid_type"
            }
        )
        self.assert_status(response, 422)
    
    # ==================== Deal Tests ====================
    
    def test_create_deal(self):
        """Test creating a deal"""
        response = requests.post(
            f"{BASE_URL}/api/deals",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "borrower_id": self.borrower_id,
                "deal_type": "purchase",
                "loan_amount": 500000,
                "appraised_value": 625000,
                "interest_rate": 0.065
            }
        )
        self.assert_status(response, 201)
        data = response.json()
        self.assert_has_keys(data, ["id", "borrower_id", "deal_type", "status"])
        self.deal_id = data["id"]
    
    def test_list_deals(self):
        """Test listing deals"""
        response = requests.get(
            f"{BASE_URL}/api/deals",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assert_status(response, 200)
        data = response.json()
        self.assert_has_keys(data, ["items"])
        assert isinstance(data["items"], list)
        assert len(data["items"]) > 0
    
    def test_get_deal_details(self):
        """Test getting deal details"""
        response = requests.get(
            f"{BASE_URL}/api/deals/{self.deal_id}",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assert_status(response, 200)
        data = response.json()
        self.assert_has_keys(data, ["id", "borrower", "deal_type", "status"])
    
    def test_create_deal_invalid_type(self):
        """Test creating deal with invalid type"""
        response = requests.post(
            f"{BASE_URL}/api/deals",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "borrower_id": self.borrower_id,
                "deal_type": "invalid_type",
                "loan_amount": 500000
            }
        )
        self.assert_status(response, 422)
    
    def test_create_deal_negative_amount(self):
        """Test creating deal with negative loan amount"""
        response = requests.post(
            f"{BASE_URL}/api/deals",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "borrower_id": self.borrower_id,
                "deal_type": "purchase",
                "loan_amount": -100000
            }
        )
        self.assert_status(response, 422)
    
    # ==================== Rate Limiting Tests ====================
    
    def test_rate_limiting(self):
        """Test rate limiting on health endpoint"""
        # Make many requests quickly
        responses = []
        for i in range(105):  # Limit is 100/minute
            response = requests.get(f"{BASE_URL}/api/health")
            responses.append(response.status_code)
        
        # At least one should be rate limited
        assert 429 in responses, "Rate limiting not working"
    
    # ==================== Security Tests ====================
    
    def test_sql_injection_attempt(self):
        """Test SQL injection protection"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data={
                "username": "admin' OR '1'='1",
                "password": "password"
            }
        )
        # Should fail authentication, not cause SQL error
        self.assert_status(response, 401)
    
    def test_xss_attempt(self):
        """Test XSS protection in user input"""
        response = requests.post(
            f"{BASE_URL}/api/borrowers",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "name": "<script>alert('xss')</script>",
                "entity_type": "llc"
            }
        )
        # Should either sanitize or reject
        if response.status_code == 201:
            data = response.json()
            assert "<script>" not in data["name"]
    
    def test_file_size_limit(self):
        """Test file upload size limit"""
        # Create a large fake file (>10MB)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        
        response = requests.post(
            f"{BASE_URL}/api/deals/{self.deal_id}/documents",
            headers={"Authorization": f"Bearer {self.token}"},
            files={"file": ("large.pdf", large_content, "application/pdf")},
            data={"document_type": "tax_return"}
        )
        # Should reject large file
        assert response.status_code in [413, 422, 400]
    
    # ==================== Summary ====================
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print(f"{Colors.BLUE}TEST SUMMARY{Colors.END}")
        print("="*60)
        print(f"Total Tests: {self.total}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.END}")
        
        pass_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        if self.failed == 0:
            print(f"\n{Colors.GREEN}✓ ALL TESTS PASSED!{Colors.END}")
        else:
            print(f"\n{Colors.YELLOW}⚠ SOME TESTS FAILED{Colors.END}")
        print("="*60)
    
    def run_all_tests(self):
        """Run all tests in order"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BLUE}UnderwritePro SaaS - Production API Test Suite{Colors.END}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")
        
        # Health tests
        print(f"\n{Colors.YELLOW}>>> Health & Monitoring Tests{Colors.END}")
        self.test("Health Check", self.test_health_check)
        
        # Authentication tests
        print(f"\n{Colors.YELLOW}>>> Authentication Tests{Colors.END}")
        self.test("Register User", self.test_register_user)
        self.test("Register Duplicate Email", self.test_register_duplicate_email)
        self.test("Register Weak Password", self.test_register_weak_password)
        self.test("Login", self.test_login)
        self.test("Login Invalid Credentials", self.test_login_invalid_credentials)
        self.test("Get Current User", self.test_get_current_user)
        self.test("Unauthorized Access", self.test_unauthorized_access)
        self.test("Invalid Token", self.test_invalid_token)
        
        # Borrower tests
        print(f"\n{Colors.YELLOW}>>> Borrower Tests{Colors.END}")
        self.test("Create Borrower", self.test_create_borrower)
        self.test("List Borrowers", self.test_list_borrowers)
        self.test("Create Borrower Invalid Entity Type", self.test_create_borrower_invalid_entity_type)
        
        # Deal tests
        print(f"\n{Colors.YELLOW}>>> Deal Tests{Colors.END}")
        self.test("Create Deal", self.test_create_deal)
        self.test("List Deals", self.test_list_deals)
        self.test("Get Deal Details", self.test_get_deal_details)
        self.test("Create Deal Invalid Type", self.test_create_deal_invalid_type)
        self.test("Create Deal Negative Amount", self.test_create_deal_negative_amount)
        
        # Security tests
        print(f"\n{Colors.YELLOW}>>> Security Tests{Colors.END}")
        self.test("SQL Injection Protection", self.test_sql_injection_attempt)
        self.test("XSS Protection", self.test_xss_attempt)
        
        # Rate limiting tests
        print(f"\n{Colors.YELLOW}>>> Rate Limiting Tests{Colors.END}")
        self.test("Rate Limiting", self.test_rate_limiting)
        
        # Print summary
        self.print_summary()
        
        return self.failed == 0

if __name__ == "__main__":
    tester = APITester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
