from datetime import datetime
from kafka import KafkaProducer
import requests
import configparser
import os

# get config values
config = configparser.ConfigParser()
config.read(os.path.abspath(os.curdir)+'/settings.cfg')

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

    # Push DateTime as Key and Output (kWh) as Value
    producer.send('weather', key=bytes(str(date_string), 'utf-8'),
              value=bytes(str(day), 'utf-8'))