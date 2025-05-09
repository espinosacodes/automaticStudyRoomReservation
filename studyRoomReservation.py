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
        
        # Wait for successful login - check for "Bienvenido" text
        logger.info("Attempting login...")
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Bienvenido')]")))
        logger.info("Login successful!")
        return True
    
    except TimeoutException:
        logger.error("Login failed or page timed out.")
    except Exception as e:
        logger.error(f"An error occurred during login: {e}")
    
    return False

def navigate_to_add_reservation(driver):
    """Navigate to the add reservation page."""
    logger.info("Navigating to add reservation page...")
    try:
        wait = WebDriverWait(driver, 10)
        
        # Find and click "AGREGAR RESERVA" button
        add_reservation_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'AGREGAR') and contains(text(), 'RESERVA')]")))
        add_reservation_button.click()
        
        # Wait for the reservation page to load
        wait.until(EC.url_to_be("https://banner9.icesi.edu.co/ic_reservas/addReserve"))
        logger.info("Successfully navigated to add reservation page.")
        return True
    
    except TimeoutException:
        logger.error("Could not find 'AGREGAR RESERVA' button or page timed out.")
    except Exception as e:
        logger.error(f"An error occurred while navigating to add reservation: {e}")
    
    return False

def fill_reservation_form(driver, date, start_time, end_time):
    """Fill in the reservation form."""
    logger.info("Filling reservation form...")
    try:
        wait = WebDriverWait(driver, 10)
        
        # Fill activity field
        activity_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Actividad')]")))
        activity_field.send_keys("Study Session")
        
        # Fill date field
        date_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='date']")))
        date_field.send_keys(date)
        
        # Fill start time field
        start_time_field = wait.until(EC.presence_of_element_located((By.XPATH, "(//input[@type='time'])[1]")))
        start_time_field.send_keys(start_time)
        
        # Fill end time field
        end_time_field = wait.until(EC.presence_of_element_located((By.XPATH, "(//input[@type='time'])[2]")))
        end_time_field.send_keys(end_time)
        
        # Select building
        building_select = Select(wait.until(EC.presence_of_element_located((By.XPATH, "//select[contains(@name, 'edificio')]"))))
        building_select.select_by_index(1)  # Select the first available building
        
        # Wait for the spaces to load
        time.sleep(2)
        
        # Fill number of people
        people_field = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='number']")))
        people_field.send_keys("1")  # Just one person
        
        # Select space
        space_select = Select(wait.until(EC.presence_of_element_located((By.XPATH, "//select[contains(@name, 'espacio')]"))))
        space_select.select_by_index(1)  # Select the first available space
        
        # Fill observation field (optional)
        observation_field = driver.find_element(By.XPATH, "//textarea")
        observation_field.send_keys("Automated reservation")
        
        logger.info("Reservation form filled successfully.")
        return True
    
    except TimeoutException:
        logger.error("Could not find form fields or page timed out.")
    except Exception as e:
        logger.error(f"An error occurred while filling the reservation form: {e}")
    
    return False

def submit_reservation(driver):
    """Submit the reservation form."""
    logger.info("Submitting reservation...")
    try:
        wait = WebDriverWait(driver, 10)
        
        # Find and click the submit button
        submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continuar')]")))
        submit_button.click()
        
        # Wait for confirmation or success message
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'exitosa') or contains(text(), 'éxito')]")))
        logger.info("Reservation submitted successfully!")
        return True
    
    except TimeoutException:
        logger.error("Could not find submit button or reservation failed.")
    except Exception as e:
        logger.error(f"An error occurred while submitting the reservation: {e}")
    
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