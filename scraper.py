import re
# from datetime import datetime

import requests
# from bs4 import BeautifulSoup

def scrape_bin_date_website(street_address=None):
    session = requests.Session()

    # Get page (for cookie + webpage_token)
    url = "https://waste.nc.north-herts.gov.uk/w/webpage/find-bin-collection-day-input-address"
    r0 = session.get(url)
    webpage_token = re.search(r"webpage_token=([a-f0-9]+)", r0.text).group(1)

    # print("webpage_token:", webpage_token)
    
    # Bootstrap POST (for form_check_ajax)
    headers = {"X-Requested-With": "XMLHttpRequest"}
    payload = {
            "_dummy": "1",
            "_session_storage": '{"_global":{"destination_stack":["w/webpage/find-bin-collection-day-input-address"]}}',
            "_update_page_content_request": "1"
        }
    r1 = session.post(url, data=payload, headers=headers)

    dumpSource("r1.html", r1.json()["data"])
    # Extract CSRF from the XHR response
    CSRF = re.search(r"CSRF = \'([a-fA-F0-9]+)", r1.text).group(1)
    # print("CSRF:", CSRF)

    # Request address input form
    # headers = {
    #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    #     "Accept": "application/json, text/javascript, */*; q=0.01",
    #     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    #     "X-Requested-With": "XMLHttpRequest",
    #     "Origin": "https://waste.nc.north-herts.gov.uk",
    #     "Referer": "https://waste.nc.north-herts.gov.uk/w/webpage/find-bin-collection-day-input-address",
    # }
    # payload = {
    #     "_dummy": "1",
    #     "_session_storage": '{"_global":{"destination_stack":["w/webpage/find-bin-collection-day-show-details?webpage_token=' + webpage_token + '","w/webpage/find-bin-collection-day-input-address"]}}',
    #     "_update_page_content_request": "1",
    #     "form_check_ajax": CSRF,
    # }

    # r2 = session.post(url, data=payload, headers=headers)
    # form_source = r2.json()["data"]

    # extract form input fields
    # populate with street_address
    # submit as form (POST?)

def dumpSource(fname, source):
    with open(fname, "w", encoding="UTF-8") as f:
        f.write(source)

def hex_with_context(text, min_len=16, max_len=70, context=50):
    patt = rf'\b[a-fA-F0-9]{{{min_len},{max_len}}}\b'
    for m in re.finditer(patt, text):
        s, e = m.span()
        snippet = text[max(0, s-context): min(len(text), e+context)]
        yield (m.group(0), snippet)

# Main execution
if __name__ == '__main__':
    with open("address.txt") as f:
        scrape_bin_date_website(f.readline())