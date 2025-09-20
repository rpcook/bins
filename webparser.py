import re
from datetime import datetime
from bs4 import BeautifulSoup

def parse_bin_table_to_dict(html):
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    # Iterate all tables (works if there's only one table too)
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        i = 0
        while i < len(rows):
            row1 = rows[i]
            # Prefer the second <td> in the first row for the bin label
            tds1 = row1.find_all("td")
            bin_label = None
            if len(tds1) >= 2:
                bin_label = tds1[1].get_text(" ", strip=True)
            else:
                # fallback: any strong/span in the row
                bin_label = row1.get_text(" ", strip=True)

            # next row usually contains the "Next collection" / date info
            date = None
            if i + 1 < len(rows):
                row2 = rows[i + 1]
                text = row2.get_text(" ", strip=True)
                # Try to capture the text after "Next collection" until "Collection cycle" or end
                m = re.search(r'Next\s+collection[:\s]*([\s\S]*?)(?:Collection\s+cycle|$)', text, flags=re.I)
                if m:
                    date = m.group(1).strip()
                    # Clean duplicated whitespace/newline bits
                    date = re.sub(r'\s+', ' ', date)
                else:
                    # fallback: try to find a weekday + year pattern e.g. "Tuesday 23rd September 2025"
                    m2 = re.search(r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b[^\d\n]*\d{1,2}.*?\d{4}', text, flags=re.I)
                    if m2:
                        date = m2.group(0).strip()

            # Normalise the label to a colour if possible (e.g. "Purple lid bin" -> "purple")
            key = None
            if bin_label:
                mcol = re.search(r'([A-Za-z]+)\s+lid', bin_label, flags=re.I)
                if mcol:
                    key = mcol.group(1).strip().lower()
                else:
                    # fallback to the whole label (strip/normalise whitespace)
                    key = re.sub(r'\s+', ' ', bin_label).strip()

            if key and date:
                result[key] = date

            # Advance: if we used a pair, skip two rows; otherwise move one row forward
            i += 2 if (i + 1 < len(rows)) else 1

    # slice dictionary to remove duplicates
    result = dict(list(result.items())[:5])
    return result

def parse_dates(bin_dictionary):
    # process date strings into integer days from dd/mm/yyyy
    # return as dictionary of bin colours and date integers
    bin_dates = {}
    for bin in bin_dictionary:
        # print(bin_dictionary[bin])
        bin_date = int(datetime.strptime(re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', bin_dictionary[bin]), "%A %d %B %Y").timestamp()/86400)
        bin_dates[bin] = bin_date
    return bin_dates

# Main execution
if __name__ == '__main__':
    with open('scraped_source.htm') as f:
        source = f.read()
    source_info = parse_bin_table_to_dict(source)
    # print(source_info)
    processed_dates = parse_dates(source_info)
    print(processed_dates)