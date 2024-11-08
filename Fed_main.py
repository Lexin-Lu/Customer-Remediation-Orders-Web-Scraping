###### Import Required Libraries #####
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

import utility


###### Set up the Chrome WebDriver #####
os.environ['WDM_SSL_VERIFY'] = '0'
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
#chrome_options.add_argument("headless")
chrome_services = Service(ChromeDriverManager().install())

driver = webdriver.Chrome(service=chrome_services, options=chrome_options)


###### Set up parameters #####
base_url = "https://www.federalreserve.gov"
enforcement_path = "/supervisionreg/enforcementactions.htm"
main_web_link = urljoin(base_url, enforcement_path)
today_timestamp = datetime.now().strftime("%Y%m%d")

##############################################################################
# INPUT NEEDED IN THIS SECTION

# specify the earliest date of an order
start_date = datetime.strptime("01/01/2022", "%m/%d/%Y")

# specify the relative path of raw data file
raw = "Fed\Fed_original.csv"

# specify the output file name
base_output_name = "Fed_enforcement_actions_cleaned.xlsx"
# specify the path to store the output
base_output_path = "Fed\\"

# SECTION ENDS
##############################################################################

output_path = base_output_path + today_timestamp + "_" + base_output_name



###### Read in raw data #####
df_raw = pd.read_csv(raw)
df_raw.columns


###### Clean and filter #####
df = df_raw.copy()

# Remove redundant columns
df = df.drop(columns=['Individual', 'Individual Affiliation', 'Name', 'Note'])

# Keep only orders after start date
df['Effective Date'] = pd.to_datetime(df['Effective Date'], errors = 'coerce', format="%m/%d/%Y")
df = df[df["Effective Date"] >= start_date]

# Keep only orders for banks 
df = df[df["Banking Organization"].notna()]

## Impute complete urls
df['URL'] = df['URL'].apply(lambda x: urljoin(base_url, x) if pd.notna(x) and x.startswith("/") else x)



###### Scrape description #####

# Helper function
def find_penalty_amount(text, offset = None):
    number_pattern = r"\$\d{1,3}(?:,\d{3})*(?:\.\d{1,5})?(?:\s*(billion|million|thousand))?"
    #matches = re.findall(number_pattern, text)
    amounts = [(match.group(), match.start(), match.end()) for match in re.finditer(rf"({number_pattern})", text)]
    # Find phrases and their start/end positions
    for amount, amount_start, amount_end in amounts:
        if offset:
            context_text = text[max(0, amount_start - offset): amount_end + offset].lower()
        else:
            context_text = text

        if re.search(r'(\bpenalty\b|\bpenalties\b|\bfine\b|\bfined\b|\bfines\b|\bfining\b)', context_text, re.IGNORECASE):  # Check for nearby keywords
            return amount
    
    return None


paragraph_exclusion = [
    "Additional enforcement actions can be searched for here.",
    "For media inquiries, please email media@frb.gov or call 202-452-2955."
]

for index, row in df.iterrows():
    # Navigate to the corresponding press page
    url = row['URL']
    driver.get(url)
    time.sleep(2)

    # Extract the title of the press
    try:
        press_title = driver.find_element(By.CSS_SELECTOR, '.title').text
    except:
        press_title = "Title not found"
    
    # Extract the description paragraph of the press
    description = []
    try:
        paragraphs = driver.find_elements(By.CSS_SELECTOR, 'div.col-xs-12.col-sm-8.col-md-8 p')
        for p in paragraphs:
            para = p.text
            if not any(phrase in para for phrase in paragraph_exclusion):
                description.append(para)
        description_text = '\n'.join(description)  # Combine all paragraphs into a single description text
    except:
        description_text = "Description not found"
    
    # Set extracted data into the DataFrame
    df.at[index, 'Press title'] = press_title
    df.at[index, 'Description'] = description_text
    

    # Extract the amount of civil money penalty if applicable
    if 'civil money penalty' in str(row['Action']).lower():
        # First check in the press title
        penalty_amount = find_penalty_amount(press_title)
        # If not found, check in the first paragraph of the description
        if not penalty_amount and description:
            penalty_amount = find_penalty_amount(description_text, 100)
        # Set civil money penalty in the DataFrame or mark for attachment check
        df.at[index, 'Civil money penalty'] = penalty_amount if penalty_amount else "Attachment check needed"
        # Convert penalty amount to numeric format
        df["Civil money penalty"] = df["Civil money penalty"].apply(lambda x: utility.standardize_amount(x) if x !="Attachment check needed" and pd.notnull(x) else x)

    else:
        df.at[index, 'Civil money penalty'] = None


# Close the driver after processing
driver.quit()

# Output the results
df.to_excel(output_path, index=False)


