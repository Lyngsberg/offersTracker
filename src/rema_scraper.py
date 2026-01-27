import os
import time
import requests
import re
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.service import Service

# --- Configuration ---
REMA_PAGE_URL = 'https://rema1000.dk/avis' 
BASE_DATA_FOLDER = 'data/' 
LOG_FILE_PATH = 'log/rema_log.txt'
MAX_PAGES_TO_SCROLL = 60 

# --- Debugging paths ---
SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_PATH, '..'))
DEBUG_FOLDER = os.path.join(PROJECT_ROOT, 'debug')
SCREENSHOT_PATH = os.path.join(DEBUG_FOLDER, "Debugging.png")

# --- Selectors ---
INITIAL_LINK_SELECTOR = 'li.relative.snap-start > button' 
NEXT_BUTTON_SELECTOR = 'button[data-direction="next"]' 
FLYER_IMAGE_SELECTOR = 'img[src*="tjek.com"]' 
DATE_TEXT_SELECTOR = 'span.text-paragraph-sm-bold'

def setup_driver():
    print("Setting up Chrome WebDriver...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--window-size=1920,1080')

    if os.path.exists("/usr/bin/chromium-browser"):
        options.binary_location = "/usr/bin/chromium-browser"
    elif os.path.exists("/usr/bin/chromium"):
        options.binary_location = "/usr/bin/chromium"

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def write_log_line(status, message):
    """
    Writes a single line to the log file.
    """
    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(LOG_FILE_PATH)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] [{status}] {message}\n")
            
    except Exception as e:
        print(f"CRITICAL: Could not write to log file: {e}")

def handle_cookie_banner(driver):
    try:
        driver.execute_script("""
            var overlay = document.getElementById('coiOverlay');
            if (overlay) { overlay.remove(); }
        """)
        time.sleep(0.5)
    except:
        write_log_line("Error", "Was not able to handle cookies properly")

def saving_offer(offer: list, date: str):
    data_file = f'{BASE_DATA_FOLDER}raw/rema/{date}_raw.txt'
    with open(data_file, "a", encoding="utf-8") as f:
            f.write(f"{offer}\n")

def scrape_rema_flyer() -> list:
    driver = setup_driver()
    
    try:
        driver.get(REMA_PAGE_URL)
        wait = WebDriverWait(driver, 15)
        handle_cookie_banner(driver)
        driver.save_screenshot(SCREENSHOT_PATH)
        print("Working on pages")

        flyer_elements = wait.until(EC.presence_of_all_elements_located(
        (By.CSS_SELECTOR, "a.group\\/publication") 
        ))
        # 2. Since you know you want the FIRST one, just grab index 0
        first_flyer = flyer_elements[0]

        # 3. Find the image inside that specific flyer
        img_element = first_flyer.find_element(By.TAG_NAME, "img")
        alt_text = img_element.get_attribute("alt")

        print(f"First Flyer Found: {alt_text}")

        # 4. Check if it matches your "Uge" requirement
        if alt_text and "Uge" in alt_text:
            print(f"✅ FOUND MATCH: {alt_text}")
            # Add your click/download logic here
        else:
            print(f"❌ First flyer was '{alt_text}', not 'Uge'")

        date_element_obj = first_flyer.find_element(By.TAG_NAME, "h4")
        date_text = date_element_obj.text 
        formatted_date = date_text.replace(".", "_").replace(" - ", "_")
        print(f"Raw Date Text: {formatted_date}")

        # Getting the flyver link
        flyer_link = first_flyer.get_attribute('href')
        print(flyer_link)
    except:
        write_log_line("Error", "Driver could not find initial flyer")
    
    # Going to the first page of the flyer
    # Loop until there are no pages left or max page limit is hit
    
    # State tracking variables
    images_downloaded_count = 0
    fatal_error_message = None
    page_number = 1
    seen_pages = []
    while page_number < MAX_PAGES_TO_SCROLL:
        print(f"--- Processing Page {page_number} ---")
        try:
            driver.get(f"{flyer_link}/{page_number}")
            wait = WebDriverWait(driver, 15)
            handle_cookie_banner(driver)
        except:
            print("Failed")
            pass

        # Stopping if page has already been seen
        current_page = driver.current_url.rstrip('/')
        if current_page in seen_pages:
            break

        # Getting the buttons for each item on the page
        buttons = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, '[data-type="offer"]') 
        ))
        
        # Extracting the offers from each button for this page
        for button in buttons:
            offer = button.get_attribute('aria-label')
            saving_offer(offer, formatted_date)

        # The pages increment by 2 but starts at 1 and then goes 2 and then 4 and so on
        if page_number == 1:
            page_number += 1
        else:
            page_number += 2

        # When the page number is larger than number of pages it goes back to page 1.
        seen_pages.append(current_page)
    
if __name__ == "__main__":
    scrape_rema_flyer()
        