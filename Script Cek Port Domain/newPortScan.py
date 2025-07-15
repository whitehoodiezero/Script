import requests
import concurrent.futures
import socket
import ssl
from bs4 import BeautifulSoup
import random
import argparse
import csv
import os
import re
import time
import json
from collections import defaultdict
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
HTTP_METHODS = ['GET', 'HEAD', 'OPTIONS', 'TRACE', 'PUT', 'DELETE', 'POST', 'PATCH', 'CONNECT']
TIMEOUT = 5
MAX_THREADS = 20  # Kurangi thread untuk stabilitas
DELAY = 0.1  # Delay default antara request

def normalize_target(target):
    """Bersihkan target dari skema http/https dan path"""
    # Hapus skema
    target = re.sub(r'^https?://', '', target)
    # Hapus path dan parameter
    target = target.split('/')[0]
    # Hapus port jika ada
    target = target.split(':')[0]
    return target.strip()

def get_title(response_text):
    """Ekstrak title dari HTML"""
    try:
        soup = BeautifulSoup(response_text, 'html.parser')
        title = soup.title.string.strip() if soup.title else ''
        return title[:100]  # Batasi panjang title
    except:
        return ''

def get_tech_stack(response):
    """Deteksi teknologi yang digunakan berdasarkan header dan konten"""
    tech = []
    
    # Deteksi dari header
    headers = response.headers
    if 'Server' in headers:
        tech.append(headers['Server'])
    if 'X-Powered-By' in headers:
        tech.append(headers['X-Powered-By'])
    if 'Via' in headers:
        tech.append(headers['Via'])
    
    # Deteksi dari konten
    body = response.text
    if 'wp-content' in body:
        tech.append('WordPress')
    if '/_next/' in body:
        tech.append('Next.js')
    if 'laravel' in body.lower():
        tech.append('Laravel')
    if 'react' in body.lower():
        tech.append('React')
    if 'jquery' in body.lower():
        tech.append('jQuery')
    
    return ', '.join(set(tech)) if tech else 'Unknown'

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

def check_http_method(target, port, protocol, method):
    """Periksa layanan HTTP/HTTPS dengan method tertentu"""
    url = f"{protocol}://{target}:{port}"
    result = {
        'url': url,
        'method': method,
        'status': 'ERROR',
        'status_code': 0,
        'title': '',
        'server': '',
        'tech_stack': '',
        'content_length': 0,
        'redirect': '',
        'allowed_methods': '',
        'port': port,
        'protocol': protocol,
        'security_headers': '',
        'vulnerable': 'No',
        'recommendation': ''
    }

    try:
        # Handle CONNECT separately as it's used for proxies
        if method == 'CONNECT':
            return check_connect_method(target, port, result)
        
        # Handle OPTIONS to get allowed methods
        if method == 'OPTIONS':
            response = requests.options(
                url,
                headers=custom_headers(),
                allow_redirects=False,
                timeout=TIMEOUT,
                verify=False
            )
            allowed_methods = response.headers.get('Allow', '')
            result['allowed_methods'] = re.sub(r'\s*,\s*', ', ', allowed_methods)
            result['status'] = 'OK'
            result['status_code'] = response.status_code
            result['server'] = response.headers.get('Server', '')
            result['content_length'] = len(response.content)
            return result
        
        # Handle other methods
        if method in ['HEAD', 'TRACE']:
            response = requests.request(
                method,
                url,
                headers=custom_headers(),
                allow_redirects=False,
                timeout=TIMEOUT,
                verify=False
            )
        else:
            # Add empty body for methods that require it
            data = None if method in ['GET', 'DELETE'] else '{}'
            response = requests.request(
                method,
                url,
                headers=custom_headers(),
                data=data,
                allow_redirects=False,
                timeout=TIMEOUT,
                verify=False
            )
        
        result['status'] = 'OK'
        result['status_code'] = response.status_code
        
        if method == 'GET':
            result['title'] = get_title(response.text)
            result['tech_stack'] = get_tech_stack(response)
        
        result['server'] = response.headers.get('Server', '')
        result['content_length'] = len(response.content)
        
        # Check security headers
        security_headers = []
        for header in ['Strict-Transport-Security', 'Content-Security-Policy', 
                      'X-Content-Type-Options', 'X-Frame-Options', 
                      'X-XSS-Protection', 'Referrer-Policy']:
            if header in response.headers:
                security_headers.append(header)
        result['security_headers'] = ', '.join(security_headers) if security_headers else 'None'
        
        # Check for vulnerabilities
        result['vulnerable'], result['recommendation'] = check_vulnerabilities(result, response)
        
        if 300 <= response.status_code < 400:
            result['redirect'] = response.headers.get('Location', '')
    
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if 'CERTIFICATE_VERIFY_FAILED' in error_msg:
            result['status'] = 'SSL_ERROR'
        elif 'Connection aborted' in error_msg:
            result['status'] = 'CONN_ABORTED'
        elif 'Read timed out' in error_msg:
            result['status'] = 'TIMEOUT'
        elif 'Connection refused' in error_msg:
            result['status'] = 'CONN_REFUSED'
        elif 'Remote end closed connection' in error_msg:
            result['status'] = 'CONN_CLOSED'
        else:
            result['status'] = f'ERROR: {error_msg[:30]}'
    
    return result

