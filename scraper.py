import re
# from datetime import datetime

import requests
from bs4 import BeautifulSoup

def scrape_bin_date_website(street_address=None):
    session = requests.Session()

    # Get page (for cookie + webpage_token)
    url_stem = "https://waste.nc.north-herts.gov.uk"
    input_url = "/w/webpage/find-bin-collection-day-input-address"
    r0 = session.get(url_stem+input_url)
    # webpage_token = re.search(r"webpage_token=([a-f0-9]+)", r0.text).group(1)
    
    # Bootstrap POST (for form_check_ajax)
    headers = {"X-Requested-With": "XMLHttpRequest"}
    payload = {
            "_dummy": "1",
            "_session_storage": '{"_global":{"destination_stack":["w/webpage/find-bin-collection-day-input-address"]}}',
            "_update_page_content_request": "1"
        }
    r1 = session.post(url_stem+input_url, data=payload, headers=headers)

    # Extract CSRF from the XHR response
    # CSRF = re.search(r"CSRF = \'([a-fA-F0-9]+)", r1.text).group(1)

    # extract form input fields
    soup = BeautifulSoup(r1.json()["data"], "html.parser")
    form_data = {}
    for inp in soup.find_all("input"):
        if inp.get("name"):  # only keep inputs with a name
            form_data[inp["name"]] = inp.get("value", "")

    # update fields with target address
    # TODO: duplicate the address look-up autocomplete field (street_address is currently an integer ID field)
    form_data[list(form_data.keys())[-2]] = street_address

    # submit form with new payload
    form_attr = soup.find("form").attrs
    submission_url = form_attr["data-submit_destination"]

    r2 = session.post(url_stem+submission_url, data=form_data, headers=headers)

    redirect_url = r2.json()["redirect_url"]

    # follow redirect
    r3 = session.post(url_stem+redirect_url, headers=headers)

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