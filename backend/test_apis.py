import requests
import time

BASE = 'http://127.0.0.1:8000'

def test_register():
    print("=== Test: User Registration ===")
    resp = requests.post(f'{BASE}/api/auth/register/', json={
        'username': 'testuser', 'email': 'test@example.com',
        'first_name': 'Test', 'last_name': 'User', 'phone': '1234567890',
        'role': 'resident', 'password': 'testpass123', 'confirm_password': 'testpass123'
    })
    print(f'Register status: {resp.status_code}')
    print(f'Register response: {resp.json()}')
    return resp.status_code == 201

def test_login():
    print("\n=== Test: User Login ===")
    resp = requests.post(f'{BASE}/api/auth/login/', json={
        'username': 'testuser', 'password': 'testpass123'
    })
    print(f'Login status: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        print(f'Tokens: access={data.get("access", "")[:20]}..., refresh={data.get("refresh", "")[:20]}...')
    return resp.status_code == 200

def test_profile():
    print("\n=== Test: User Profile ===")
    resp = requests.get(f'{BASE}/api/auth/profile/', 
                       headers={'Authorization': 'Bearer placeholder'})
    print(f'Profile status: {resp.status_code}')
    return resp.status_code in [200, 401]

def test_change_password():
    print("\n=== Test: Change Password ===")
    resp = requests.post(f'{BASE}/api/auth/change-password/', json={
        'old_password': 'testpass123', 'new_password': 'newpass123'
    }, headers={'Authorization': 'Bearer placeholder'})
    print(f'Change password status: {resp.status_code}')
    return resp.status_code in [200, 401]

def test_society_crud():
    print("\n=== Test: Society CRUD ===")
    # List societies
    resp = requests.get(f'{BASE}/api/society/')
    print(f'Society list status: {resp.status_code}')
    
    # Create society (admin only - will fail without auth)
    resp = requests.post(f'{BASE}/api/society/', json={
        'name': 'Test Society', 'registration_number': 'TS001',
        'address': '123 Test St', 'city': 'Test City', 'state': 'TS',
        'pincode': '12345', 'contact_email': 'test@test.com',
        'contact_phone': '1234567890'
    })
    print(f'Society create status: {resp.status_code}')

def test_emergency_contacts():
    print("\n=== Test: Emergency Contacts ===")
    # List contacts
    resp = requests.get(f'{BASE}/api/contacts/')
    print(f'Contacts list status: {resp.status_code}')
    
    # Create contact
    resp = requests.post(f'{BASE}/api/contacts/', json={
        'contact_type': 'primary_guardian',
        'relationship': 'spouse', 'name': 'John Doe', 'phone': '1234567891',
        'email': 'john@test.com'
    })
    print(f'Contact create status: {resp.status_code}')
    
    # Verify contact
    if resp.status_code == 201:
        contact_id = resp.json().get('id')
        print(f'Created contact ID: {contact_id}')
        
        # Verify contact
        resp = requests.get(f'{BASE}/api/contacts/{contact_id}/')
        print(f'Contact detail status: {resp.status_code}')
        
        # Verify contact
        resp = requests.put(f'{BASE}/api/contacts/{contact_id}/', json={
            'contact_type': 'primary_guardian', 'relationship': 'spouse',
            'name': 'John Updated', 'phone': '1234567891'
        })
        print(f'Contact update status: {resp.status_code}')
        
        # Verify verification endpoint
        resp = requests.post(f'{BASE}/api/contacts/{contact_id}/verify/', json={'token': 'test'})
        print(f'Verify contact status: {resp.status_code}')

if __name__ == '__main__':
    test_register()
    time.sleep(1)
    test_login()
    time.sleep(1)
    test_profile()
    time.sleep(1)
    test_change_password()
    time.sleep(1)
    test_society_crud()
    time.sleep(1)
    test_emergency_contacts()
    print("\n=== All tests completed ===")