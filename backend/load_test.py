"""
Load Testing Script for UnderwritePro SaaS
Uses Locust to simulate 500+ concurrent users
"""
from locust import HttpUser, task, between
import random
import json

class UnderwriteProUser(HttpUser):
    """Simulated user for load testing"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts - register and login"""
        # Register a new user
        timestamp = int(random.random() * 1000000)
        self.email = f"loadtest_{timestamp}@example.com"
        self.password = "LoadTest123"
        
        response = self.client.post("/api/auth/register", json={
            "email": self.email,
            "password": self.password,
            "full_name": f"Load Test User {timestamp}",
            "organization_name": f"Load Test Org {timestamp}"
        })
        
        if response.status_code == 201:
            data = response.json()
            self.user_id = data["id"]
            self.org_id = data["organization_id"]
        
        # Login
        response = self.client.post("/api/auth/login", data={
            "username": self.email,
            "password": self.password
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
        
        # Create a borrower
        if self.token:
            response = self.client.post("/api/borrowers", 
                headers=self.headers,
                json={
                    "name": f"Test Borrower {timestamp}",
                    "entity_type": random.choice(["individual", "llc", "corp", "partnership"])
                }
            )
            if response.status_code == 201:
                self.borrower_id = response.json()["id"]
            else:
                self.borrower_id = None
    
    @task(10)
    def view_dashboard(self):
        """View dashboard - most common action"""
        if self.token:
            self.client.get("/api/auth/me", headers=self.headers)
    
    @task(8)
    def list_deals(self):
        """List deals"""
        if self.token:
            self.client.get("/api/deals", headers=self.headers)
    
    @task(5)
    def list_borrowers(self):
        """List borrowers"""
        if self.token:
            self.client.get("/api/borrowers", headers=self.headers)
    
    @task(3)
    def create_deal(self):
        """Create a new deal"""
        if self.token and self.borrower_id:
            self.client.post("/api/deals",
                headers=self.headers,
                json={
                    "borrower_id": self.borrower_id,
                    "deal_type": random.choice(["purchase", "refi"]),
                    "loan_amount": random.randint(100000, 1000000),
                    "appraised_value": random.randint(125000, 1250000),
                    "interest_rate": round(random.uniform(0.04, 0.08), 3)
                }
            )
    
    @task(2)
    def health_check(self):
        """Health check"""
        self.client.get("/api/health")

# Run with: locust -f load_test.py --host=http://localhost:8000
# Then open http://localhost:8089 to configure and start the test