def check_connect_method(target, port, result):
    """Handle CONNECT method (proxy tunneling)"""
    try:
        # Create raw socket connection
        sock = socket.create_connection((target, port), timeout=TIMEOUT)
        
        # For HTTPS, we need to wrap socket
        if result['protocol'] == 'https':
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=target)
        
        # Send CONNECT request
        sock.sendall(b"CONNECT / HTTP/1.1\r\n")
        sock.sendall(f"Host: {target}:{port}\r\n".encode())
        sock.sendall(b"User-Agent: Mozilla/5.0 (Recon Tool)\r\n")
        sock.sendall(b"\r\n")
        
        # Get response
        response = sock.recv(4096)
        sock.close()
        
        # Parse response
        response_str = response.decode('utf-8', errors='ignore')
        status_line = response_str.split('\r\n')[0]
        status_code = int(status_line.split(' ')[1]) if ' ' in status_line else 0
        
        result['status'] = 'OK'
        result['status_code'] = status_code
        result['server'] = 'Proxy'
        result['content_length'] = len(response)
        
        # Generate recommendations
        result['vulnerable'] = 'Yes'
        result['recommendation'] = 'Open proxy detected! Restrict CONNECT method to authorized users only.'
        
        return result
        
    except Exception as e:
        result['status'] = f'CONNECT_ERR: {str(e)[:30]}'
        return result

def check_vulnerabilities(result, response):
    """Deteksi kerentanan potensial dan berikan rekomendasi"""
    vulnerable = 'No'
    recommendations = []
    
    # 1. Check for dangerous HTTP methods
    if 'OPTIONS' in result.get('allowed_methods', ''):
        dangerous_methods = ['PUT', 'DELETE', 'TRACE', 'CONNECT']
        for method in dangerous_methods:
            if method in result['allowed_methods']:
                recommendations.append(f"Disable {method} method")
                vulnerable = 'Yes'
    
    # 2. Check for missing security headers
    if result.get('security_headers') == 'None':
        recommendations.append("Implement security headers: HSTS, CSP, XSS-Protection")
        vulnerable = 'Yes'
    
    # 3. Check server version vulnerabilities
    server_info = result.get('server', '')
    if server_info:
        for server, versions in VULNERABLE_SERVERS.items():
            if server in server_info:
                for version in versions:
                    if version in server_info:
                        recommendations.append(f"Upgrade {server} from vulnerable version {version}")
                        vulnerable = 'Yes'
                        break
    
    # 4. Check for HTTP when HTTPS is available
    if result['protocol'] == 'http' and result['status_code'] in [200, 301, 302]:
        recommendations.append("Enforce HTTPS with HSTS header")
        vulnerable = 'Yes'
    
    # 5. Check for directory listing
    if "Index of /" in result.get('title', ''):
        recommendations.append("Disable directory listing")
        vulnerable = 'Yes'
    
    # 6. Check for default pages
    default_titles = ['Welcome to nginx!', 'Apache HTTP Server', 'IIS Windows']
    if any(title in result.get('title', '') for title in default_titles):
        recommendations.append("Remove default server page")
        vulnerable = 'Yes'
    
    # 7. Check for TRACE method
    if 'TRACE' in result.get('allowed_methods', ''):
        recommendations.append("Disable TRACE method to prevent XST attacks")
        vulnerable = 'Yes'
    
    # 8. Check for proxy misconfiguration
    if 'CONNECT' in result.get('allowed_methods', ''):
        recommendations.append("Restrict CONNECT method to prevent proxy abuse")
        vulnerable = 'Yes'
    
    # 9. Check for open CORS
    if 'Access-Control-Allow-Origin' in response.headers:
        if response.headers['Access-Control-Allow-Origin'] == '*':
            recommendations.append("Restrict CORS policy to trusted domains")
            vulnerable = 'Yes'
    
    return vulnerable, '; '.join(recommendations) if recommendations else 'No issues found'

def process_target(target, ports, output_writer, output_file, delay):
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
        # Tentukan protokol berdasarkan port
        if port == 80:
            protocols = ['http']
        elif port == 443:
            protocols = ['https']
        else:
            protocols = ['http', 'https']
            
        for protocol in protocols:
            for method in HTTP_METHODS:
                tasks.append((target, port, protocol, method))
                time.sleep(delay)  # Delay antara pembuatan task
    
    # Eksekusi tasks dengan thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = []
        for task in tasks:
            futures.append(executor.submit(check_http_method, task[0], task[1], task[2], task[3]))
        
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                output_writer.writerow([
                    result['url'],
                    result['method'],
                    result['status'],
                    result['status_code'],
                    result['title'],
                    result['server'],
                    result['tech_stack'],
                    result['content_length'],
                    result['redirect'],
                    result['allowed_methods'],
                    result['port'],
                    result['protocol'],
                    result['security_headers'],
                    result['vulnerable'],
                    result['recommendation']
                ])
                output_file.flush()
                print_result(result)
            except Exception as e:
                print(f"[!] Error processing result: {e}")

