import requests
from datetime import datetime, timedelta, timezone

BASE_URL = "http://localhost:9999/links"

def test_shorten(url, alias, expires_at, project_name):
    # Конвертируем expires_at в строку, если он не None
    if expires_at is not None and isinstance(expires_at, datetime):
        expires_at = expires_at.isoformat()
    
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
    

test_shorten("https://hse.ru/", 'hse', expires_at=None, project_name=None)
test_shorten("https://msu.ru/", 'msu', expires_at=(datetime.utcnow() + timedelta(hours=3) + timedelta(minutes=5)).isoformat(), project_name='MSU_Project')
test_shorten("https://muctr.ru/", alias=None, expires_at=(datetime.utcnow() + timedelta(hours=3) + timedelta(minutes=100)).isoformat(), project_name='MUCTR_Project')
test_shorten("https://hse.ru/", 'hse2', expires_at=(datetime.utcnow() + timedelta(hours=3)  + timedelta(minutes=1)).isoformat(), project_name=None)

def test_redirect(short):
    response = requests.get(f"{BASE_URL}/{short}", allow_redirects=False)
    print(f"Status: {response.status_code}, Location: {response.headers.get('Location')}")


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


def test_update(alias, new_url):
    response = requests.put(
        f"{BASE_URL}/{alias}",
        json={"url": new_url}
    )
    print("Update Result:", response.json())


test_update('hse2', "https://hse.ru/updated_url/")


def test_search(original_url):
    # Тест поиска
    response = requests.get(f"{BASE_URL}/search", params={"original_url": original_url})
    print("Search Result:", response.json())

test_search('http://muctr.ru/')
test_search('https://muctr.ru')
test_search('https://hse.ru/updated_url')
test_search('https://hse.ru')

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