# Import Required Libraries
import requests
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import os

# Set up the Chrome WebDriver
os.environ['WDM_SSL_VERIFY'] = '0'
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_services = Service(ChromeDriverManager().install())

driver = webdriver.Chrome(service=chrome_services, options=chrome_options)


# Set up date filter and base urls
base_url = "https://www.consumerfinance.gov"
enforcement_path = "/enforcement/actions"
start_date = datetime(2022,1,1)


# Navigate to the base page
driver.get(base_url+enforcement_path)
time.sleep(2)


res = []

# Step 1: Scrape order links after 1/1/2022 across all pages
def get_order_links():
    order_links = []
    page = 1
    while True:
        # Navigate to the page
        url = f"{base_url}?page={page}"
        driver.get(url)
        time.sleep(2)
        
        # Parse the page contents
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find all order entries 
        orders = soup.find_all('article', class_ = "o-post-preview")
        if not orders: break # Stop if hit the end of the page
        print(orders)

        # Scrape all order link
        for order in orders: 
            date_tag = order.find('span', class_ = 'datetime').find("time")
            if date_tag:
                order_date = date_tag["datetime"]
                if order_date > "2022-01-01T00:00:00":
                    link_tag = order.find('h3', class_ = "o-post-preview__title").find('a')
                    order_links.append(base_url+link_tag['href'])
        page +=1

    return order_links


get_order_links()
