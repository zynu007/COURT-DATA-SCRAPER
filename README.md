Court Data Scraper: Delhi High Court Case Fetcher
Hi there! This project is a Python-based web scraper designed to automatically fetch and display case information from the Delhi High Court website. The goal was to build a reliable and robust tool capable of handling the site's specific requirements, such as CAPTCHA validation, to retrieve publicly available data. This scraper is containerized using Docker, ensuring a consistent and reproducible environment for anyone who needs to run it.

Why the Delhi High Court Website?
I chose the Delhi High Court website for this project because its technical implementation presented a unique and interesting challenge. While many websites use complex image-based CAPTCHAs that require expensive third-party APIs to solve, the Delhi High Court site uses a simple four-digit number. After inspecting the page, I discovered this number is stored directly as text within an HTML tag.

This insight allowed me to implement a low-cost, efficient solution. Instead of relying on external services, the scraper reads the number directly from the HTML and uses an API POST call with the correct CSRF token and inputs to correctly mock the CAPTCHA validation request. This approach is both cost-effective and performant.

Key Features
Robust Scraping: The core of the project is a web scraper built with Python and Playwright, capable of navigating the court's website, entering case details, and correctly handling the CAPTCHA.

Intelligent CAPTCHA Handling: As mentioned, the scraper reads a simple four-digit number from the HTML and uses an API call to validate it. This avoids the need for manual intervention or expensive third-party services.

Rate Limiting: To be a responsible user of the court's public resources and to prevent any potential misuse of the server, I have implemented a rate-limiting mechanism. This limits the number of requests the scraper can make per minute.

Data Persistence: Using a Flask backend with SQLAlchemy and a SQLite database, the application caches search queries and their results. This prevents redundant scraping and improves the performance of repeat queries.

Containerization with Docker: The entire application is packaged within a Docker container. This makes the project portable and easy to set up on any system, eliminating "it works on my machine" issues.

Intuitive UI: A simple frontend built with Vue.js and Tailwind CSS allows users to easily input search criteria and view the results in a clean, organized manner.

How to Run this Project Locally (A to Z Guide)
Follow these steps to get a local copy of the project up and running.

Prerequisites
Docker Desktop: Ensure you have Docker Desktop installed and running on your machine.

Git: You'll need Git to clone the repository.

Step 1: Clone the Repository
First, clone this repository to your local machine using your preferred terminal.

git clone https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories
cd [your-repo-name]

Step 2: Build the Docker Image
Navigate to the root directory of the project (the one containing the Dockerfile) and build the Docker image.

docker build -t court-data-scraper .

This command builds the image and tags it as court-data-scraper. It may take a few minutes as Docker downloads the base image and installs all the necessary dependencies.

Step 3: Run the Docker Container
Once the image is built, you can run the application inside a container with the following command:

docker run -p 5000:5000 court-data-scraper

The -p 5000:5000 flag maps the container's port 5000 to port 5000 on your local machine, allowing you to access the application via your web browser.

Step 4: Access the Application
After running the docker run command, open your web browser and go to:

http://localhost:5000

You should see the application's user interface, ready for you to search for case data!

Project Structure
.
├── backend/
│   ├── app.py          # Flask application and API routes
│   ├── config.py       # Configuration settings
│   ├── database.py     # SQLAlchemy models
│   ├── scraper.py      # Core scraping logic with Playwright
│   ├── utils.py        # Helper functions
│   ├── requirements.txt# Python dependencies
│   ├── templates/      # Jinja2 templates (contains index.html)
│   └── instance/       # Database file location
├── Dockerfile          # Docker configuration for building the image
└── README.md           # This file
