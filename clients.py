import requests
from datetime import datetime, timedelta

BASE_URL_LINKS = "http://localhost:9999/links"
BASE_URL_PROJECTS = "http://localhost:9999/projects"

def test_shorten(url, alias, expires_at, project_name):
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
            f"{BASE_URL_LINKS}/shorten",
            json=data,
            timeout=5
        )
        response.raise_for_status()
        print("Shorten Response:", response.json())
    except requests.exceptions.RequestException as e:
        print(f"Shorten Error: {str(e)}")
        if e.response:
            print("Response content:", e.response.text)

def test_get_stat(short):
    response = requests.get(f"{BASE_URL_LINKS}/{short}/stats")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Search Result:", response.json())
    else:
        print("Error:", response.text)

def test_redirect(short):
    response = requests.get(f"{BASE_URL_LINKS}/{short}", allow_redirects=False)
    print(f"Status: {response.status_code}, Location: {response.headers.get('Location')}")

def test_delete(alias):
    response = requests.delete(f"{BASE_URL_LINKS}/{alias}")
    print("Delete Result:", response.json())

def test_update(alias, new_url):
    response = requests.put(
        f"{BASE_URL_LINKS}/{alias}",
        json={"url": new_url}
    )
    print("Update Result:", response.json())

def test_search(original_url):
    response = requests.get(f"{BASE_URL_LINKS}/search", params={"original_url": original_url})
    print(f"Status: {response.status_code}")
    
    try:
        data = response.json()
        if response.status_code == 200:
            print("Search Result:", data)
        else:
            print("Error details:", data)
    except:
        print("Invalid JSON response:", response.text)


def test_deleted():

    response = requests.get(f"{BASE_URL_LINKS}/deleted")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Deleted Result:", response.json())

def test_project_stats(project_name):
    response = requests.get(f"{BASE_URL_PROJECTS}/{project_name}/stats")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Project Stats:", response.json())
    else:
        print("Error:", response.text)

    

test_shorten("https://hse.ru/", 'hse', expires_at=None, project_name=None)
test_shorten("https://msu.ru/", 'msu', expires_at=(datetime.utcnow() + timedelta(hours=3) + timedelta(minutes=1)).isoformat(), project_name='University')
test_shorten("https://muctr.ru/", alias=None, expires_at=(datetime.utcnow() + timedelta(hours=3) + timedelta(days=3)).isoformat(), project_name='University')
test_shorten("https://hse.ru/", 'hse2', expires_at=(datetime.utcnow() + timedelta(hours=3)  + timedelta(minutes=1)).isoformat(), project_name=None)



test_redirect('hse')
test_redirect('msu')
test_redirect('hse2')
test_redirect('hse')
test_redirect('hse')

test_delete('msu')

test_update('hse2', "https://hse.ru/updated_url/")


test_search('http://muctr.ru/')

test_redirect('hse')
test_redirect('msu')
test_redirect('hse2')
test_redirect('hse')
test_redirect('hse')


test_get_stat('hse')

test_deleted()

test_project_stats("University")

test_search('https://hse.ru/')
test_search('https://muctr.ru/')