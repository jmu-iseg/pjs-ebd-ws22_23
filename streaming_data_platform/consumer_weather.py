from kafka import KafkaConsumer
import pandas as pd
import sys
sys.path.append('..')
from app import app, get_config

# Create empty dataframe
df = pd.DataFrame()

# Get config values
config = get_config(app.root_path)

# Get the kafka config values
kafka_url = config['kafka']['kafka_url']
kafka_port = config['kafka']['kafka_port']

# Create a kafka consumer
consumer = KafkaConsumer('weather_data',
                         auto_offset_reset='earliest',
                         group_id='weather-consumer',
                         bootstrap_servers=[kafka_url+':'+kafka_port])

# Get topic data
print('polling...')
records = consumer.poll(timeout_ms=1000)
print(records)

try:
    # Read items
    for _, consumer_records in records.items():
        # Parse records
        for consumer_record in consumer_records:
            # get information
            varData = consumer_record.value.decode("utf-8").replace("'",'"')
except TypeError:
    print('TypeError')

# save as json
with open("weather_forecast.json", "w") as outfile:
    outfile.write(varData)