def print_result(result):
    """Tampilkan hasil secara real-time"""
    status = f"[{result['status']}]".ljust(15)
    method = f"{result['method']}".ljust(8)
    code = f"{result['status_code']}".ljust(5)
    
    output = f"{status} {method} {code} {result['url']}"
    
    if result['vulnerable'] == 'Yes':
        output += f" \033[91m[VULNERABLE]\033[0m"
        if result['recommendation']:
            output += f" \033[93mRecommendation: {result['recommendation']}\033[0m"
    
    print(output)

def generate_summary(input_file, output_file):
    """Buat laporan ringkasan dari hasil scan"""
    findings = defaultdict(list)
    vulnerable_targets = set()
    all_targets = set()
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)  # Baca semua baris
            
            if not rows:
                print("[!] File output kosong, tidak bisa membuat laporan")
                return
                
            for row in rows:
                all_targets.add(row['URL'])
                if row['Vulnerable'] == 'Yes':
                    vulnerable_targets.add(row['URL'])
                    findings[row['Recommendation']].append(row['URL'])
        
        # Generate summary report
        report = {
            "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_targets": len(all_targets),
            "vulnerable_targets": len(vulnerable_targets),
            "findings": []
        }
        
        for recommendation, urls in findings.items():
            report["findings"].append({
                "issue": recommendation,
                "affected_count": len(urls),
                "affected_targets": urls[:10],  # Batasi jumlah target yang ditampilkan
                "total_affected": len(urls)
            })
        
        # Sort by severity
        severity_order = [
            "Open proxy detected",
            "Upgrade",
            "Disable TRACE",
            "Disable CONNECT",
            "Disable PUT",
            "Disable DELETE",
            "Implement security headers",
            "Enforce HTTPS",
            "Disable directory listing",
            "Remove default server page",
            "Restrict CORS policy"
        ]
        
        def get_severity_level(issue):
            for i, s in enumerate(severity_order):
                if s in issue:
                    return i
            return len(severity_order)
        
        report["findings"].sort(key=lambda x: get_severity_level(x["issue"]))
        
        # Save report
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4)
        
        print(f"[+] Laporan ringkasan disimpan sebagai {output_file}")
    except Exception as e:
        print(f"[!] Error generating summary: {e}")

def main():
    parser = argparse.ArgumentParser(description='Subdomain Recon Tool')
    parser.add_argument('-i', '--input', help='File berisi list subdomain', required=True)
    parser.add_argument('-o', '--output', help='Output file (CSV)', default='recon_results.csv')
    parser.add_argument('-p', '--ports', help='Ports (comma separated)', default=','.join(map(str, DEFAULT_PORTS)))
    parser.add_argument('-d', '--delay', help='Delay antara request (detik)', type=float, default=DELAY)
    parser.add_argument('-r', '--report', help='Buat laporan ringkasan', action='store_true')
    args = parser.parse_args()

    # Parse ports
    ports = list(map(int, args.ports.split(',')))
    
    # Baca dan normalisasi target
    targets = []
    seen = set()  # Untuk hindari duplikat
    try:
        with open(args.input, 'r') as f:
            for line in f:
                target = line.strip()
                if not target:
                    continue
                    
                # Normalisasi target
                clean_target = normalize_target(target)
                
                # Cek validitas target
                if not re.match(r'^[a-zA-Z0-9.-]+$', clean_target):
                    print(f"[!] Target tidak valid: {target} -> {clean_target}")
                    continue
                    
                # Hindari duplikat
                if clean_target not in seen:
                    seen.add(clean_target)
                    targets.append(clean_target)
        
        print(f"[+] Ditemukan {len(targets)} target unik")
        
        # Siapkan output
        output_exists = os.path.exists(args.output)
        with open(args.output, 'a', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            
            if not output_exists:
                writer.writerow([
                    'URL', 'Method', 'Status', 'Status Code', 'Title', 'Server', 
                    'Tech Stack', 'Content Length', 'Redirect', 'Allowed Methods', 
                    'Port', 'Protocol', 'Security Headers', 'Vulnerable', 'Recommendation'
                ])
            
            for target in targets:
                process_target(target, ports, writer, outfile, args.delay)
        
        # Buat laporan ringkasan jika diminta
        if args.report:
            report_file = args.output.replace('.csv', '_summary.json')
            generate_summary(args.output, report_file)
            
    except Exception as e:
        print(f"[!] Error utama: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()