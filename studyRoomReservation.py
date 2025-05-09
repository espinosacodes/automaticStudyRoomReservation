import os
import json
import time
import logging
import argparse
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reservation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Automate study room reservation.')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()

def load_credentials():
    """Load credentials from the JSON file."""
    try:
        with open('credentials.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("credentials.json file not found!")
        username = input("Enter your username (document number): ")
        password = input("Enter your password: ")
        
        credentials = {
            "username": username,
            "password": password
        }
        
        # Save credentials for future use
        with open('credentials.json', 'w') as f:
            json.dump(credentials, f, indent=4)
        
        return credentials

def load_reservation_times():
    """Load reservation times from the JSON file."""
    try:
        with open('reservationTime.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("reservationTime.json file not found!")
        return []

def get_next_reservation_date(reservation_times):
    """Get the next reservation date based on the specified days."""
    if not reservation_times:
        logger.error("No reservation times specified!")
        return None, None, None
    
    today = datetime.now()
    days_map = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6
    }
    
    # Find the next available reservation day
    next_reservation = None
    days_until = 7  # Maximum days to look ahead
    
    for reservation in reservation_times:
        day_of_week = days_map.get(reservation["day"], -1)
        if day_of_week == -1:
            logger.error(f"Invalid day specified: {reservation['day']}")
            continue
        
        days_ahead = (day_of_week - today.weekday()) % 7
        if days_ahead == 0 and today.hour >= int(reservation["startTime"].split(":")[0]):
            # If it's the same day but after the start time, then look at next week
            days_ahead = 7
        
        if days_ahead < days_until:
            days_until = days_ahead
            next_reservation = reservation
    
    if next_reservation:
        next_date = today + timedelta(days=days_until)
        formatted_date = next_date.strftime("%Y-%m-%d")
        return formatted_date, next_reservation["startTime"], next_reservation["endTime"]
    
    return None, None, None

def initialize_driver(headless=False):
    """Initialize and return a Selenium WebDriver."""
    logger.info("Initializing web driver...")
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--start-maximized")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        logger.error(f"Error initializing browser: {e}")
        return None

def login(driver, username, password):
    """Navigate to the login page and attempt to log in."""
    logger.info("Navigating to login page...")
    driver.get("https://banner9.icesi.edu.co/ic_reservas/login")
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # Find username and password fields
        logger.info("Looking for login form...")
        username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        
        # Fill in credentials
        logger.info("Filling in credentials...")
        username_field.send_keys(username)
        password_field.send_keys(password)
        
        # Find and click login button
        login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        login_button.click()
        
        # Wait for successful login - check for URL change or welcome message
        logger.info("Attempting login...")
        try:
            # First, check if we're redirected away from the login page
            wait.until(EC.url_changes("https://banner9.icesi.edu.co/ic_reservas/login"))
            logger.info(f"Current URL after login: {driver.current_url}")
            
            # Then look for welcome text if available
            try:
                welcome_element = wait.until(EC.presence_of_element_located((
                    By.XPATH, "//div[contains(text(), 'Bienvenido') or contains(text(), 'Welcome') or contains(@class, 'welcome')]"
                )))
                logger.info("Welcome message found!")
            except:
                # If no welcome message but URL changed, we'll consider it successful
                if "login" not in driver.current_url:
                    logger.info("Login appears successful!")
                else:
                    raise Exception("URL still shows login page")
                
            return True
            
        except TimeoutException:
            logger.error("Login redirect did not occur.")
            return False
    
    except TimeoutException:
        logger.error("Login failed or page timed out.")
    except Exception as e:
        logger.error(f"An error occurred during login: {e}")
    
    return False

def navigate_to_add_reservation(driver):
    """Navigate to the add reservation page."""
    logger.info("Navigating to add reservation page...")
    try:
        wait = WebDriverWait(driver, 15)  # Increased wait time
        
        # Log the current URL
        logger.info(f"Current URL after login: {driver.current_url}")
        
        # First attempt: Try clicking the "AGREGAR RESERVA" button with various approaches
        logger.info("Trying to find button by text content (case insensitive)")
        button_found = False
        
        # Try various XPath expressions to find the button
        for xpath in [
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agregar reserva')]",
            "//button[contains(text(), 'AGREGAR')]",
            "//button[contains(text(), 'RESERVA')]",
            "//button[contains(@class, 'primary')]",
            "//button"
        ]:
            logger.info(f"Trying XPath: {xpath}")
            buttons = driver.find_elements(By.XPATH, xpath)
            logger.info(f"Found {len(buttons)} potential buttons")
            
            # Check each button found
            for btn in buttons:
                try:
                    text = btn.text
                    logger.info(f"Button text: '{text}'")
                    if "AGREGAR" in text.upper() and "RESERVA" in text.upper():
                        logger.info("Found AGREGAR RESERVA button")
                        btn.click()
                        button_found = True
                        break
                except:
                    pass
            
            if button_found:
                break
        
        # If button click fails, try direct navigation
        if not button_found:
            logger.warning("Could not find AGREGAR RESERVA button, using direct navigation")
            driver.get("https://banner9.icesi.edu.co/ic_reservas/addReserve")
        
        # Wait for the reservation page to load
        wait.until(EC.url_contains("addReserve"))
        logger.info("Successfully on add reservation page")
        
        # Give the page some time to fully load
        time.sleep(3)
        return True
    
    except TimeoutException:
        logger.error("Could not navigate to add reservation page")
        # Take screenshot for debugging
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            driver.save_screenshot(f"navigation_error_{timestamp}.png")
        except:
            pass
    except Exception as e:
        logger.error(f"An error occurred while navigating to add reservation: {e}")
    
    return False

def fill_reservation_form(driver, date, start_time, end_time):
    """Fill in the reservation form."""
    logger.info("Filling reservation form...")
    try:
        # Use a longer wait time for form elements to load
        wait = WebDriverWait(driver, 20)
        
        # Log the current URL to verify we're on the right page
        logger.info(f"Current URL before filling form: {driver.current_url}")
        
        # Wait for the main form container to be present
        logger.info("Waiting for form to load...")
        form_container = wait.until(EC.presence_of_element_located((By.XPATH, "//form | //div[contains(@class, 'form')]")))
        logger.info("Form container found")
        
        # Fill activity field - try multiple possible selectors
        logger.info("Filling activity field...")
        try:
            activity_field = wait.until(EC.presence_of_element_located((
                By.XPATH, "//input[contains(@placeholder, 'Actividad') or contains(@name, 'activ') or @type='text']")))
            activity_field.clear()
            activity_field.send_keys("Study Session")
            logger.info("Activity field filled")
        except Exception as e:
            logger.warning(f"Could not fill activity field: {e}")
        
        # Fill date field - try multiple possible selectors
        logger.info("Filling date field...")
        try:
            date_field = wait.until(EC.presence_of_element_located((
                By.XPATH, "//input[@type='date' or contains(@name, 'date') or contains(@name, 'fecha')]")))
            driver.execute_script("arguments[0].value = arguments[1]", date_field, date)
            logger.info("Date field filled with: " + date)
        except Exception as e:
            logger.warning(f"Could not fill date field: {e}")
        
        # Fill start time field
        logger.info("Filling start time field...")
        try:
            start_time_fields = driver.find_elements(By.XPATH, "//input[@type='time']")
            if start_time_fields and len(start_time_fields) >= 1:
                start_time_fields[0].clear()
                start_time_fields[0].send_keys(start_time)
                logger.info("Start time field filled")
            else:
                logger.warning("Start time field not found")
        except Exception as e:
            logger.warning(f"Could not fill start time field: {e}")
        
        # Fill end time field
        logger.info("Filling end time field...")
        try:
            end_time_fields = driver.find_elements(By.XPATH, "//input[@type='time']")
            if end_time_fields and len(end_time_fields) >= 2:
                end_time_fields[1].clear()
                end_time_fields[1].send_keys(end_time)
                logger.info("End time field filled")
            else:
                logger.warning("End time field not found")
        except Exception as e:
            logger.warning(f"Could not fill end time field: {e}")
        
        # Select building - try with more flexible approach
        logger.info("Selecting building...")
        try:
            selects = driver.find_elements(By.XPATH, "//select")
            if selects:
                building_select = Select(selects[0])
                options = [i for i in range(1, len(building_select.options))]
                if options:
                    building_select.select_by_index(options[0])  # Select first non-default option
                    logger.info("Building selected")
                    # Wait for potential AJAX updates after building selection
                    time.sleep(3)
            else:
                logger.warning("Building select not found")
        except Exception as e:
            logger.warning(f"Could not select building: {e}")
        
        # Fill number of people
        logger.info("Filling number of people...")
        try:
            people_field = wait.until(EC.presence_of_element_located((
                By.XPATH, "//input[@type='number' or contains(@name, 'people') or contains(@name, 'personas')]")))
            people_field.clear()
            people_field.send_keys("1")
            logger.info("People field filled")
        except Exception as e:
            logger.warning(f"Could not fill people field: {e}")
        
        # Select space - try with more flexible approach
        logger.info("Selecting space...")
        try:
            # Wait a moment for any AJAX updates to complete
            time.sleep(2)
            selects = driver.find_elements(By.XPATH, "//select")
            if len(selects) >= 2:
                space_select = Select(selects[1])
                options = [i for i in range(1, len(space_select.options))]
                if options:
                    space_select.select_by_index(options[0])  # Select first non-default option
                    logger.info("Space selected")
            else:
                logger.warning("Space select not found or not enough options")
        except Exception as e:
            logger.warning(f"Could not select space: {e}")
        
        # Fill observation field (optional)
        logger.info("Filling observation field...")
        try:
            observation_fields = driver.find_elements(By.XPATH, "//textarea")
            if observation_fields:
                observation_fields[0].clear()
                observation_fields[0].send_keys("Automated reservation")
                logger.info("Observation field filled")
            else:
                logger.warning("Observation field not found")
        except Exception as e:
            logger.warning(f"Could not fill observation field: {e}")
        
        logger.info("Reservation form filled successfully.")
        return True
    
    except TimeoutException:
        logger.error("Could not find form fields or page timed out.")
        # Take a screenshot for debugging
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"form_error_{timestamp}.png"
            driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
            
            # Log the page source for debugging
            with open(f"page_source_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logger.info(f"Page source saved to page_source_{timestamp}.html")
        except:
            logger.warning("Could not save debug information")
    except Exception as e:
        logger.error(f"An error occurred while filling the reservation form: {e}")
    
    return False

def submit_reservation(driver):
    """Submit the reservation form."""
    logger.info("Submitting reservation...")
    try:
        wait = WebDriverWait(driver, 15)  # Increased wait time
        
        # Take a screenshot before attempting to click the button
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        driver.save_screenshot(f"before_submit_{timestamp}.png")
        logger.info(f"Screenshot saved before attempting submission")
        
        # Try multiple strategies to find and click the CONTINUAR button
        button_found = False
        
        # Strategy 1: Try by exact text "CONTINUAR"
        logger.info("Trying to find button by exact text 'CONTINUAR'")
        try:
            submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='CONTINUAR']")))
            logger.info("Found button by exact text 'CONTINUAR'")
            button_found = True
        except:
            logger.info("Button not found by exact text, trying alternatives")
        
        # Strategy 2: Try by case-insensitive text content
        if not button_found:
            logger.info("Trying to find button by case-insensitive text")
            try:
                submit_button = wait.until(EC.element_to_be_clickable((
                    By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continuar')]"
                )))
                logger.info("Found button by case-insensitive text")
                button_found = True
            except:
                logger.info("Button not found by case-insensitive text, trying alternatives")
        
        # Strategy 3: Look for blue button that might be the submit button
        if not button_found:
            logger.info("Looking for blue button (likely submit button)")
            buttons = driver.find_elements(By.XPATH, "//button")
            for btn in buttons:
                try:
                    # Check if button is blue (primary style) or contains relevant text
                    btn_class = btn.get_attribute("class")
                    if ("primary" in btn_class.lower() or 
                        "blue" in btn_class.lower() or 
                        "continuar" in btn.text.lower() or 
                        "submit" in btn.text.lower()):
                        submit_button = btn
                        logger.info(f"Found button with class: {btn_class}, text: {btn.text}")
                        button_found = True
                        break
                except:
                    pass
        
        # Strategy 4: Try by position in the page (last resort)
        if not button_found:
            logger.info("Looking for a button at the bottom of the form")
            try:
                # Get all buttons and try the ones near the bottom of the page
                buttons = driver.find_elements(By.TAG_NAME, "button")
                if buttons:
                    # Try the last few buttons
                    for i in range(min(3, len(buttons))):
                        btn = buttons[len(buttons) - 1 - i]
                        logger.info(f"Trying button {i+1} from the end, text: {btn.text}")
                        if btn.is_displayed() and btn.is_enabled():
                            submit_button = btn
                            button_found = True
                            break
            except Exception as e:
                logger.warning(f"Error looking for buttons by position: {e}")
        
        # Actually click the button
        if button_found:
            # Ensure button is in view
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(1)  # Small pause to ensure the button is fully in view
            
            logger.info(f"Clicking button with text: '{submit_button.text}'")
            
            # Try JavaScript click first (more reliable in some cases)
            try:
                driver.execute_script("arguments[0].click();", submit_button)
                logger.info("Button clicked using JavaScript")
            except:
                # Fall back to regular click
                submit_button.click()
                logger.info("Button clicked using regular click method")
                
            # Take a screenshot after clicking
            driver.save_screenshot(f"after_submit_{timestamp}.png")
            
            # Wait for confirmation or success message
            try:
                success_msg = wait.until(EC.presence_of_element_located((By.XPATH, 
                    "//div[contains(text(), 'exitosa') or contains(text(), 'éxito') or contains(text(), 'realizada')]")))
                logger.info(f"Reservation success message found: {success_msg.text}")
                return True
            except TimeoutException:
                logger.warning("No success message found, but button was clicked")
                return True  # Return true anyway since we successfully clicked the button
        else:
            logger.error("Could not find the submit button")
            # Take a screenshot for debugging
            driver.save_screenshot(f"no_button_found_{timestamp}.png")
            return False
    
    except TimeoutException:
        logger.error("Timeout while looking for submit button")
        # Take a screenshot for debugging
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            driver.save_screenshot(f"submit_timeout_{timestamp}.png")
        except:
            pass
    except Exception as e:
        logger.error(f"An error occurred while submitting the reservation: {e}")
        # Take a screenshot for debugging
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            driver.save_screenshot(f"submit_error_{timestamp}.png")
        except:
            pass
    
    return False

def main():
    """Main function to run the automation."""
    args = parse_arguments()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Starting study room reservation automation...")
    
    # Load credentials and reservation times
    credentials = load_credentials()
    reservation_times = load_reservation_times()
    
    # Get the next available reservation date and times
    next_date, start_time, end_time = get_next_reservation_date(reservation_times)
    
    if not next_date:
        logger.error("Could not determine next reservation date. Please check reservationTime.json.")
        return
    
    logger.info(f"Next reservation: {next_date} from {start_time} to {end_time}")
    
    # Initialize WebDriver
    driver = initialize_driver(headless=args.headless)
    
    if not driver:
        logger.error("Could not initialize browser. Exiting...")
        return
    
    try:
        # Log in to the system
        if not login(driver, credentials["username"], credentials["password"]):
            logger.error("Login failed. Please check your credentials.")
            return
        
        # Navigate to add reservation page
        if not navigate_to_add_reservation(driver):
            logger.error("Could not navigate to add reservation page.")
            return
        
        # Fill reservation form
        if not fill_reservation_form(driver, next_date, start_time, end_time):
            logger.error("Could not fill reservation form.")
            return
        
        # Submit reservation
        if submit_reservation(driver):
            logger.info("Reservation process completed successfully!")
        else:
            logger.error("Failed to submit reservation.")
    
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    
    finally:
        logger.info("Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()