import re
import os
import time
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin



def get_detail_value(detail_soup, selector):
    '''
    Get the value of the input item
    Input:
        detail_soup: the sparsed html of the detail page using BeautifualSoup package
        selector: the CSS selector of the item whose value is to be extracted
    Output:
        detail_values: a list containling all values for the specific item
    '''
    details = detail_soup.select(selector)
    detail_values = []
    for detail in details:
        detail_values.append(detail.get_text(strip=True))
    
    return detail_values


def generate_name_variants(name):
    '''
    Generate common variants given the name of an institution
    Input:
        name: institution name
    Output:
        a list containing all common variants of the institution name
    '''
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


def calculate_distance(amount_start, amount_end, phrase_start, phrase_end):
    '''
    Calculate distance based on relative positions of amount and phrase
    Input: 
        amount_start: the start position of the amount
        amount_end: the end position of the amount
        phrase_start: the start position of the phrase
        phrase_end: the end position of the phrase
    Output:
        the distance between the amount and the phrase
    '''
    if phrase_start > amount_end:  # Phrase appears after amount
        return phrase_start - amount_end
    else:  # Phrase appears before amount
        return amount_start - phrase_end


def find_closest_phrase(amount_start, amount_end, phrases_positions):
    '''
    Find the closest phrase based on the distance calculation, which will be used to decide the input amount is redress or civil money penalty
    Input:
        amount_start: the start position of the amount
        amount_end: the end position of the amount
        phrases_positions: a list of position of specified phrases
    Output:
        closest_phrase: the phrase that is closest to the amount
    '''
    closest_phrase, min_distance = None, float('inf')
    for phrase, (phrase_start, phrase_end) in phrases_positions:
        distance = calculate_distance(amount_start, amount_end, phrase_start, phrase_end)
        if distance < min_distance:
            min_distance = distance
            closest_phrase = phrase
    return closest_phrase


def extract_info_from_paragraph(paragraph, institution_name, phrases, number_pattern, if_not_found=None):
    '''
    Extract amount information from a paragraph and decide the category (penalty vs. redress)
    Input:
        paragraph: a text paragraph to extract information from
        institution_name: the institution name that the amount should be tied to
        number_pattern: a regex pattern of amount
        if_not_found: value to return if the amount is not found, default None
    Output: 
        result (if amount that meets requirements is found): a dictionary whose keys are the category of the amount and values are the amount
        if_not_found (if amount that meets requirements is not found)
    
    '''
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
            elif any(word in closest_phrase.lower() for word in ["redress", "refund"]) and any(re.search(re.escape(name.lower()), context_text) for name in name_variants):
                results["Redress Amount"] = amount
    return results if results else if_not_found


def standardize_amount(amount_str):
    '''
    Standardize the format of the amount columns into "xxx,xxx,xxx.xx" format
    Input: 
        amount_str: the amount in string
    Output:
        numeric_amount: the numeric and well-formatted amount
    '''
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
    numeric_amount = f"{number:,.3f}".rstrip('0').rstrip('.')
    return numeric_amount # Remove trailing zeros and decimal if unnecessary 