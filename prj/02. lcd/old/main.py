import datetime
import psutil
import pytz
import requests
import subprocess
from RPLCD import i2c
from astral import LocationInfo
from astral.sun import sun
from datetime import datetime
from threading import Thread
from time import sleep

# External variables
DISK_PATH = '/srv/dev-disk-by-uuid-d2d5ec9f-ae15-4cb9-bbe3-c42f95d13958'
PROXIES = {'http': 'socks5://127.0.0.1:xxxx', 'https': 'socks5://127.0.0.1:xxxx'}
CHECK_IP_URL = 'https://checkip.amazonaws.com'
PAYLOAD_AUTH = {"password": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}
BASE_URL = "https://127.0.0.1:xxxx/"
URL_AUTH = BASE_URL + "api/auth"
URL_SUMMARY = BASE_URL + "api/stats/summary"

# Set-up some constants to initialise the LCD
LCDMODE = 'i2c'
COLS = 20
ROWS = 4
CHARMAP = 'A00'
I2C_EXPANDER = 'PCF8574'
ADDRESS = 0x27 # If you don't know what yours is, do i2cdetect -y 1
PORT = 1 # 0 on an older Pi

BOOT_TIME = 600
CPU_TEMP_THRESHOLD = 55
CPU_USAGE_THRESHOLD = 80
RAM_USAGE_THRESHOLD = 80
LOCATIONINFO = LocationInfo(name="LittleBox", region="Unknown", timezone="Europe/Rome", latitude=99.9, longitude=99.9)

row1 = "                    "
row2 = "                    "
row3 = "                    "
row4 = "                    "
cpuUsage = 0
cpuTemp = 0
ramUsage = 0

# Initialise the LCD
lcd = i2c.CharLCD(I2C_EXPANDER, ADDRESS, port=PORT, charmap=CHARMAP, cols=COLS, rows=ROWS)
lcd.clear()

# Global variables for authentication tokens
sid = None
csrf = None

def get_current_times():
    tz = pytz.timezone(LOCATIONINFO.timezone)
    now = datetime.now(tz)
    return now

def get_cpu_info():
    cpu_usage = int(psutil.cpu_percent())
    cpu_temp = int(psutil.sensors_temperatures()['cpu_thermal'][0][1])
    return cpu_usage, cpu_temp

def get_memory_info():
    ram_usage = int(psutil.virtual_memory().percent)
    swap_usage = int(psutil.swap_memory().percent)
    return ram_usage, swap_usage

def get_disk_usage():
    hd1_usage = int(psutil.disk_usage('/').percent)
    hd2_usage = int(psutil.disk_usage(DISK_PATH).percent)
    return hd1_usage, hd2_usage

def get_uptime():
    delta_time = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    uptime_days = delta_time.days
    uptime_hours = delta_time.seconds // 3600
    return uptime_days, uptime_hours

def get_public_ip():
    try:
        response = requests.get(CHECK_IP_URL)
        return response.text.strip()
    except:
        return 'Exception'

def get_tor_ip():
    try:
        session = requests.session()
        session.proxies = PROXIES
        response = session.get(CHECK_IP_URL)
        return response.text.strip()
    except:
        return 'Exception'

# PiHole
def get_auth_tokens():
    global sid, csrf
    response = requests.request("POST", URL_AUTH, json=PAYLOAD_AUTH, verify=False)
    data = response.json()
    sid = data["session"]["sid"]
    csrf = data["session"]["csrf"]

def get_summary_stats():
    headers = {
        'X-FTL-SID': sid,
        'X-FTL-CSRF': csrf
    }
    response = requests.request("GET", URL_SUMMARY, headers=headers, verify=False)
    return response


# Main thread
def refresh(sleep_time):
    global row1, row2, row3, row4, cpuUsage, cpuTemp, ramUsage

    start = get_current_times()
    
    while True:
        now = get_current_times()
        now_time = now.time()

        sunhours = sun(LOCATIONINFO.observer, now)
        sunrise = sunhours["sunrise"].time()
        sunset = sunhours["sunset"].time()

        if ((now - start).seconds <= BOOT_TIME 
            or ((now_time >= sunset) or (now_time <= sunrise)) 
            or cpuUsage >= CPU_USAGE_THRESHOLD 
            or cpuTemp >= CPU_TEMP_THRESHOLD 
            or ramUsage >= RAM_USAGE_THRESHOLD):
            lcd.backlight_enabled = True
        else:
            lcd.backlight_enabled = False

        row1 = '  ' + now.strftime('%d/%m/%Y %H:%M')

        lcd.write_string(row1)
        lcd.crlf()
        lcd.write_string(row2)
        lcd.crlf()
        lcd.write_string(row3)
        lcd.crlf()
        lcd.write_string(row4)
        sleep(sleep_time)
        lcd.cursor_pos = (0, 0)

def refresh_cpu_data(sleep_time):
    global row2, cpuUsage, cpuTemp

    while True:
        cpuUsage, cpuTemp = get_cpu_info()
        row2 = f'CPU: {cpuUsage:3}%    TMP: {cpuTemp:3}C'
        sleep(sleep_time)

def refresh_hw_data(sleep_time):
    global row3, ramUsage

    while True:
        ramUsage, swapUsage = get_memory_info()
        row3 = f'RAM: {ramUsage:3}%  SWP: {swapUsage:3}%'
        sleep(sleep_time)

        hd1_usage, hd2_usage = get_disk_usage()
        row3 = f'HD1: {hd1_usage:3}%  HD2: {hd2_usage:3}%'
        sleep(sleep_time)

def refresh_system_data(sleep_time):
    global row4, sid, csrf

    get_auth_tokens()

    while True:
        try:
            uptime_days, uptime_hours = get_uptime()
            row4 = f'Uptime: {uptime_days:6}d +{uptime_hours:2}h'
            sleep(sleep_time)
        
            public_ip = get_public_ip()
            row4 = f'IP: {public_ip.rjust(16, " ")}'
            sleep(sleep_time)

            tor_ip = get_tor_ip()
            row4 = f'TOR: {tor_ip.rjust(15, " ")}'
            sleep(sleep_time)

            response = get_summary_stats()
            if response.status_code == 200:
                data = response.json()
                percent_blocked = data['queries']['percent_blocked']
                row4 = f'ADV Blocked: {percent_blocked:6.2f}%'
            elif response.status_code == 401:
                get_auth_tokens()
                row4 = 'Re-authenticating...'
            else:
                row4 = 'Exception unknown...'
            sleep(sleep_time)
        except Exception as e:
            print(f"Exception while calling services: {e}")

# MAIN TASK
t1 = Thread(target=refresh, args=(1,))
t2 = Thread(target=refresh_cpu_data, args=(5,))
t3 = Thread(target=refresh_hw_data, args=(10,))
t4 = Thread(target=refresh_system_data, args=(15,))

t1.start()
t2.start()
t3.start()
t4.start()