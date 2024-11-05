# Import Required Libraries
import requests
import re
import os
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



# Set up the Chrome WebDriver
os.environ['WDM_SSL_VERIFY'] = '0'
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_services = Service(ChromeDriverManager().install())

driver = webdriver.Chrome(service=chrome_services, options=chrome_options)


# Set up parameters
base_url = "https://www.consumerfinance.gov"
enforcement_path = "/enforcement/actions"
main_page_link = urljoin(base_url, enforcement_path)
start_date = "2022-01-01T00:00:00"
info_dict = {
    "Forum": True,
    "Court": True,
    "Docket_number": True,
    "Initial_filing_date": True,
    "Status": True,
    "Products": True,
    "Civil_money_penalty": True,
    "Redress_amount": True
}


driver.get(main_page_link)
time.sleep(2)


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
def get_order_links(main_page_link):
    order_links = []
    page = 1
    total_page = get_total_pages(main_page_link)
    scrape = True
    while scrape:
        # Navigate to the page
        url = f"{main_page_link}?page={page}"
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
                    order_links.append(urljoin(base_url,link_tag['href']))
        page +=1
        if page > total_page: 
            break # stop if hit the last page
        
    return order_links

temp_1104 = get_order_links(main_page_link)
len(temp_1104)


def get_detail_value(detail_soup, selector):
    details = detail_soup.select(selector)
    detail_values = []
    for detail in details:
        detail_values.append(detail.get_text(strip=True))
    
    return detail_values

def generate_name_variants(name):
    # Full name & the first word
    institution_variants = [name, name.split()[0]]
    # Name without commas and suffixes
    suffixes = ["Inc.", "LLC", "N.A.", "et", "al.", "Corp.", "Co.", "Ltd."]
    name_parts = name.replace(",", "").split()
    
    if ";" in name: 
        names = name.split(";")
        institution_variants.extend(names)
        cleaned_names = []
        for n in names:
            n_parts = n.replace(",", "").split()
            cleaned_names.append(" ".join([part for part in n_parts if part not in suffixes]))
        institution_variants.extend(cleaned_names)
        institution_variants.append("; ".join(n for n in cleaned_names))
    else: 
        cleaned_name = " ".join([part for part in name_parts if part not in suffixes])
        institution_variants.append(cleaned_name)    


    return list(set(institution_variants))


def extract_info_from_paragraph(paragraph, pattern, if_not_found):
    matches = re.findall(pattern, paragraph, re.IGNORECASE)
    if matches:
        for match in matches:
            amount = next((m for m in match if m and m.startswith("$")), None)
            if amount: 
                return amount
    else:
        return if_not_found


