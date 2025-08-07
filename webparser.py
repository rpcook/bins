import re
import datetime

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
    # process date strings into integer days from XXXX
    # return as dictionary of bin colours and date integers
    pass

# Main execution
if __name__ == '__main__':
    with open('scraped_source.htm') as f:
        source = f.read()
    source_info = find_info(source)
    
    print(source_info[0][0])
