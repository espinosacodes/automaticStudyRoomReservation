import os
import json
import getpass
import time
from cryptography.fernet import Fernet
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

def get_or_create_key(key_file="encryption_key.key"):
    """Get or create an encryption key for securing credentials."""
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
    return key

def encrypt_data(data, key):
    """Encrypt data using Fernet."""
    cipher_suite = Fernet(key)
    encrypted_data = cipher_suite.encrypt(data.encode())
    return encrypted_data

def decrypt_data(encrypted_data, key):
    """Decrypt data using Fernet."""
    cipher_suite = Fernet(key)
    decrypted_data = cipher_suite.decrypt(encrypted_data).decode()
    return decrypted_data

def get_credentials():
    """Get user credentials and store them securely."""
    credentials_file = "credentials.enc"
    key_file = "encryption_key.key"
    
    # If credentials already exist, ask if user wants to use them
    if os.path.exists(credentials_file) and os.path.exists(key_file):
        use_existing = input("Stored credentials found. Use them? (y/n): ").lower()
        if use_existing == 'y':
            # Load and decrypt existing credentials
            key = get_or_create_key(key_file)
            with open(credentials_file, "rb") as f:
                encrypted_data = f.read()
            credentials_str = decrypt_data(encrypted_data, key)
            credentials = json.loads(credentials_str)
            return credentials
    
    # Get new credentials
    print("Please enter your login credentials:")
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    
    # Store credentials
    credentials = {"username": username, "password": password}
    credentials_str = json.dumps(credentials)
    
    # Encrypt and save
    key = get_or_create_key(key_file)
    encrypted_data = encrypt_data(credentials_str, key)
    with open(credentials_file, "wb") as f:
        f.write(encrypted_data)
    
    print("Credentials saved securely.")
    return credentials

def initialize_driver():
    """Initialize and return a Selenium WebDriver."""
    print("Initializing browser...")
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error initializing browser: {e}")
        return None

def login(driver, username, password):
    """Navigate to the login page and attempt to log in."""
    print("Navigating to login page...")
    driver.get("https://banner9.icesi.edu.co/ic_reservas/login")
    
    try:
        wait = WebDriverWait(driver, 10)
        
        # Finding login form elements
        # These selectors need to be updated based on actual page inspection
        print("Looking for login form...")
        username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        
        # Fill in credentials
        print("Filling in credentials...")
        username_field.send_keys(username)
        password_field.send_keys(password)
        
        # Find and click login button
        login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        login_button.click()
        
        # Wait for successful login
        print("Attempting login...")
        wait.until(EC.url_changes("https://banner9.icesi.edu.co/ic_reservas/login"))
        print("Login successful!")
        return True
    
    except TimeoutException:
        print("Login failed or page timed out.")
    except Exception as e:
        print(f"An error occurred during login: {e}")
    
    return False

def main():
    """Main function to run the automation."""
    print("Welcome to the Study Room Reservation Tool")
    print("------------------------------------------")
    
    # Get user credentials
    credentials = get_credentials()
    
    # Initialize WebDriver
    driver = initialize_driver()
    
    if not driver:
        print("Could not initialize browser. Exiting...")
        return
    
    try:
        # Attempt to log in
        login_success = login(driver, credentials["username"], credentials["password"])
        
        if login_success:
            print("You are now logged in!")
            # Add your reservation automation code here
            # ...
            
            input("Press Enter to close the browser and exit...")
        else:
            print("Login was unsuccessful.")
            print("\nTip: You may need to adjust the selectors in the script.")
            print("Right-click on the username field and select 'Inspect' to find the correct ID.")
            time.sleep(5)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()