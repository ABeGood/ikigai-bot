FROM python:3.10.11

ENV BOT_TOKEN='7033123838:AAGIVMfG5C2hIHUB0I2S4sNCZDZx4JOH9SM'

# set a directory for the app
WORKDIR /app

# copy all the files to the container
COPY . .

# install app-specific dependencies
RUN pip install --no-cache-dir -r requirements.txt

# app command
CMD ["python", "-u", "./main.py"]