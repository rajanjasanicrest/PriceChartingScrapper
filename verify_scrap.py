import json
import time
import asyncio
import logging
import requests
from pathlib import Path
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
        # print(f"processing : {base_url}{href}?sort=&when=none&release-date=2025-01-08&cursor={cursor}&format=json")
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
        need_scrapping = []
        try:
            for category in main_categories:
                print(f"Processing category: {category.text_content()}")
                if category.text_content()=='Marvel Cards':
                    try:
                        # Click the category to open dropdown
                        
                        magic_cards_list = page.locator('#trading-cards > ul.menu-dropdown > li > a:has-text("Marvel Cards")')
                        magic_cards_list_url = magic_cards_list.get_attribute('href')

                        new_page = browser.new_page()
                        new_page.goto(f"{base_url}{magic_cards_list_url}")

                        new_page.wait_for_selector('.home-box.all')
                        set_list = new_page.locator('.home-box.all ul li a').all()
                        
                        print('Getting the Set List for Magic Cards')
                        for set in set_list:
                            set_name = set.inner_text().strip()
                            safe_set_name = set_name.replace("/", "").replace("\\", "").replace("?", "").replace("*", "").replace(':','')

                            set_url = set.get_attribute('href')
                            # print(f"Processing Set: {set_name}")
                            print(f'Checking for {set_name}')
                            existing_data = []
                            try:
                                with open(f'data/{safe_set_name}.json', 'r', encoding='utf-8') as f:
                                    existing_data = json.load(f)

                                cards_list = get_cards_list(set_url)
                                num_of_cards = len(cards_list)
                                scrapped_num_of_cards = len(existing_data)

                                if scrapped_num_of_cards != num_of_cards:
                                    print(set_name, "requires rescrapping")
                                    print(f"has {num_of_cards} || scrapped {scrapped_num_of_cards}")
                                    need_scrapping.append(set_name)
                                else:
                                    print('ok')

                            except Exception as e:
                                print(e)
                                print(f'{set_name} pending to scrapped')

                    except Exception as e:
                        print(e)
                    finally:
                        new_page.close()
        except Exception as e:
            print(e)

        finally:
            browser.close()
    
        print(need_scrapping)
if __name__ == '__main__':
    priceChartingScrapper()