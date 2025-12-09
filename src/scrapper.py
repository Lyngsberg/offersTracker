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
NETTO_PAGE_URL = 'https://netto.dk/netto-avisen/' 
BASE_DATA_FOLDER = 'data/' 
MAX_PAGES_TO_SCROLL = 50 

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

def handle_cookie_banner(driver):
    try:
        driver.execute_script("""
            var overlay = document.getElementById('coiOverlay');
            if (overlay) { overlay.remove(); }
        """)
        time.sleep(0.5)
    except Exception:
        pass

def get_folder_name_from_text(raw_text):
    """Parses date text like '6. - 12. december' into a folder name."""
    try:
        clean_text = raw_text.replace('.', '').strip()
        clean_text = re.sub(r'\s*-\s*', '-', clean_text)
        clean_text = re.sub(r'\s+', '_', clean_text)
        current_year = datetime.datetime.now().year
        folder_name = f"{clean_text}_{current_year}"
        folder_name = re.sub(r'[<>:"/\\|?*]', '', folder_name)
        return folder_name
    except Exception as e:
        print(f"Error parsing date: {e}. Using fallback.")
        return f"offer_week_{int(time.time())}"

def download_image(image_url: str, save_path: str, filename: str):
    try:
        if not image_url or not image_url.startswith('http'): return
        file_ext = '.webp' if '.webp' in image_url else '.jpg'
        full_path = os.path.join(save_path, f"{filename}{file_ext}")
        if os.path.exists(full_path): return

        response = requests.get(image_url, stream=True, timeout=15)
        response.raise_for_status()

        with open(full_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"   -> Downloaded: {filename}{file_ext}")
    except Exception as e:
        print(f"   -> ERROR downloading {image_url}: {e}")

def get_all_image_urls(driver):
    """Returns a set of all flyer image URLs currently in the DOM."""
    elements = driver.find_elements(By.CSS_SELECTOR, FLYER_IMAGE_SELECTOR)
    urls = set()
    for el in elements:
        try:
            src = el.get_attribute('src')
            if src and "tjek.com" in src:
                urls.add(src)
        except StaleElementReferenceException:
            continue
    return urls

def scrape_netto_flyer():
    driver = setup_driver()
    
    try:
        driver.get(NETTO_PAGE_URL)
        wait = WebDriverWait(driver, 15)
        handle_cookie_banner(driver)

        # 1. Find Initial Link
        print("Waiting for initial flyer to load...")
        initial_btn = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, INITIAL_LINK_SELECTOR))
        )
        
        # --- NEW: Extract Date Text & Create Folder ---
        try:
            date_element = initial_btn.find_element(By.CSS_SELECTOR, DATE_TEXT_SELECTOR)
            raw_date_text = date_element.text
            print(f"Found date text: '{raw_date_text}'")
            subfolder_name = get_folder_name_from_text(raw_date_text)
        except Exception as e:
            print(f"Could not find date text ({e}). Using default name.")
            subfolder_name = "unknown_date"

        current_save_folder = os.path.join(BASE_DATA_FOLDER, subfolder_name)
        os.makedirs(current_save_folder, exist_ok=True)
        print(f"Saving images to: '{current_save_folder}'")
        # ----------------------------------------------

        # 2. Click to Open Viewer
        driver.execute_script("arguments[0].click();", initial_btn)
        
        print("Waiting for viewer to open...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, FLYER_IMAGE_SELECTOR)))
        
        seen_urls = set()
        
        # 3. Loop through pages
        page_number = 1
        while page_number <= MAX_PAGES_TO_SCROLL:
            print(f"--- Processing Page {page_number} ---")
            
            # A. Find the NEW URL
            new_url_found = None
            retries = 10 
            
            while retries > 0:
                current_urls = get_all_image_urls(driver)
                diff = current_urls - seen_urls
                
                if diff:
                    new_url_found = diff.pop()
                    break
                
                if page_number == 1 and current_urls:
                    new_url_found = list(current_urls)[0]
                    break
                    
                time.sleep(0.5)
                retries -= 1
            
            if new_url_found:
                download_image(new_url_found, current_save_folder, f"flyer_page_{page_number}")
                seen_urls.add(new_url_found)
            else:
                print("   Warning: No new image appeared. (End of flyer?)")
                if page_number > 1: break

            # B. Click Next Button
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, NEXT_BUTTON_SELECTOR)
                
                if not next_btn.is_enabled():
                    print("Next button disabled.")
                    break
                
                driver.execute_script("arguments[0].click();", next_btn)
                page_number += 1
                time.sleep(1.0)
                
            except (NoSuchElementException, StaleElementReferenceException):
                print("Next button not found. Assuming end of flyer.")
                break
            except Exception as e:
                print(f"Error clicking next: {e}")
                break

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Closing WebDriver...")
        driver.quit()
        print("--- Scraper Finished ---")

if __name__ == '__main__':
    scrape_netto_flyer()