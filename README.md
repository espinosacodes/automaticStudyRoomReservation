# Study Room Reservation Automation

## Introduction
This Python script automates the process of logging into the study room reservation system at `banner9.icesi.edu.co/ic_reservas/login`. It securely stores credentials locally and uses Selenium to handle browser automation.

## Requirements
* Python 3.6 or higher
* Chrome browser installed
* Internet connection

## Installation
1. Clone or download this repository:

```bash
git clone https://github.com/yourusername/automaticStudyRoomReservation.git
cd automaticStudyRoomReservation

2. Set up a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```
4. Ensure you have the Chrome WebDriver installed and available in your PATH. You can download it from [here](https://sites.google.com/chromium.org/driver/downloads).
5. Set up your credentials:
   - Create a file named `credentials.json` in the root directory of the project with the following structure:

```json
{
    "username": "your_username",
    "password": "your_password"
}
```
Make sure to replace `your_username` and `your_password` with your actual credentials.

6. Set up the reservation time:
   - Create a file named `reservationTime.json` in the root directory of the project with the following structure:

```json
[
    {
        "day": "Thursday",
        "startTime": "18:00",
        "endTime": "20:00"
    },
    {
        "day": "Friday",
        "startTime": "9:00",
        "endTime": "13:00"
    }
]
```

7. run the script:

```bash
python studyRoomReservation.py
```

enjoy! 
fell free to contribute to this project by adding more features or improving the code.
## Features
- Securely stores credentials using `cryptography` library.
- Uses Selenium to automate the login process.
- Handles browser interactions to navigate the reservation system.
- Allows for easy configuration of reservation times and days.
- Provides feedback on the reservation status.
- Automatically closes the browser after the reservation process is complete.
- Handles exceptions and errors gracefully.
- Uses `json` for configuration files to easily modify reservation times and credentials.
- Uses `logging` for better debugging and error tracking.
- Uses `argparse` for command-line argument parsing.
- Uses `dotenv` for environment variable 