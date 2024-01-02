FROM python:3.11

# Install Cron.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install -y cron curl \
    # Remove package lists for smaller image sizes
    && rm -rf /var/lib/apt/lists/* \
    && which cron \
    && rm -rf /etc/cron.*/*

# Create the Django project directory
WORKDIR /app

# Copy the project files to the working directory
COPY . .

# Add Environment variables.
ARG ENV
ARG DEBUG

ENV ENV $ENV
ENV DEBUG $DEBUG

# Install Python dependencies.
RUN pip install -r requirements.txt

# Set the default timezone
# ENV TZ America/New_York
# ENV POSTGRES_VERSION postgres-15

CMD ["python", "manage.py", "run_scheduled_tasks"]

