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
start_date = datetime(2022,1,1,0,0,0)



# Step 1: Get the total page of the website
def get_total_pages(main_page_link):
    # Navidate to the main page
    driver.get(main_page_link)
    time.sleep(2)

    # Parse the main page
    soup = BeautifulSoup(driver.page_source, "html.parser")
    page_input = soup.find('input', id = "m-pagination__current-page-0")
    if page_input and page_input.has_attr("max"):
        total_pages = int(page_input['max'])
    else: total_pages = 1

    return total_pages


# Step 2: Scrape order links after 1/1/2022 across all pages
def get_order_links():
    order_links = []
    page = 1
    main_page_link = base_url+enforcement_path
    scrape = True
    while scrape:
        # Navigate to the page
        url = f"{base_url+enforcement_path}?page={page}"
        driver.get(url)
        time.sleep(2)
        
        # Parse the page contents
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find all order entries 
        orders = soup.find_all('article', class_ = "o-post-preview")
        if not orders: 
            break # stop if hit the end of the page

        # Scrape all order link
        for order in orders: 
            date_tag = order.find('span', class_ = 'datetime').find("time")
            if date_tag:
                order_date = date_tag["datetime"]
                if order_date <=  start_date:
                    scrape = False
                    break # stop if prior to start date
                else:
                    link_tag = order.find('h3', class_ = "o-post-preview__title").find('a')
                    order_links.append(base_url+link_tag['href'])
        page +=1
        if page > get_total_pages(main_page_link): 
            break # stop if hit the last page
        
    return order_links

temp_1104 = get_order_links()
len(temp_1104)


# Step 2: Scrape details of each order
def get_order_details(link):
    # Navigate to the detial page
    link = temp_1104[4]
    driver.get(link)
    time.sleep(2)

    # Parse the detial page contents
    detail_soup = BeautifulSoup(driver.page_source, "html.parser")

    # Extract order detials
    order_detail = {}

    details_items = detail_soup.find_all("div", class_ = "m-related-metadata__item-container")

# Forum
# Docket number
# Initial filing date
# Status
# Products
# Name of the institution
# Civil money penalty
# Redress amount


# Main function
# res = []
#def main():
    # Navigate to the base page
    # driver.get(base_url+enforcement_path)
    # time.sleep(2)


    

