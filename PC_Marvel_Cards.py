import json
import time
import asyncio
import logging
import requests
from playwright.sync_api import sync_playwright
from typing import List, Dict
from get_agents import get_agent
from PC_scrape_cards import scrape_card_details
from excel_helper import write_data_to_file
import os

def get_cards_list(href):
    base_url = 'https://www.pricecharting.com'
    product_uri_list = []
    cursor = 0
    while cursor != -1:
        print(f"processing : {base_url}{href}?sort=&when=none&release-date=2025-01-08&cursor={cursor}&format=json")
        response = requests.get(f"{base_url}{href}?sort=&when=none&release-date=2025-01-08&cursor={cursor}&format=json")
        if response.status_code == 200:
            data = response.json()
            product_uri_list.extend([ (f'/game/{product['consoleUri']}/{product['productUri']}', product['id']) for product in data['products']])
            cursor = data.get('cursor', -1)
        else:
            break
    return product_uri_list



def priceChartingScrapper():
    
    with sync_playwright() as p:
        # Launch browser (headless=False to see what's happening)
        print('Launching Browser')
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent=get_agent()
        )
        print('Browser Launched')
        page = context.new_page()
        base_url = 'https://www.pricecharting.com'
        # Navigate to the main page
        print('navigating to pricecharting.com')

        page.goto('https://www.pricecharting.com')

        # Get all main category elements (Nintendo, Atari, etc.) under the "Video Games" section
        page.wait_for_selector('#trading-cards > ul.menu-dropdown', state='attached')
        main_categories = page.query_selector_all('#trading-cards > ul.menu-dropdown > li > a')[1:]
        print(main_categories)
        try:
            for category in main_categories:
                print(f"Processing category: {category.text_content()}")
                if category.text_content()=='Marvel Cards':
                    try:
                        # Click the category to open dropdown
                        
                        marvel_cards_list = page.locator('#trading-cards > ul.menu-dropdown > li > a:has-text("Marvel Cards")')
                        marvel_cards_list_url = marvel_cards_list.get_attribute('href')

                        new_page = browser.new_page()
                        new_page.goto(f"{base_url}{marvel_cards_list_url}")

                        new_page.wait_for_selector('.home-box.all')
                        set_list = new_page.locator('.home-box.all ul li a').all()
                        
                        print('Getting the Set List for Marvel Cards')
                        for set in set_list:
                            set_name = set.inner_text().strip()
                            safe_set_name = set_name.replace("/", "").replace("\\", "").replace("?", "").replace("*", "").replace(':','')

                            set_url = set.get_attribute('href')
                            print(f"Processing Set: {set_name}")

                            print(f'Checking for existing scrapped data for set {set_name}')
                            existing_data = []
                            try:
                                with open(f'data/{safe_set_name}.json', 'r', encoding='utf-8') as f:
                                    existing_data = json.load(f)
                            except Exception as e:
                                print(e)
                                print('file doesnot exist')

                            print(f'Getting Cards List for set {set_name}')

                            cards_list = get_cards_list(set_url)
                            print(f"Number of cards to save: {len(cards_list)} for {set_name}")
                            set_cards_list = []
                            
                            cards_data = []
                            if existing_data:
                                cards_data.extend(existing_data)
                            
                            existing_data_pc_ids = [ x['pricecharting_id'] for x in existing_data if x]

                            for index, card_uri in enumerate(cards_list):
                                try:
                                    print(f"scrapping card {index} from {set_name}")

                                    product_pc_id = card_uri[1]
                                    detail_page = browser.new_page()
                                    if product_pc_id not in existing_data_pc_ids:
                                        card_details = scrape_card_details(card_uri[0], detail_page)
                                        cards_data.append(card_details)

                                    if index%50 == 0 or index!=0:
                                        os.makedirs('data', exist_ok=True)
                                        with open(f'data/{safe_set_name}.json', 'w', encoding='utf-8') as f:
                                            json.dump(cards_data, f, indent=4, ensure_ascii=False)

                                except Exception as e:
                                    print(f'error processing card with uri : {card_uri}')
                                    print(e)
                                finally:
                                    detail_page.close()

                            if cards_data:
                                write_data_to_file(cards_data, f'Marvel-Cards-{set_name}', "Marvel Cards")

                    except Exception as e:
                        print(f"Error processing category: {str(e)}")

        finally:
            browser.close()

def retry_wrapper(func, retries=3, delay=1):
    """Retry mechanism for failed operations"""
    def wrapper(*args, **kwargs):
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == retries - 1:  # Last attempt
                    raise e
                time.sleep(delay)
                continue
    return wrapper

if __name__ == "__main__":
    try:
        priceChartingScrapper()
    except Exception as e:
        print(f"Main error: {str(e)}")
