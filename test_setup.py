#!/usr/bin/env python3
"""
Quick test script to verify OceanQuery setup is working.
"""

import requests
import sys
import os

def test_backend_health():
    """Test if backend is running and healthy."""
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend health: {data['status']}")
            print(f"   Service: {data['service']}")
            print(f"   Version: {data['version']}")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to backend: {e}")
        return False

def test_api_endpoints():
    """Test key API endpoints."""
    endpoints = [
        ('/api/v1/chat/query', 'POST', {'message': 'test'}),
        ('/api/v1/argo/floats', 'GET', None),
        ('/api/v1/argo/statistics', 'GET', None),
        ('/api/v1/auth/demo-login', 'GET', None),
    ]
    
    results = []
    
    for endpoint, method, data in endpoints:
        try:
            url = f'http://localhost:8000{endpoint}'
            
            if method == 'POST':
                response = requests.post(url, json=data, timeout=5)
            else:
                response = requests.get(url, timeout=5)
            
            if response.status_code in [200, 201]:
                print(f"✅ {method} {endpoint} - OK")
                results.append(True)
            else:
                print(f"❌ {method} {endpoint} - {response.status_code}")
                results.append(False)
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {method} {endpoint} - Connection error: {e}")
            results.append(False)
    
    return all(results)

def test_frontend_build():
    """Check if frontend can be analyzed."""
    try:
        os.chdir('frontend')
        result = os.system('flutter analyze --no-fatal-infos > /dev/null 2>&1')
        if result == 0:
            print("✅ Frontend code analysis - OK")
            return True
        else:
            print("❌ Frontend code analysis - FAILED")
            return False
    except Exception as e:
        print(f"❌ Frontend test error: {e}")
        return False
    finally:
        os.chdir('..')

def main():
    """Run all tests."""
    print("🌊 OceanQuery Setup Test")
    print("=" * 40)
    
    # Check if backend is running
    backend_ok = test_backend_health()
    
    if not backend_ok:
        print("\n💡 To start the backend:")
        print("   make install     # Install dependencies")
        print("   make dev         # Start database + backend")
        print("\n   Or manually:")
        print("   make db-up       # Start database")
        print("   make backend     # Start backend server")
        return 1
    
    print()
    
    # Test API endpoints
    api_ok = test_api_endpoints()
    
    print()
    
    # Test frontend
    frontend_ok = test_frontend_build()
    
    print()
    print("=" * 40)
    
    if backend_ok and api_ok and frontend_ok:
        print("🎉 All tests passed! OceanQuery is ready for development.")
        print("\n🚀 Quick start:")
        print("   Frontend: make front")
        print("   Backend:  already running")
        print("   API Docs: http://localhost:8000/docs")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == '__main__':
    exit(main())
