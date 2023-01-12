from datetime import datetime
from kafka import KafkaProducer
import requests
import configparser
import os
from pathlib import Path
import time
from kafka.errors import KafkaError

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
response = requests.post('https://pro.openweathermap.org/data/2.5/forecast/climate?units=metric&lat='+lat+'&lon='+lon+'&appid='+key+'&lang=DE')

# Print the status code of the response
print(response.status_code) # should return 200

# Print the content of the response
response_content = response.json()

# get the kafka config values
kafka_url = config['kafka']['kafka_url']
kafka_port = config['kafka']['kafka_port']

# Create a Kafka Producer
producer = KafkaProducer(bootstrap_servers=[kafka_url+':'+kafka_port])

# get Datetime
act_datetime = datetime.now()

# Error logging
def on_send_success(record_metadata):
    print(record_metadata.topic)
    print(record_metadata.partition)
    print(record_metadata.offset)

def on_send_error(excp):
    print('I am an errback', exc_info=excp)
    # handle exception

# Push Weather as Value
producer.send('weather_data', value=bytes(str(response_content), 'utf-8'))

# Flush the message to send it
producer.flush()