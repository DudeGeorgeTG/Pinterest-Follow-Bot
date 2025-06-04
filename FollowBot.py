import re
import json
import time
import random
import secrets
import requests
import ua_generator
import threading
from datetime import datetime
from solver import Solver
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Back, Style, init
import os
import logging
from typing import List, Optional, Dict, Any

os.system("cls")
init(autoreset=True)

ACCOUNT_USERNAME = 'dudegeorge'
FOLLOW_USER = True
PROFILE_USER_OPTIONS = '{"options":{"user_id":"895090632098603335"},"context":{}}'
PROFILE_USERNAME = '/3P32/'


BASE_URL = 'https://co.pinterest.com'
RECAPTCHA_SITE_KEY = '6Ldx7ZkUAAAAAF3SZ05DRL2Kdh911tCa3qFP0-0r'
MAX_WORKERS = 10
REQUEST_TIMEOUT = 30
ACCOUNTS_FILE = 'pinterestaccounts.txt'
PROXIES_FILE = 'proxies.txt'
CAPTCHA_TOKEN_LENGTH = 50 


LOG_FORMAT = (
    f"{Fore.CYAN}%(asctime)s{Fore.RESET} | "
    f"{Fore.BLUE}%(levelname)s{Fore.RESET} | "
    f"{Fore.MAGENTA}%(message)s{Fore.RESET}"
)


logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def print_success(message: str) -> None:
    print(f"{Fore.GREEN}✓ {message}{Fore.RESET}")

def print_info(message: str) -> None:
    print(f"{Fore.CYAN}→ {message}{Fore.RESET}")

def print_action(message: str) -> None:
    print(f"{Fore.BLUE}• {message}{Fore.RESET}")

def pinterest_setup(session: requests.Session, url: str) -> None:
    try:
        site = session.get(url, timeout=REQUEST_TIMEOUT)
        session.cookies.update(site.cookies)
        session.headers.update({
            'X-App-Version': 'd31bac2',
            'X-Csrftoken': site.cookies['csrftoken'],
            'X-Pinterest-Appstate': 'active',
            'X-Pinterest-Source-Url': '/signup/step3/',
            'X-Pinterest-Pws-Handler': 'www/signup/step[step].js',
            'X-Requested-With': 'XMLHttpRequest'
        })
    except requests.exceptions.RequestException as e:
        logger.error(f"Pinterest setup failed: {e}")
        raise

def get_recaptcha_token(solution: Solver) -> str:
    re_token = solution.token()
    truncated_token = re_token[:CAPTCHA_TOKEN_LENGTH] + ('...' if len(re_token) > CAPTCHA_TOKEN_LENGTH else '')
    print_action(f"Captcha solved: {truncated_token}")
    return re_token

def follow_user(session: requests.Session, url: str, username: str) -> bool:
    try:
        session.headers.update({
            'X-Pinterest-Source-Url': PROFILE_USERNAME,
            'X-Pinterest-Pws-Handler': 'www/[username].js'
        })

        response = session.post(
            f'{url}/resource/UserFollowResource/create/',
            data={
                'source_url': PROFILE_USERNAME,
                'data': PROFILE_USER_OPTIONS
            },
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            print_success(f"Followed user: {username}")
            return True
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to follow user: {e}")
        return False

def random_string(length: int = 12) -> str:
    return ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(length))

def create_account(username: str, session: requests.Session, url: str) -> bool:
    try:
        solution = Solver(RECAPTCHA_SITE_KEY, url)
        username_full = f"{username}_{random.randint(10000, 30000)}"
        email = f"{random_string()}@gmail.com"
        password = secrets.token_urlsafe(8)

        signup_data_options = {
            "options": {
                "type": "email",
                "birthday": "988934400",
                "email": email,
                "first_name": username_full,
                "password": password,
                "has_ads_credits": False,
                "recaptchaV3Token": get_recaptcha_token(solution),
                "user_behavior_data": "{}",
                "visited_pages": "",
                "get_user": ""
            },
            "context": {}
        }

        response = session.post(
            f'{url}/resource/UserRegisterResource/create/',
            data={
                'source_url': '/signup/step3/',
                'data': json.dumps(signup_data_options)
            },
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            with open(ACCOUNTS_FILE, 'a') as f:
                f.write(f'{username_full}:{email}:{password}\n')
            session.cookies.update(response.cookies.get_dict())
            print_success(f"Account created: {username_full}")
            
            if FOLLOW_USER:
                follow_user(session, url, username_full)
            return True
        return False
    except Exception as e:
        logger.error(f"Account creation failed: {e}")
        return False

def configure_session(proxies: Optional[List[str]] = None) -> requests.Session:
    session = requests.Session()
    ua = ua_generator.generate(device='desktop', browser=('chrome', 'edge'))

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "es-US,es-419;q=0.9,es;q=0.8",
        "cache-control": "max-age=0",
        "sec-ch-ua": ua.ch.brands,
        "sec-ch-ua-mobile": ua.ch.mobile,
        "sec-ch-ua-platform": ua.ch.platform,
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": ua.text
    }
    session.headers.update(headers)

    if proxies:
        proxy = random.choice(proxies).strip()
        session.proxies = {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
    
    return session

def run_pinterest_thread(username: str, proxies: Optional[List[str]]) -> None:
    try:
        session = configure_session(proxies)
        pinterest_setup(session, BASE_URL)
        create_account(username, session, BASE_URL)
    except Exception as e:
        logger.error(f"Thread execution failed: {e}")
    finally:
        if 'session' in locals():
            session.close()

def load_proxies() -> List[str]:
    try:
        with open(PROXIES_FILE, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
            if not proxies:
                logger.warning("No proxies found in proxies.txt")
            return proxies
    except FileNotFoundError:
        logger.error("proxies.txt file not found")
        return []

def main() -> None:
    os.system("cls")
    print_info("Pinterest Account Creator + Follow Bot")
    print_info("-----------------------")
    
    try:
        amount = int(input(f'{Fore.YELLOW}Enter account amount: {Fore.RESET}'))
    except ValueError:
        print(f"{Fore.RED}Please enter a valid number{Fore.RESET}")
        return
    
    proxies = load_proxies()
    print_action(f"Starting creation of {amount} accounts...")

    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(run_pinterest_thread, ACCOUNT_USERNAME, proxies) 
                      for _ in range(amount)]
            
            for future in futures:
                future.result()

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Process interrupted by user{Fore.RESET}")
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {e}{Fore.RESET}")
    finally:
        print_info("Process completed")

if __name__ == '__main__':
    main()
