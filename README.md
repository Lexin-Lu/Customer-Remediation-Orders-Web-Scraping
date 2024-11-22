# Enforcement Action Consent Orders Data Collection

## Overview
This repository contains web-scraping scripts, input data, and output files for collecting enforcement action consent orders from CFPB, FRB, FDIC, and OCC websites as of Nov 8, 2024. The project supports customer remediation platform research by collecting and analyzing critical data such as civil money panelty, product type, etc.

---

## Table of Contents
1. [Introduction](#introduction)
2. [Pre-requisites](#prerequisites)
3. [Project Structure](#project-structure)
4. [Installation and Setup](#installation-and-setup)
5. [Data Collection Process](#data-collection-process)
6. [Limitations and Assumptions](#limitations-and-assumptions)
7. [Future Enhancements](#future-enhancements)
8. [Contact Information](#contact-information)

---

## Introduction
This project automates the collection of enforcement action consent order data issued after 1/1/2022 and to financial and non-financial institutions (primarily banks) from regulatory websites. The goal is to provide a structured dataset for efficient analysis for customer remediation efforts, focusing on product type, penalties and other relevant details.

### Scope of Data Collection
The data collection focuses on:
1. Consent orders issued after January 1, 2022.
2. Consent orders directed at institutions, primarily banks but also including other financial and non-financial companies.

### Source Data
The data were collected from four regulatory websites. Below is the methodology for each websit:
1. **CFPB**
    - Source: [CFPB Enforcement Actions](https://www.consumerfinance.gov/enforcement/actions/)
    - Method: 
        - Web-scraping each action for institution, content paragraph and action details
        - Manually remove orders issued to individuals
2. **FRB**
    - Source: [FRB Enforcement Actions](https://www.federalreserve.gov/supervisionreg/enforcementactions.htm)
    - Method: 
        - Download all historical orders from the website and clean and filter for orders within scope via codes
        - Navigate to the press release links (provided in the download data) and web-scrape descriptive paragraphs containing penalties and remediation details
3. **FDIC**
    - Source: [FDIC Order Search Form](https://orders.fdic.gov/s/searchform)
    - Method: Use the search and download tool provided on the website to filter for orders within scope, search, and download dataset
4. **OCC**
    - Source: [OCC Enforcement Actions Search](https://apps.occ.gov/EASearch)
    - Method: Use the search and download tool provided on the website to filter for orders within scope, search, and download dataset

### Summary of Results
The following table provides a summary of the consent orders collected: 
| Regulator | Number of consent orders(institutions) | Number of orders that may have resulted with cusotmer remediation |
|-----------|----------------------------------------|-------------------------------------------------------------------|
| CFPB      | 70                                     | 69                                                                |
| FRB       | 51                                     | 14                                                                |
| FDIC      | 307                                    | 36                                                                |
| OCC       | 67                                     | 7                                                                 |


---

## Pre-requisites
To run the scripts, you will need the following:
- Python 3.8+
- Libraries:
    - `re`
    - `os`
    - `time`
    - `pandas`
    - `beautifulsoup4`
    - `datetime`
    - `selenium`
- Web driver: this project uses ChromeDriver for Selenium
- Access to input data file: **store the downloaded FRB enforcement actions data under `FRB` folder**

---

## Project Structure
The repository is organized as follows:
```
|--- CFPB/          # Folder for storing output files related to CFPB
|--- FRB/           # Folder for storing original input file and output files related to FRB
|--- CFPB_main.py   # Main script for CFPB web-scraping and data collection
|--- FRB_main.py    # Main script for FRB data cleaning and web-scraping
|--- utility.pu     # Script containing neccessary helper functions
|--- README.md      # Project document
```

---

## Installation and Setup
Follow these steps to set up the project:
1. Clone the repository:
```
git clone https://github.com/Lexin-Lu/Customer-Remediation-Orders-Web-Scraping.git
cd [your-repository path]
```
2. Install the required Python libraries if needed
```
pip install [library name]
```

---

## Data Collection Process
1. **CFPB**
    - Sript: `CFPB_main.py`
    - Description: Extracts enforcement actions details, including institution name, forum, court, docket number, initial filing date, status, products, civil money penalty, redress amount, description paragraph, and order link.
    - Output file: an Excel file with structured data, located under `CFPB` folder
    - Step-by-step Execution: 
        1. Open `CFPB_main.py`
        2. Modify **the start date of the lookback period**(`start_date`), **which detail elements are needed**(`info_dict`) (by default all elements are selected. Set into *False* if any element is unwant), and **output file name**(`base_output_name`) in the below section (where user inputs are needed)
            ```
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
            ```
        3. Select the whole script and run all
        4. Open the output file in the specified location and manually remove orders issued to individuals

2. **FRB**
    - Script: `FRB_main.py`
    - Description: Clean and filter orders in scope (after 1/1/2022 and to institution), and then navigate to the press release links provided in the input table to web-scrape descriptive paragraphs
    - Output file: an Excel file with structured data, located under `FRB` folder
    - Step-by-step Execution: 
        1. Go to [FRB Enforcement Actions](https://www.federalreserve.gov/supervisionreg/enforcementactions.htm) and download all historical orders from the website
        2. Copy the csv file to the `FRB` folder as input data
        3. Open `FRB_main.py`
        4. Modify **the start date of the lookback period**(`start_date`), **the relative file path of the original FRB data downloaded from the website** (`raw`), and the output file name (`base_output_name`) in the below section (where user inputs are needed)
            ```
            # INPUT NEEDED IN THIS SECTION

            # specify the earliest date of an order
            start_date = datetime.strptime("01/01/2022", "%m/%d/%Y")

            # specify the relative path of raw data file
            raw = "FRB\FRB_original.csv"

            # specify the output file name
            base_output_name = "FRB_enforcement_actions_cleaned.xlsx"
            # specify the path to store the output
            base_output_path = "FRB\\"

            # SECTION ENDS
            ```
        5. Select the whole script and run all
        6. Open the output file, filter `Civil money penalty > $0`, assuming orders with a civil money penalty have potential impact on customers
        7. Manually review the press (`Description` column) and order pdf attachment in the press page if need to summarize the product types

3. **FDIC**
    - Step-by-step Execution:
        1. Go to [FDIC Order Search Form](https://orders.fdic.gov/s/searchform)
        2. Modify the filter "Issued Data Between" to be the start date of the lookback period
        3. Click "Search"
        4. Click "Export Results" and download dataset
        5. Open the output file, filter `CMP Amount > $0`, assuming orders with a civil money penalty have potential impact on customers
        6. Use the corresponding link to navigate to the order pdf (`File URL` column) and manually summarize the product types
4. **OCC**
    - Step-by-step Execution:
        1. Go to [OCC Enforcement Actions Search](https://apps.occ.gov/EASearch)
        2. Click "Advanced..."
        3. Modify the filter "Enter Start Date Range" to be the start date of the lookback period, and check "Show Records for Institutions" box
        4. Click "Search"
        5. Select "CVS(Excel)" for "Save As" and it will download the search results automatically
        6. Open the output file, filter `Amount > $0`, assuming orders with a civil money penalty have potential impact on customers
        6. Use column `DocketNumber` and manually find the corresponding order pdf by the link provided in the search results after step 4 
        7. Manually summarize the product types

---

## Limitations and Assumptions
- Website structure changes may require updates to the scraping scripts
- Manual filtering and review is necessary to identify product types for FRB, FDIC and OCC data
- Some enforcement actions may not include all desired fields (e.g., civil money penalty and redress amount were extracted from the paragraph text in CFPB)

---

## Future Enhancements
To further improve the project, the following enhancements are planned: 
- Automate product type identification for FRB, FDIC and OCC data (e.g., a Machine learning text classification model or leveraging OWL and other AI tools)
- Develope a scheduler (e.g., `cron` jobs or a task scheduler like `APScheduler`) to automate the entire data collection process on a recurring bases (e.g., every two months), including
    - Run all scripts sequentially
    - Save updated data in the specified location
    - Send notifications or logs summarizing the updates
- Improve error handling for website structure changes

---

## Contact Information
Code produced by Oliver Wyman. In case of any question or feedback,  please refer to: Lexin Lu (lexin.lu@oliverwyman.com)