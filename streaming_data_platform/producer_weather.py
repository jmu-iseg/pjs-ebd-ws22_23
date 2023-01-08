from datetime import datetime
from kafka import KafkaProducer
import requests
import configparser
import os
from pathlib import Path
import time

# get config values
config = configparser.ConfigParser()
path = Path(os.curdir)
config.read(os.path.join(os.path.abspath('..'),'app/settings.cfg'))
print(os.path.join(os.path.abspath('..'),'app/settings.cfg'))

# specify the location
lat = config['weather']['lat']
lon = config['weather']['lon']

# specify the api key
key = config['weather']['openweatherapikey']

# Make the POST request
response = requests.post('https://pro.openweathermap.org/data/2.5/forecast/climate?units=metric&lat='+lat+'&lon='+lon+'&appid='+key)

# Print the status code of the response
print(response.status_code) # should return 200

# Print the content of the response
response_content = response.json()

# Create a Kafka Producer
producer = KafkaProducer(bootstrap_servers='localhost:9092')

# Get forecast for every day and push it to kafka
for day in response_content["list"]:
    # Convert Date
    date = datetime.fromtimestamp(day["dt"])
    date_string = date.strftime("%Y-%m-%d")

    print(date_string)
    print("____")

    # get Datetime
    act_datetime = datetime.datetime.now()

    # Push Date as Key and Weather as Value
    producer.send('weather_' + act_datetime.strftime("%y-%m-%d_%H:%M"), key=bytes(str(date_string), 'utf-8'),
            value=bytes(str(day), 'utf-8'))