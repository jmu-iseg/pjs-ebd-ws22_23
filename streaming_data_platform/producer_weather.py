from datetime import datetime
from kafka import KafkaProducer
import requests

# specify the location
lat = '49.7672'
long = '9.5183'

# specify the api key
key = '2976793f8fedfed783bff2512733ed4b'

# Make the POST request
response = requests.post('https://pro.openweathermap.org/data/2.5/forecast/climate?units=metric&lat='+lat+'&lon='+long+'&appid='+key)

# Print the status code of the response
print(response.status_code) # should return 200

# Print the content of the response
response_content = response.json()

# Create a Kafka Producer
producer = KafkaProducer(bootstrap_servers='localhost:9092')

# Get forecast for every day and push it to kafka
for day in response_content["list"]:
    print(day["dt"])
    print("____")

    datetime = datetime.datetime.fromtimestamp(day["dt"])

    # Push DateTime as Key and Output (kWh) as Value
    producer.send('weather', key=bytes(str(datetime), 'utf-8'),
              value=bytes(str(day), 'utf-8'))