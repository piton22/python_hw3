import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:9999/links"

def test_shorten(url, alias, expires_at, project_name):
    data = {
        "url": url,
        "custom_alias": alias,
        "expires_at": expires_at,
        "project": project_name
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/shorten",
            json=data,
            timeout=5
        )
        response.raise_for_status()
        print("Shorten Response:", response.json())
    except requests.exceptions.RequestException as e:
        print(f"Shorten Error: {str(e)}")
        if e.response:
            print("Response content:", e.response.text)
    

test_shorten("https://hse.ru/", 'hse', None, None)
test_shorten("https://msu.ru/", 'msu', (datetime.utcnow() + timedelta(hours=3) + timedelta(minutes=5)).isoformat(), 'MSU_Project')
test_shorten("https://muctr.ru/", alias=None, expires_at=(datetime.utcnow() + timedelta(hours=3) + timedelta(minutes=10)).isoformat(), project_name='MUCTR_Project')
test_shorten("https://hse.ru/", 'hse2', expires_at=(datetime.utcnow()+ timedelta(hours=3) + timedelta(minutes=1)).isoformat(), project_name=None)

def test_redirect(short):
    response = requests.get(f"{BASE_URL}/{short}", allow_redirects=False)
    print(f"Status: {response.status_code}, Location: {response.headers.get('Location')}")


test_redirect('/shrt/hse')
test_redirect('hse')
test_redirect('msu')
test_redirect('hse2')
test_redirect('hse')
test_redirect('hse')

def test_delete(alias):
    # Тест удаления
    response = requests.delete(f"{BASE_URL}/{alias}")
    print("Delete Result:", response.json())

test_delete('msu')
test_delete('/shrt/hse2') 


def test_update(alias, new_url):
    response = requests.put(
        f"{BASE_URL}/{alias}",
        json={"url": new_url}
    )
    print("Update Result:", response.json())


test_update('hse2', "https://hse.ru/updated_url/")
test_update('/shrt/hse2', "https://hse.ru/updated_url_2/")


def test_search(original_url):
    # Тест поиска
    response = requests.get(f"{BASE_URL}/search", params={"original_url": original_url})
    print("Search Result:", response.json())

test_search('https://muctr.ru/')

test_redirect('/shrt/hse')
test_redirect('hse')
test_redirect('msu')
test_redirect('hse2')
test_redirect('hse')
test_redirect('hse')

def test_get_stat(short):
    response = requests.get(f"{BASE_URL}/{short}/stats")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Search Result:", response.json())
    else:
        print("Error:", response.text)

test_get_stat('hse')





# def test_shorten():
#     # Тест создания короткой ссылки
#     data = {
#         "url": TEST_URL,
#         "custom_alias": CUSTOM_ALIAS,
#         "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
#         "project": PROJECT_NAME
#     }
    
#     response = requests.post(f"{BASE_URL}/shorten", json=data)
#     print("Shorten Response:", response.json())

# def test_redirect():
#     # Тест редиректа
#     short_code = CUSTOM_ALIAS  # или сгенерированный код
#     response = requests.get(f"{BASE_URL}/{short_code}", allow_redirects=False)
    
#     print(f"Redirect Status: {response.status_code}")
#     print(f"Location Header: {response.headers.get('Location')}")

# def test_search():
#     # Тест поиска
#     response = requests.get(f"{BASE_URL}/search", params={"original_url": TEST_URL})
#     print("Search Result:", response.json())

# def test_update():
#     # Тест обновления URL
#     new_url = "https://new-example.com"
#     response = requests.put(
#         f"{BASE_URL}/{CUSTOM_ALIAS}",
#         json={"url": new_url}
#     )
#     print("Update Result:", response.json())

# def test_delete():
#     # Тест удаления
#     response = requests.delete(f"{BASE_URL}/{CUSTOM_ALIAS}")
#     print("Delete Result:", response.json())

# # def test_all():
#     try:
#         print("Testing Shorten:")
#         test_shorten()
        
#         print("\nTesting Redirect:")
#         test_redirect()
        
#         print("\nTesting Search:")
#         test_search()
        
#         print("\nTesting Update:")
#         test_update()
        
#         print("\nTesting Delete:")
#         test_delete()
        
#     except Exception as e:
#         print(f"Test Failed: {str(e)}")

# test_all()
