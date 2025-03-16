import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:9999/links"

# Тестовые данные
TEST_URL = "https://example.com"
CUSTOM_ALIAS = "test-alias"
PROJECT_NAME = "test-project"

def test_shorten():
    # Тест создания короткой ссылки
    data = {
        "url": TEST_URL,
        "custom_alias": CUSTOM_ALIAS,
        "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
        "project": PROJECT_NAME
    }
    
    response = requests.post(f"{BASE_URL}/shorten", json=data)
    print("Shorten Response:", response.json())

def test_redirect():
    # Тест редиректа
    short_code = CUSTOM_ALIAS  # или сгенерированный код
    response = requests.get(f"{BASE_URL}/{short_code}", allow_redirects=False)
    
    print(f"Redirect Status: {response.status_code}")
    print(f"Location Header: {response.headers.get('Location')}")

def test_search():
    # Тест поиска
    response = requests.get(f"{BASE_URL}/search", params={"original_url": TEST_URL})
    print("Search Result:", response.json())

def test_update():
    # Тест обновления URL
    new_url = "https://new-example.com"
    response = requests.put(
        f"{BASE_URL}/{CUSTOM_ALIAS}",
        json={"url": new_url}
    )
    print("Update Result:", response.json())

def test_delete():
    # Тест удаления
    response = requests.delete(f"{BASE_URL}/{CUSTOM_ALIAS}")
    print("Delete Result:", response.json())

def test_all():
    try:
        print("Testing Shorten:")
        test_shorten()
        
        print("\nTesting Redirect:")
        test_redirect()
        
        print("\nTesting Search:")
        test_search()
        
        print("\nTesting Update:")
        test_update()
        
        print("\nTesting Delete:")
        test_delete()
        
    except Exception as e:
        print(f"Test Failed: {str(e)}")

test_all()