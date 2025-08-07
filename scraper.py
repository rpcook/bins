from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

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
        with open('targetURL.txt') as target:
            url = target.read()
        self.driver.get(url)
        #self.parse()

    def write_source_file(self):
        with open('scraped_source.htm', 'w') as f:
            f.write(self.source())

    def source(self):
        return self.driver.page_source

    # Close the web driver manually if needed
    def close_spider(self):
        self.driver.quit()

# Main execution
if __name__ == '__main__':
    # Use 'with' statement for automatic cleanup
    with SeleniumScraper() as scraper:
        scraper.start_requests()
        time.sleep(2) # wait for page to load
        scraper.write_source_file()