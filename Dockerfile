# Placeholder Dockerfile for pytest-prairielearn-grader
# Replace with your actual Dockerfile content

FROM python:3.13-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies and the package
ARG PACKAGE_VERSION=latest
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pytest-prairielearn-grader==${PACKAGE_VERSION}

# Default command
CMD ["pytest"]
