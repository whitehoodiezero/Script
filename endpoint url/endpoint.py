import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def find_endpoints(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    endpoints = set()

    # Find all anchor tags with href attributes
    for a_tag in soup.find_all('a', href=True):
        endpoint = urljoin(url, a_tag['href'])
        endpoints.add(endpoint)

    return endpoints

def save_endpoints_to_file(endpoints, filename):
    with open(filename, 'w') as file:
        for endpoint in endpoints:
            file.write(f"{endpoint}\n")

def main():
    website_url = 'https://www.sekarlaut.com/'  # Ganti dengan URL website yang ingin Anda cari endpoint-nya
    output_file = 'endpoints.txt'
    
    print(f"Mencari endpoint dari {website_url}...")
    endpoints = find_endpoints(website_url)
    
    if endpoints:
        print(f"Menemukan {len(endpoints)} endpoint. Menyimpan ke {output_file}...")
        save_endpoints_to_file(endpoints, output_file)
        print(f"Endpoint berhasil disimpan di {output_file}.")
    else:
        print("Tidak ada endpoint yang ditemukan.")

if __name__ == "__main__":
    main()