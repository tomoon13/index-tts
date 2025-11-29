#!/usr/bin/env python3
"""
Test User Management API
=========================

Quick test script for user management endpoints.
"""

import requests

BASE_URL = "http://localhost:8000"


def test_user_management():
    """Test user management flow"""
    print("=" * 60)
    print("Testing User Management API")
    print("=" * 60)

    # 1. Login as admin
    print("\n1. Login as admin...")
    response = requests.post(
        f"{BASE_URL}/v1/auth/login",
        json={"email": "admin@example.com", "password": "test123"},
    )

    if response.status_code != 200:
        print(f"✗ Login failed: {response.text}")
        return

    data = response.json()
    admin_token = data["accessToken"]
    print(f"✓ Admin logged in: {data['user']['email']}")

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. List all users
    print("\n2. List all users...")
    response = requests.get(f"{BASE_URL}/v1/users", headers=headers)

    if response.status_code != 200:
        print(f"✗ List users failed: {response.text}")
        return

    data = response.json()
    print(f"✓ Found {data['total']} users")
    for user in data["users"]:
        print(f"  - {user['email']} (ID: {user['id']}, Admin: {user['isAdmin']})")

    # 3. Create a new user
    print("\n3. Create a new user...")
    response = requests.post(
        f"{BASE_URL}/v1/users",
        headers=headers,
        json={
            "email": "testuser@example.com",
            "password": "testpass123",
            "username": "testuser",
            "displayName": "Test User",
            "isAdmin": False,
            "isVerified": True,
        },
    )

    if response.status_code != 201:
        print(f"✗ Create user failed: {response.text}")
        # User might already exist, continue anyway
    else:
        data = response.json()
        new_user_id = data["id"]
        print(f"✓ User created: {data['email']} (ID: {new_user_id})")

        # 4. Get user details
        print(f"\n4. Get user {new_user_id} details...")
        response = requests.get(f"{BASE_URL}/v1/users/{new_user_id}", headers=headers)

        if response.status_code != 200:
            print(f"✗ Get user failed: {response.text}")
        else:
            data = response.json()
            print(f"✓ User details:")
            print(f"  Email: {data['email']}")
            print(f"  Username: {data['username']}")
            print(f"  Display Name: {data['displayName']}")
            print(f"  Is Active: {data['isActive']}")
            print(f"  Is Verified: {data['isVerified']}")
            print(f"  Is Admin: {data['isAdmin']}")

        # 5. Update user
        print(f"\n5. Update user {new_user_id}...")
        response = requests.patch(
            f"{BASE_URL}/v1/users/{new_user_id}",
            headers=headers,
            json={"displayName": "Updated Test User", "isVerified": True},
        )

        if response.status_code != 200:
            print(f"✗ Update user failed: {response.text}")
        else:
            data = response.json()
            print(f"✓ User updated: {data['displayName']}")

        # 6. Set user password
        print(f"\n6. Set user {new_user_id} password...")
        response = requests.post(
            f"{BASE_URL}/v1/users/{new_user_id}/password",
            headers=headers,
            json={"newPassword": "newpassword123"},
        )

        if response.status_code != 200:
            print(f"✗ Set password failed: {response.text}")
        else:
            print(f"✓ Password updated")

        # 7. Login as new user
        print(f"\n7. Login as new user...")
        response = requests.post(
            f"{BASE_URL}/v1/auth/login",
            json={"email": "testuser@example.com", "password": "newpassword123"},
        )

        if response.status_code != 200:
            print(f"✗ New user login failed: {response.text}")
        else:
            data = response.json()
            print(f"✓ New user logged in: {data['user']['email']}")

        # 8. Delete user
        print(f"\n8. Delete user {new_user_id}...")
        response = requests.delete(
            f"{BASE_URL}/v1/users/{new_user_id}", headers=headers
        )

        if response.status_code != 200:
            print(f"✗ Delete user failed: {response.text}")
        else:
            data = response.json()
            print(f"✓ {data['message']}")

    print("\n" + "=" * 60)
    print("✓ User Management API test complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_user_management()
    except requests.exceptions.ConnectionError:
        print("✗ Error: Cannot connect to API server")
        print("Make sure the server is running: uv run python run_api.py")
    except Exception as e:
        print(f"✗ Error: {e}")
