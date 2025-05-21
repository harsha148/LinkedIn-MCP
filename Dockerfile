FROM mcr.microsoft.com/playwright/python:v1.42.0

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Copy the rest of the application
COPY . .

# Use the existing user (usually 'playwright' with UID 1000)
USER 1000

# Expose the port
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]