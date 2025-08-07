from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
#nothing
class SeleniumScraper:
    # Initialize the web driver for Chrome
    def __init__(self):
        chrome_options = Options()
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Allow use of 'with' statement for clean resource management
    def __enter__(self):
        return self

    # Ensure the web driver is closed after use
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.quit()

    # Start the web scraping process
    def start_requests(self):
        # Open the target webpage
        with open("targetURL.txt") as target:
            url = target.read()
        self.driver.get(url)
        self.parse()

    # Helper method to find elements and extract data
    def find_element_by_css(self, css_selector, attribute="text", child_index=None):
        # Wait for the element to be present before finding it
        element = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
        # Extract text or attribute based on parameters
        if attribute == "text":
            return element.text.replace('\n', ' ').strip() if child_index is None else element.find_elements(By.CSS_SELECTOR, "*")[child_index].strip()
        return element.get_attribute(attribute)

    # Parse the webpage to extract data
    def parse(self):
        # Wait a bit for all elements to fully load
        time.sleep(2)
        
        # data = {
        #     'date': self.driver.find_element(By.CLASS_NAME, 'value-as-text')
        # }
        # print(data)

        source = self.driver.page_source
        print(source)

        # Extract and print data from the page
        # data = {
        #     'name': self.find_element_by_css('h1[data-qa="device-name"]', 'text'),
        #     'memory': self.find_element_by_css('span[class^="simtype_selectedMemory__"]', 'text'),
        #     'pay_monthly_price': self.find_element_by_css('p[class^="paymentOptions_subtotalContent__"] > span:nth-child(1)', 'text'),
        #     'pay_today_price': self.find_element_by_css('p[class^="paymentOptions_subtotalContent__"] > span:nth-child(2) > span', 'text') + "/mo",
        # }
        # print(data)

    # Close the web driver manually if needed
    def close_spider(self):
        self.driver.quit()

# Main execution
if __name__ == "__main__":
    # Use 'with' statement for automatic cleanup
    with SeleniumScraper() as scraper:
        scraper.start_requests()