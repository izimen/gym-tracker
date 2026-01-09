import unittest
import requests
import os
import json
import uuid

# Configuration
BASE_URL = "http://127.0.0.1:5000"
TEST_USER = "security_test_user"
TEST_PASS = "secure_password_123"
VICTIM_USER = "victim_user"
VICTIM_PASS = "victim_password_123"

class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.session = requests.Session()
        # Create test users if they don't exist
        self._create_user(TEST_USER, TEST_PASS)
        self._create_user(VICTIM_USER, VICTIM_PASS)
        
        # Get Victim ID
        self.victim_id = self._login_get_id(VICTIM_USER, VICTIM_PASS)
        self.attacker_id = self._login_get_id(TEST_USER, TEST_PASS)

    def _create_user(self, username, password):
        try:
            requests.post(f"{BASE_URL}/api/auth/register", json={
                "username": username,
                "password": password
            })
        except:
            pass

    def _login_get_id(self, username, password):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": username,
            "password": password
        })
        if resp.status_code == 200:
            return resp.json().get('user_id')
        return None

    def test_security_headers(self):
        """Verify CSP and Security Headers are present"""
        resp = requests.get(f"{BASE_URL}/")
        
        self.assertIn('Content-Security-Policy', resp.headers, "CSP header missing")
        self.assertIn('Strict-Transport-Security', resp.headers, "HSTS header missing")
        self.assertIn('X-Content-Type-Options', resp.headers, "X-Content-Type-Options missing")
        self.assertIn("default-src 'self'", resp.headers['Content-Security-Policy'], "CSP too permissive?")

    def test_idor_create_workout(self):
        """
        IDOR TEST: Attacker attempts to create a workout for Victim.
        SECURE BEHAVIOR: Server ignores 'user_id' in payload and uses logged-in user (Attacker).
        """
        # Login as Attacker
        self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASS
        })
        
        target_date = "2025-09-09"
        
        # Payload tries to inject victim's ID
        payload = {
            "date": target_date,
            "body_parts": ["klata"],
            "user_id": self.victim_id  # <--- IDOR ATTEMPT (Ignored by secure server)
        }
        
        resp = self.session.post(f"{BASE_URL}/api/workout", json=payload)
        
        if resp.status_code == 200:
            # 1. Check if Victim has it (should NOT)
            victim_session = requests.Session()
            victim_session.post(f"{BASE_URL}/api/auth/login", json={
                "username": VICTIM_USER,
                "password": VICTIM_PASS
            })
            
            # Note: We use the session to auth, no need for user_id param anymore
            check_resp = victim_session.get(f"{BASE_URL}/api/workout/{target_date}")
            data = check_resp.json()
            
            # Verify Victim does NOT have this workout
            self.assertNotEqual(data.get('body_parts'), ['klata'], "IDOR FAILED: Victim received the workout!")
            
            # 2. Check if Attacker has it (should YES - because server used attacker's session)
            attacker_check = self.session.get(f"{BASE_URL}/api/workout/{target_date}")
            att_data = attacker_check.json()
            self.assertEqual(att_data.get('body_parts'), ['klata'], "Workout should be saved for Attacker (the logged in user)")
            print("\n[SUCCESS] IDOR Prevented: Workout saved for Attacker, not Victim.")

    def test_idor_delete_workout(self):
        """
        IDOR TEST: Attacker attempts to delete Victim's workout.
        SECURE BEHAVIOR: Server tries to delete for Attacker (effectively doing nothing or deleting attacker's own), Victim's data safe.
        """
        # 1. Create workout as Victim
        victim_session = requests.Session()
        victim_session.post(f"{BASE_URL}/api/auth/login", json={
            "username": VICTIM_USER,
            "password": VICTIM_PASS
        })
        date_to_delete = "2025-09-10"
        resp = victim_session.post(f"{BASE_URL}/api/workout", json={
            "date": date_to_delete,
            "body_parts": ["plecy"]
        })
        self.assertEqual(resp.status_code, 200, f"Setup Failed: Could not create victim workout. Resp: {resp.text}")
        
        # 2. Login as Attacker
        self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": TEST_USER,
            "password": TEST_PASS
        })
        
        # 3. Attempt delete with Victim's ID query param (Ignored by secure server)
        self.session.delete(f"{BASE_URL}/api/workout/{date_to_delete}?user_id={self.victim_id}")
        
        # 4. Verify if it still exists for Victim
        check_resp = victim_session.get(f"{BASE_URL}/api/workout/{date_to_delete}")
        data = check_resp.json()
        
        self.assertTrue(data.get('date') == date_to_delete, "Workout should still exist for Victim! (IDOR Delete Prevented)")
        print("\n[SUCCESS] IDOR Delete Prevented: Victim's workout remains.")

if __name__ == '__main__':
    unittest.main()
