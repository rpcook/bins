import re
# from datetime import datetime

import requests
from bs4 import BeautifulSoup
import html
import json

def scrape_bin_date_website(street_address=None):
    # TODO: think about error handling and return value(s)
    session = requests.Session()

    ## Get page (for cookie + webpage_token)
    url_stem = "https://waste.nc.north-herts.gov.uk"
    input_url = "/w/webpage/find-bin-collection-day-input-address"
    r0 = session.get(url_stem+input_url)

    # TODO: need to check for "page down for maintenance" (redirects to here: https://waste.nc.north-herts.gov.uk/w/webpage/system-maintenance-page)
    # return status -1?

    webpage_token = re.search(r"webpage_token=([a-f0-9]+)", r0.text).group(1)
    
    ## Bootstrap POST (for form_check_ajax)
    headers = {"X-Requested-With": "XMLHttpRequest"}
    payload = {
            "_dummy": "1",
            "_session_storage": '{"_global":{"destination_stack":["w/webpage/find-bin-collection-day-input-address"]}}',
            "_update_page_content_request": "1"
        }
    r1 = session.post(url_stem+input_url, data=payload, headers=headers)

    ## Extract CSRF from the XHR response
    CSRF = re.search(r"CSRF = \'([a-fA-F0-9]+)", r1.text).group(1)

    ## Extract form input fields
    soup = BeautifulSoup(r1.json()["data"], "html.parser")
    form_data = {}
    for inp in soup.find_all("input"):
        if inp.get("name"):  # only keep inputs with a name
            form_data[inp["name"]] = inp.get("value", "")

    div = soup.find("div", class_="fragment_presenter_template_edit")

    if div:
        raw_data_params = div.get("data-params")
        # Decode HTML entities (&quot; → ")
        decoded = html.unescape(raw_data_params)
        # Parse as JSON
        params = json.loads(decoded)
        # Extract levels
        levels = params.get("levels")
        # print("Levels token:", levels)

    ## Duplicate autocomplete request to return an integer ID that's mapped to the street address
    autocomplete_url = "/w/ajax"
    
    params = {
        "webpage_subpage_id": "PAG0000732GBNLM1",
        "webpage_token": webpage_token,
        "ajax_action": "html_get_type_ahead_results",
    }

    ajax_headers = {
        "Accept": "text/html, */*; q=0.01",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8,vi;q=0.7",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://waste.nc.north-herts.gov.uk",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    data = {
        "levels": levels,
        "search_string": street_address,
        "display_limit": "75",
        "presenter_settings[records_limit]": "75",
        "presenter_settings[load_more_records_label]": "Click here to load more addresses",
        "presenter_settings[min_characters]": "3",
        "presenter_settings[exact_match_first]": "0",
        "settings[message_offline_mode_unique_lookup]": "",
        "settings[wrapper]": "16",
        "settings[presenter]": "73",
        "settings[remember_last_value]": "0",
        "settings[label]": "Search for an address. For example, 123 Test Road, or SG6 3JF. Postcodes must contain a space.",
        "settings[hint]": "",
        "settings[required]": "1",
        "settings[omit_if_blank]": "0",
        "settings[title_field_path]": ":PRO0000228GBLLP1",
        "settings[lookup_field_path]": ":CMP0000243GBNLM1",
        "settings[lookup_comparator]": "17",
        "settings[order_field_path]": ":CMP0000211GBNLM1",
        "settings[order_direction]": "ASC",
        "settings[force_to_default_input_value]": "0",
        "settings[logged_in_user_visibility_relationship][OBJ0000063GBNLM9_inverse]": "0",
        "settings[limit_subset_field_path]": ":SUB0000445GBNLM1",
        "settings[allow_existing_invalid_value]": "0",
        "settings[show_value_history]": "0",
        "settings[presenter_settings][records_limit]": "75",
        "settings[presenter_settings][load_more_records_label]": "Click here to load more addresses",
        "settings[presenter_settings][min_characters]": "3",
        "settings[presenter_settings][exact_match_first]": "0",
        "settings[display_on_small_devices]": "true",
        "settings[display_on_medium_devices]": "true",
        "settings[display_on_large_devices]": "true",
        "settings[tiles_orientation]": "horizontal",
        "settings[message_offline_mode_callback]": "",
        "context_page_id": "PAG0000732GBNLM1",
        "form_check_ajax": CSRF,
    }

    r2 = session.post(url_stem+autocomplete_url, headers=ajax_headers, data=data, params=params)

    ## Extract street address ID
    street_address_integer_id = re.search(r"[0-9]+", r2.text).group(0)

    ## Update form fields with target address
    form_data[list(form_data.keys())[-2]] = street_address_integer_id

    ## Submit form with new payload
    form_attr = soup.find("form").attrs
    submission_url = form_attr["data-submit_destination"]

    r3 = session.post(url_stem+submission_url, data=form_data, headers=headers)

    redirect_url = r3.json()["redirect_url"]

    ## Follow redirect
    r4 = session.post(url_stem+redirect_url, headers=headers)

    ## Bootstrap POST
    payload = {
            "_dummy": "1",
            "_session_storage": '{"_global":{"destination_stack":["w/webpage/find-bin-collection-day-show-details"]}}',
            "_update_page_content_request": "1"
        }
    r5 = session.post(url_stem+redirect_url, data=payload, headers=headers)

    scraped_source = r5.json()["data"]
    return scraped_source

# Main execution
if __name__ == '__main__':
    with open("address.txt") as f:
        scrape_bin_date_website(f.readline())