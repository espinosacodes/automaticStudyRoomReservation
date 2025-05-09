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

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```
3. Ensure you have the Chrome WebDriver installed and available in your PATH. You can download it from [here](https://sites.google.com/chromium.org/driver/downloads).
4. Set up your credentials:
   - Create a file named `credentials.json` in the root directory of the project with the following structure:

```json
{
    "username": "your_username",
    "password": "your_password"
}
```