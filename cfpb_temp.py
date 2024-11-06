# Import Required Libraries
import requests
import re
import os
import time
import pandas as pd
from itertools import chain
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
today_timestamp = datetime.now().strftime("%Y%m%d")
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
base_output_name = "CFPB_enforcement_actions.xlsx"
base_output_path = ""
outpath = today_timestamp + "_" + base_output_name


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

def calculate_distance(amount_start, amount_end, phrase_start, phrase_end):
    # Calculate distance based on relative positions of amount and phrase
    if phrase_start > amount_end:  # Phrase appears after amount
        return phrase_start - amount_end
    else:  # Phrase appears before amount
        return amount_start - phrase_end
    
def find_closest_phrase(amount_start, amount_end, phrases_positions):
    # Calculate closest phrase based on adjusted distance calculation
    closest_phrase, min_distance = None, float('inf')
    for phrase, (phrase_start, phrase_end) in phrases_positions:
        distance = calculate_distance(amount_start, amount_end, phrase_start, phrase_end)
        if distance < min_distance:
            min_distance = distance
            closest_phrase = phrase
    return closest_phrase

def extract_info_from_paragraph(paragraph, institution_name, phrases, number_pattern, if_not_found=None):
    # Generate institution name variants
    name_variants = generate_name_variants(institution_name)
    number_pattern = r"\$\d{1,3}(?:,\d{3})*(?:\.\d{1,5})?(?:\s*(billion|million|thousand))?"
    # Find dollar amounts and their start/end positions
    amounts = [(match.group(), match.start(), match.end()) for match in re.finditer(rf"({number_pattern})", paragraph)]
    # Find phrases and their start/end positions
    phrases_positions = []
    for phrase in phrases:  
        for match in re.finditer(re.escape(phrase), paragraph, re.IGNORECASE):
            phrases_positions.append((phrase, (match.start(), match.end())))
    # Process each amount to determine if it’s redress or penalty
    results = {}
    for amount, amount_start, amount_end in amounts:
        closest_phrase = find_closest_phrase(amount_start, amount_end, phrases_positions)
        context_text = paragraph[max(0, amount_start - 300): amount_end + 300].lower()
        # Decide amount type based on closest phrase
        if closest_phrase and (closest_phrase in context_text):
            if any(word in closest_phrase.lower() for word in ["penalty", "civil", "penalties"]) and any(re.search(re.escape(name.lower()), context_text) for name in name_variants):
                results["Penalty Amount"] = amount
            elif "redress" in closest_phrase.lower() and any(re.search(re.escape(name.lower()), context_text) for name in name_variants):
                results["Redress Amount"] = amount
    return results if results else if_not_found

