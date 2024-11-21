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
6. [Output Files](#output-files)
7. [Limitations and Assumptions](#limitations-and-assumptions)
8. [Future Enhancements](#future-enhancements)
9. [Contact Information](#contact-information)

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










### Data Collection Process
1. **CFPB**
    - Source: [CFPB Enforcement Actions](https://www.consumerfinance.gov/enforcement/actions/)
    - Method: 
        - Web-scraping each action for institution, content paragraph and action details
        - Manually remove orders issued to individuals
2. **Fed**
    - Source: [Fed Enforcement Actions](https://www.federalreserve.gov/supervisionreg/enforcementactions.htm)
    - Method: 
        - Download all historical orders from the website
        - Copy to the "Fed" folder as input and clean and filter the data set for orders within scope
        - Navigate to the press release links (provided in the download data) and web-scrape descriptive paragraphs containing penalties and remediation details
3. **FDIC**
    - Source: [CFPB Enforcement Actions](https://www.consumerfinance.gov/enforcement/actions/)
    - Method: Web-scraping each action for institution, content paragraph and action details
4. **OCC**
    - Source: [CFPB Enforcement Actions](https://www.consumerfinance.gov/enforcement/actions/)
    - Method: Web-scraping each action for institution, content paragraph and action details
The scripts extract data on 