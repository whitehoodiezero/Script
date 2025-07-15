import requests
import concurrent.futures
import socket
import ssl
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import random
import argparse
import csv
import os
from datetime import datetime

# Konfigurasi default
DEFAULT_PORTS = [80, 443, 8080, 8443, 8000, 8888, 8008, 3000, 5000, 9000]
DEFAULT_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
]
TIMEOUT = 5
MAX_THREADS = 50

def get_title(response_text):
    """Ekstrak title dari HTML"""
    try:
        soup = BeautifulSoup(response_text, 'html.parser')
        title = soup.title.string.strip() if soup.title else ''
        return title[:100]  # Batasi panjang title
    except:
        return ''

def custom_headers():
    """Generate header dengan User-Agent acak"""
    return {
        'User-Agent': random.choice(DEFAULT_USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def check_port(host, port):
    """Cek koneksi port TCP"""
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT):
            return True
    except:
        return False

def check_http(target, port, protocol):
    """Periksa layanan HTTP/HTTPS"""
    url = f"{protocol}://{target}:{port}"
    result = {
        'url': url,
        'status': 'ERROR',
        'status_code': 0,
        'title': '',
        'server': '',
        'content_length': 0,
        'redirect': '',
        'port': port,
        'protocol': protocol
    }

    try:
        response = requests.get(
            url,
            headers=custom_headers(),
            allow_redirects=False,
            timeout=TIMEOUT,
            verify=False
        )
        
        result['status'] = 'OK'
        result['status_code'] = response.status_code
        result['title'] = get_title(response.text)
        result['server'] = response.headers.get('Server', '')
        result['content_length'] = len(response.content)
        
        if 300 <= response.status_code < 400:
            result['redirect'] = response.headers.get('Location', '')
    
    except requests.exceptions.RequestException as e:
        if 'CERTIFICATE_VERIFY_FAILED' in str(e):
            result['status'] = 'SSL_ERROR'
        elif 'Connection aborted' in str(e):
            result['status'] = 'CONN_ABORTED'
        elif 'Read timed out' in str(e):
            result['status'] = 'TIMEOUT'
    
    return result

def process_target(target, ports, output_writer, output_file):
    """Proses setiap target dengan multithreading"""
    print(f"[*] Memproses: {target}")
    tasks = []
    
    # Cek port TCP terlebih dahulu
    open_ports = []
    for port in ports:
        if check_port(target, port):
            open_ports.append(port)
    
    # Buat tasks untuk port yang terbuka
    for port in open_ports:
        for protocol in ['http', 'https']:
            tasks.append((target, port, protocol))
    
    # Eksekusi tasks dengan thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [executor.submit(check_http, t[0], t[1], t[2]) for t in tasks]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            output_writer.writerow([
                result['url'],
                result['status'],
                result['status_code'],
                result['title'],
                result['server'],
                result['content_length'],
                result['redirect'],
                result['port'],
                result['protocol']
            ])
            output_file.flush()
            print_result(result)

def print_result(result):
    """Tampilkan hasil secara real-time"""
    status = f"[{result['status']}]".ljust(12)
    print(f"{status} {result['url']} | Title: {result['title']} | Server: {result['server']}")

def main():
    parser = argparse.ArgumentParser(description='Subdomain Recon Tool')
    parser.add_argument('-i', '--input', help='File berisi list subdomain', required=True)
    parser.add_argument('-o', '--output', help='Output file (CSV)', default='recon_results.csv')
    parser.add_argument('-p', '--ports', help='Ports (comma separated)', default=','.join(map(str, DEFAULT_PORTS)))
    args = parser.parse_args()

    # Parse ports
    ports = list(map(int, args.ports.split(',')))
    
    # Baca target
    targets = []
    with open(args.input, 'r') as f:
        targets = [line.strip() for line in f.readlines() if line.strip()]
    
    # Siapkan output
    output_exists = os.path.exists(args.output)
    with open(args.output, 'a', newline='') as outfile:
        writer = csv.writer(outfile)
        
        if not output_exists:
            writer.writerow([
                'URL', 'Status', 'Status Code', 'Title', 'Server', 
                'Content Length', 'Redirect', 'Port', 'Protocol'
            ])
        
        for target in targets:
            process_target(target, ports, writer, outfile)

if __name__ == '__main__':
    main()