# Step 2: Scrape details of each order
def get_order_details(link, info_dict):
    # Navigate to the detial page
    driver.get(link)
    time.sleep(2)

    # Parse the detial page contents
    detail_soup = BeautifulSoup(driver.page_source, "html.parser")

    # Find all available details in this page
    all_possible_items = ["Forum", "Court", "Docket number", "Initial filing date", "Status", "Products"]
    items = detail_soup.find_all("h3", class_ = "h4")
    all_items = []
    for item in items:
        if item.get_text(strip=True) in all_possible_items:
            all_items.append(item.get_text(strip=True))


    # Extract order detials
    order_detail = {}
    order_detail["Link"] = link

    # Name of the institution
    order_detail["Institution"] = detail_soup.find("div", class_ = "o-item-introduction").find("h1").get_text(strip=True)
    
    # Forum
    if info_dict["Forum"]: 
        order_detail["Forum"] = get_detail_value(detail_soup, ".m-related-metadata__item-container .m-list__item span")
    
    # Court
    if info_dict["Court"] and "Court" in all_items:
        court_values = get_detail_value(detail_soup, ".m-related-metadata__item-container:nth-child(3)")
        if court_values:
            order_detail["Court"] = [court_value[5:] for court_value in court_values]
    else: order_detail["Court"] = None
    
    # Docket number
    if info_dict["Docket_number"] and "Docket number" in all_items:
        if "Court" in all_items: 
            order_detail["Docket_number"] = get_detail_value(detail_soup, ".m-related-metadata__item-container:nth-child(4) p")
        elif "Court" not in all_items: 
            order_detail["Docket_number"] = get_detail_value(detail_soup, ".m-related-metadata__item-container:nth-child(3) p")
    else: 
        order_detail["Docket_number"] = None

    # Initial filing date
    if info_dict["Initial_filing_date"] and "Initial filing date" in all_items:
        order_detail["Initial_filing_date"] = get_detail_value(detail_soup, ".m-related-metadata__item-container time")
    else: order_detail["Initial_filing_date"] = None

    # Status
    if info_dict["Status"] and "Status" in all_items:
        order_detail["Status"] = get_detail_value(detail_soup, ".m-related-metadata__status div")

    # Products
    if info_dict["Products"] and "Products" in all_items:
        order_detail["Products"] = get_detail_value(detail_soup, ".a-tag-topic__text")

    # Civil money penalty & Redress amount
    if info_dict["Civil_money_penalty"] or info_dict["Redress_amount"]:
        # Extract the whole description paragraph
        description = detail_soup.select("p:nth-child(1)")[0].get_text(strip=True)
        
        # Generate patterns and phrases for amount extracting
        number_pattern = r"\$\d{1,3}(?:\.\d{1,2})?(?:\s*million)?"
        phrases = ["redress", "penalty", "civil money penalty", "penalties"]        

        # Extract amounts
        amount_outputs = extract_info_from_paragraph(description, order_detail["Institution"], phrases, number_pattern, if_not_found=None)
        
        # Civil money penalty
        if info_dict["Civil_money_penalty"]:
            order_detail["Civil_money_penalty"] = amount_outputs["Penalty Amount"] if amount_outputs and ("Penalty Amount" in amount_outputs.keys()) else None
        # Redress amount
        if info_dict["Redress_amount"]:
            order_detail["Redress_amount"] = amount_outputs["Redress Amount"] if amount_outputs and ("Redress Amount" in amount_outputs.keys()) else None

    return order_detail


def standardize_amount(amount_str):

    # Remove the dollar sign and commas
    amount_str = amount_str.replace('$', '').replace(',', '')

    # Check for "million", "billion", or "thousand" and convert accordingly
    if 'million' in amount_str:
        number = float(re.sub(r' million', '', amount_str)) * 1_000_000
    elif 'billion' in amount_str:
        number = float(re.sub(r' billion', '', amount_str)) * 1_000_000_000
    elif 'thousand' in amount_str:
        number = float(re.sub(r' thousand', '', amount_str)) * 1_000
    else:
        number = float(amount_str)  # Basic numeric amount without suffix

    # Format to "xxx,xxx.xxx"
    numeric_amout = f"{number:,.3f}".rstrip('0').rstrip('.')
    return numeric_amout # Remove trailing zeros and decimal if unnecessary 


def main(main_page_link, info_dict, output_path):
    # Navigate to the main page
    driver.get(main_page_link)
    time.sleep(2)

    # Step 1: Scrape order links within the specified time period
    print("Begin scraping order links...")
    order_links = get_order_links(main_page_link)
    print("Managed to get all order links")

    # Step 2: Scrape details of each order
    print("Begin scrap order details...")
    res = []
    for link in order_links:
        res.append(get_order_details(link, info_dict))
    print("Managed to scrape all order details")

    # Step 3: Convert the result into a clean Pandas dataframe
    df = pd.DataFrame(res)
    # Flatten lists in the dataframe
    for col in df:
        df[col] = df[col].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
    # Convert the amount units into scientifc format
    df["Civil_money_penalty"] = df["Civil_money_penalty"].apply(lambda x: standardize_amount(x) if pd.notnull(x) else x)
    df["Redress_amount"] = df["Redress_amount"].apply(lambda x: standardize_amount(x) if pd.notnull(x) else x)


    # Step 4: Output the result dataframe
    df.to_csv(output_path, index=False)


main(main_page_link, info_dict, output_path)