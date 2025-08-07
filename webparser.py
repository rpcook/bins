import re

def find_info(text):
    # find headings
    pattern = '<div class="formatting_bold formatting_size_bigger formatting">.*?<span[^>]*>(.*?)</span>.*?</div>'
    headings = re.findall(pattern, text)
    # find dates etc
    pattern = 'data-current_value="([^"]*)"'
    date_strings = re.findall(pattern, text)
    return headings, date_strings

# Main execution
if __name__ == "__main__":
    with open('scraped_source.htm') as f:
        source = f.read()
    print(find_info(source))
