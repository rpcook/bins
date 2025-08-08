import re
from datetime import datetime

def find_info(text):
    # find headings
    pattern = '<div class="formatting_bold formatting_size_bigger formatting">.*?<span[^>]*>(.*?)</span>.*?</div>'
    headings = re.findall(pattern, text)
    # find dates etc
    pattern = 'data-current_value="([^"]*)"'
    date_strings = re.findall(pattern, text)
    return headings, date_strings

def validate_info(info):
    # validate that the returned information is the right size / shape
    # check for correct address
    return True

def process_info(info):
    # process date strings into integer days from dd/mm/yyyy
    # return as dictionary of bin colours and date integers
    bin_collections = {
        info[0][1]: int(datetime.strptime(info[1][1],'%d/%m/%Y').timestamp()/86400),
        info[0][3]: int(datetime.strptime(info[1][4],'%d/%m/%Y').timestamp()/86400),
        info[0][5]: int(datetime.strptime(info[1][7],'%d/%m/%Y').timestamp()/86400),
        info[0][7]: int(datetime.strptime(info[1][10],'%d/%m/%Y').timestamp()/86400),
        info[0][9]: int(datetime.strptime(info[1][13],'%d/%m/%Y').timestamp()/86400)
    }
    return bin_collections

# Main execution
if __name__ == '__main__':
    with open('scraped_source.htm') as f:
        source = f.read()
    source_info = find_info(source)
    if not validate_info(source_info):
        print('Scraped data not valid, quitting')
        quit()
    print(process_info(source_info))
    # print(source_info)
