import datetime
import psutil
import pytz
import requests
from astral import LocationInfo
from datetime import datetime

# External variables
DISK_PATH = '/srv/dev-disk-by-uuid-d2d5ec9f-ae15-4cb9-bbe3-c42f95d13958'
PROXIES = {'http': 'socks5://127.0.0.1:xxxx', 'https': 'socks5://127.0.0.1:xxxx'}
CHECK_IP_URL = 'https://checkip.amazonaws.com'
PAYLOAD_AUTH = {"password": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}
BASE_URL = "https://127.0.0.1:xxxx/"
URL_AUTH = BASE_URL + "api/auth"
URL_SUMMARY = BASE_URL + "api/stats/summary"

# Function to get current times
def get_current_times(location_info):
    tz = pytz.timezone(location_info.timezone)
    now = datetime.now(tz)
    return now

# Function to get CPU usage and temperature
def get_cpu_info():
    cpu_usage = int(psutil.cpu_percent())
    cpu_temp = int(psutil.sensors_temperatures()['cpu_thermal'][0][1])
    return cpu_usage, cpu_temp

# Function to get RAM and swap usage
def get_memory_info():
    ram_usage = int(psutil.virtual_memory().percent)
    swap_usage = int(psutil.swap_memory().percent)
    return ram_usage, swap_usage

# Function to get disk usage
def get_disk_usage():
    hd1_usage = int(psutil.disk_usage('/').percent)
    hd2_usage = int(psutil.disk_usage(DISK_PATH).percent)
    return hd1_usage, hd2_usage

# Function to get system uptime
def get_uptime():
    delta_time = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    uptime_days = delta_time.days
    uptime_hours = delta_time.seconds // 3600
    return uptime_days, uptime_hours

# Function to get public IP address
def get_public_ip():
    try:
        response = requests.get(CHECK_IP_URL)
        return response.text.strip()
    except Exception as e:
        return f'Exception: {e}'

# Function to get TOR IP address
def get_tor_ip():
    try:
        session = requests.session()
        session.proxies = PROXIES
        response = session.get(CHECK_IP_URL)
        return response.text.strip()
    except Exception as e:
        return f'Exception: {e}'

# Function to get authentication tokens
def get_auth_tokens():
    try:
        response = requests.request("POST", URL_AUTH, json=PAYLOAD_AUTH, verify=False)
        response.raise_for_status()
        data = response.json()
        return data["session"]["sid"], data["session"]["csrf"]
    except requests.RequestException as e:
        return f'Exception: {e}', None

# Function to get summary stats
def get_summary_stats(sid, csrf):
    try:
        headers = {
            'X-FTL-SID': sid,
            'X-FTL-CSRF': csrf
        }
        response = requests.request("GET", URL_SUMMARY, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return f'Exception: {e}'

# Main function to print system information
def main():
    LOCATIONINFO = LocationInfo(name="LittleBox", region="Unknown", timezone="Europe/Rome", latitude=45.4, longitude=9.1)
    now = get_current_times(LOCATIONINFO)
    print('  ' + now.strftime('%d/%m/%Y %H:%M'))

    cpu_usage, cpu_temp = get_cpu_info()
    print(f'CPU: {cpu_usage:3}%    TMP: {cpu_temp:3}C')

    ram_usage, swap_usage = get_memory_info()
    print(f'RAM: {ram_usage:3}%    SWP: {swap_usage:3}%')

    hd1_usage, hd2_usage = get_disk_usage()
    print(f'HD1: {hd1_usage:3}%    HD2: {hd2_usage:3}%')

    uptime_days, uptime_hours = get_uptime()
    print(f'Uptime: {uptime_days:6}d +{uptime_hours:2}h')

    public_ip = get_public_ip()
    print(f'IP: {public_ip.rjust(16, " ")}')

    tor_ip = get_tor_ip()
    print(f'TOR: {tor_ip.rjust(15, " ")}')

    sid, csrf = get_auth_tokens()
    if csrf is None:
        print(sid)  # Print the exception message if authentication fails
        return

    response = get_summary_stats(sid, csrf)
    if isinstance(response, dict):
        percent_blocked = response['queries']['percent_blocked']
        print(f'ADV Blocked: {percent_blocked:6.2f}%')
    else:
        print(response)  # Print the exception message if summary stats retrieval fails

if __name__ == "__main__":
    main()