# Step 2: Scrape details of each order
def get_order_details(link, info_dict):
    # Navigate to the detial page
    link = temp_1104[4]
    driver.get(link)
    time.sleep(2)

    # Parse the detial page contents
    detail_soup = BeautifulSoup(driver.page_source, "html.parser")

    # Extract order detials
    order_detail = {}
    order_detail["Link"] = link

    # Name of the institution
    order_detail["Institution"] = detail_soup.find("div", class_ = "o-item-introduction").find("h1").get_text(strip=True)
    
    # Forum
    if info_dict["Forum"]: 
        order_detail["Forum"] = get_detail_value(detail_soup, ".m-related-metadata__item-container .m-list__item span")
    
    # Court
    elif info_dict["Court"]:
        order_detail["Court"] = get_detail_value(detail_soup, ".m-related-metadata__item-container:nth-child(3)")
        for i in range(len(order_detail["Court"])):
            order_detail["Court"][i] = order_detail["Court"][i][5:]
    
    # Docket number
    elif info_dict["Docket_number"]:
        order_detail["Docket_number"] = get_detail_value(detail_soup, ".m-related-metadata__item-container:nth-child(4) p")
    
    # Initial filing date
    elif info_dict["Initial_filing_date"]:
        order_detail["Initial_filing_date"] = get_detail_value(detail_soup, ".m-related-metadata__item-container time")
    
    # Status
    elif info_dict["Status"]:
        order_detail["Status"] = get_detail_value(detail_soup, ".m-related-metadata__status div")
    
    # Products
    elif info_dict["Products"]:
        order_detail["Products"] = get_detail_value(detail_soup, ".a-tag-topic__text")
    
    # Civil money penalty & Redress amount
    elif info_dict["Civil_money_penalty"] or info_dict["Redress_amount"]:
        # Extract the whole description paragraph
        description = detail_soup.select("p:nth-child(1)")[0].get_text(strip=True)
        # Create a list of institution name variants
        name_variants = generate_name_variants(order_detail["Institution"])
        # Generate patterns for amount extracting
        name_pattern = "|".join(re.escape(v) for v in name_variants)
        number_pattern = r"\$\d{1,3}(?:\.\d{1,2})?(?:\s*million)?"

        # Civil money penalty
        if info_dict["Civil_money_penalty"]:
            # Generate full pattern
            target_phrase = ["civil money penalty", "penalty"]
            avoid_phrase = ["redress", "redressing"]
            full_pattern = generate_full_pattern(name_pattern, number_pattern, target_phrase, avoid_phrase)
            # Pull the civil money penalty amount
            order_detail["Civil_money_penalty"] = extract_info_from_paragraph(description, full_pattern, "No civil money penalty found")
        
        # Redress amount
        elif info_dict["Redress_amount"]:
            # Generate full pattern
            phrase = "redress"
            avoid_phrase = "civil money penalty|penalty"
            full_pattern = generate_full_pattern(name_pattern, number_pattern, phrase, avoid_phrase)
            # Pull the civil money penalty amount
            order_detail["Redress_amount"] = extract_info_from_paragraph(description, full_pattern, "No redress amount found")

    return order_detail



def generate_full_pattern(name_pattern, number_pattern, target_phrase, avoid_phrase):
    # Generate phrase patterns
    target_pattern = "|".join([re.escape(phrase) for phrase in target_phrase])
    avoid_pattern = "|".join([re.escape(phrase) for phrase in avoid_phrase])

    # Generate full pattern
    full_pattern = (
            rf"(?:(?:{name_pattern}).*?({number_pattern})(?!.*?(?:{avoid_pattern})).*?(?:{target_pattern})|"     # Name - $ - Phrase
            rf"(?:{name_pattern}).*?(?:{target_pattern}).*?({number_pattern})(?!.*?(?:{avoid_pattern}))|"        # Name - Phrase - $
            rf"(?:{target_pattern}).*?({number_pattern})(?!.*?(?:{avoid_pattern})).*?(?:{name_pattern})|"        # Phrase - $ - Name
            rf"(?:{target_pattern}).*?(?:{name_pattern}).*?({number_pattern})(?!.*?(?:{avoid_pattern}))|"        # Phase - Name - $
            rf"({number_pattern})(?!.*?(?:{avoid_pattern})).*?(?:{target_pattern}).*?(?:{name_pattern})|"        # $ - Phrase - Name
            rf"({number_pattern})(?!.*?(?:{avoid_pattern})).*?(?:{target_pattern}).*?(?:{name_pattern}))"        # $ - Name - Phrase
            )        
    return full_pattern


description = "On October 23, 2024, the Bureau issued an order against Goldman Sachs Bank USA (Goldman). The order requires Goldman to pay $19.8 million in redress to consumers and a $45 million civil money penalty and to come into compliance with the law.The Bureau separately took action against Apple for its role in marketing and servicing the Apple Card. The order against Apple requires it to pay a $25 million civil money penalty and to come into compliance with the law."
name = "Goldman Sachs Bank USA"
# Create a list of institution name variants
name_variants = generate_name_variants(name)
# Generate patterns for amount extracting
name_pattern = "|".join(re.escape(v) for v in name_variants)
number_pattern = r"\$\d{1,3}(?:\.\d{1,2})?(?:\s*million)?"
phrase = "redress|redressing"
avoid_phrase = "civil money penalty|penalty" 
full_pattern = generate_full_pattern(name_pattern, number_pattern, phrase, avoid_phrase)
# Pull the civil money penalty amount
extract_info_from_paragraph(description, full_pattern, "No redress amount found")




# Main function
# res = []
#def main():
    # Navigate to the base page
    # driver.get(base_url+enforcement_path)
    # time.sleep(2)