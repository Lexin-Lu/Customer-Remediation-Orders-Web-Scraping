##### Import Required Libraries #####
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

##### Import utility functions #####
import utility


##### Set up the Chrome WebDriver #####
os.environ['WDM_SSL_VERIFY'] = '0'
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_services = Service(ChromeDriverManager().install())



##### Set up parameters #####
base_url = "https://www.consumerfinance.gov"
enforcement_path = "/enforcement/actions"
main_web_link = urljoin(base_url, enforcement_path)
today_timestamp = datetime.now().strftime("%Y%m%d")

##############################################################################
# INPUT NEEDED IN THIS SECTION

# specify the earliest date of an order
start_date = "2022-01-01T00:00:00"
# specify which detail items are needed (True: to include; False: not to include)
info_dict = {
    "Forum": True,
    "Court": True,
    "Docket_number": True,
    "Initial_filing_date": True,
    "Status": True,
    "Products": True,
    "Description": True,
    "Civil_money_penalty": True,
    "Redress_amount": True
}
# specify the output file name
base_output_name = "CFPB_enforcement_actions.xlsx"
# specify the path to store the output
base_output_path = "CFPB\\"

# SECTION ENDS
##############################################################################

output_path = base_output_path + today_timestamp + "_" + base_output_name


###### Helper functions #####
def get_total_pages(main_web_link):
    '''
    Get the total page of the main website
    Input: 
        main_web_link: the link of main website
    Output: 
        total_pages: the number of total pages
    '''
    # Navidate to the main page
    driver.get(main_web_link)
    time.sleep(2)

    # Parse the main page
    soup = BeautifulSoup(driver.page_source, "html.parser")
    page_input = soup.find('input', id = "m-pagination__current-page-0")
    if page_input and page_input.has_attr("max"):
        total_pages = int(page_input['max'])
    else: total_pages = 1

    return total_pages

def get_order_links(main_web_link):
    '''
    Get links of all orders within the specified time
    Input: 
        main_web_link: the link of main website
    Output: 
        order_links: a list containing all order links
    '''
    order_links = []
    page = 1
    total_page = get_total_pages(main_web_link)
    scrape = True
    while scrape:
        # Navigate to the page
        url = f"{main_web_link}?page={page}"
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

def get_order_details(link, info_dict):
    '''
    Get the values of detail items for each order
    Input:
        link: the link of each order
        info_dict: the parameters dictionary indicating which detail items are needed
    Output:
        order_detail: a dictionary containing all values of the required detail items for this order
    '''
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
        order_detail["Forum"] = utility.get_detail_value(detail_soup, ".m-related-metadata__item-container .m-list__item span")
    
    # Court
    if info_dict["Court"] and "Court" in all_items:
        court_values = utility.get_detail_value(detail_soup, ".m-related-metadata__item-container:nth-child(3)")
        if court_values:
            order_detail["Court"] = [court_value[5:] for court_value in court_values]
    else: order_detail["Court"] = None
    
    # Docket number
    if info_dict["Docket_number"] and "Docket number" in all_items:
        if "Court" in all_items: 
            order_detail["Docket_number"] = utility.get_detail_value(detail_soup, ".m-related-metadata__item-container:nth-child(4) p")
        elif "Court" not in all_items: 
            order_detail["Docket_number"] = utility.get_detail_value(detail_soup, ".m-related-metadata__item-container:nth-child(3) p")
    else: 
        order_detail["Docket_number"] = None

    # Initial filing date
    if info_dict["Initial_filing_date"] and "Initial filing date" in all_items:
        order_detail["Initial_filing_date"] = utility.get_detail_value(detail_soup, ".m-related-metadata__item-container time")
    else: order_detail["Initial_filing_date"] = None

    # Status
    if info_dict["Status"] and "Status" in all_items:
        order_detail["Status"] = utility.get_detail_value(detail_soup, ".m-related-metadata__status div")

    # Products
    if info_dict["Products"] and "Products" in all_items:
        order_detail["Products"] = utility.get_detail_value(detail_soup, ".a-tag-topic__text")

    # Description:
    if info_dict["Description"]:
        order_detail["Description"] = detail_soup.select("p:nth-child(1)")[0].get_text(strip=True)
    
    # Civil money penalty & Redress amount
    if info_dict["Civil_money_penalty"] or info_dict["Redress_amount"]:
        # Extract the whole description paragraph
        description = detail_soup.select("p:nth-child(1)")[0].get_text(strip=True)
        
        # Generate patterns and phrases for amount extracting
        number_pattern = r"\$\d{1,3}(?:\.\d{1,2})?(?:\s*million)?"
        phrases = ["redress", "refund", "penalty", "civil money penalty", "penalties"]        

        # Extract amounts
        amount_outputs = utility.extract_info_from_paragraph(description, order_detail["Institution"], phrases, number_pattern, if_not_found=None)
        
        # Civil money penalty
        if info_dict["Civil_money_penalty"]:
            order_detail["Civil_money_penalty"] = amount_outputs["Penalty Amount"] if amount_outputs and ("Penalty Amount" in amount_outputs.keys()) else None
        # Redress amount
        if info_dict["Redress_amount"]:
            order_detail["Redress_amount"] = amount_outputs["Redress Amount"] if amount_outputs and ("Redress Amount" in amount_outputs.keys()) else None

    return order_detail

def main(main_web_link, info_dict, output_path):
    '''
    Main execution function
    Input:
        main_web_link: the link of main website
        info_dict: the parameters dictionary indicating which detail items are needed
        output_path: the path to store the output
    '''
    # Navigate to the main page
    driver.get(main_web_link)
    time.sleep(2)

    # Step 1: Scrape order links within the specified time period
    print("Begin scraping order links...")
    order_links = get_order_links(main_web_link)
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
    df["Civil_money_penalty"] = df["Civil_money_penalty"].apply(lambda x: utility.standardize_amount(x) if pd.notnull(x) else x)
    df["Redress_amount"] = df["Redress_amount"].apply(lambda x: utility.standardize_amount(x) if pd.notnull(x) else x)
    print("The output dataframe is ready.")

    # Step 4: Output the result dataframe
    print("Outputing the results...")
    df.to_excel(output_path, index=False)


###### Execute codes #####
driver = webdriver.Chrome(service=chrome_services, options=chrome_options)
main(main_web_link, info_dict, output_path)
driver.quit()