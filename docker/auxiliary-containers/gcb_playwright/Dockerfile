FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Install dependencies
RUN apt-get update && apt-get install -y  curl  wget  gnupg  && rm -rf /var/lib/apt/lists/*

# Install Playwright
RUN pip install playwright

# Set up Playwright dependencies for Chromium, Firefox and Webkit
RUN playwright install
RUN playwright install-deps

CMD ["/bin/bash"]
