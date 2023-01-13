from kafka import KafkaConsumer
import pandas as pd
import sys
sys.path.append('..')
from app import app, get_config

# create empty dataframe
df = pd.DataFrame()

# get config values
config = get_config(app.root_path)
kafka_url = config['kafka']['kafka_url']
kafka_port = config['kafka']['kafka_port']

""" Consumer """
consumer = KafkaConsumer('weather_data',
                         auto_offset_reset='earliest',
                         group_id='weather-consumer',
                         bootstrap_servers=[kafka_url+':'+kafka_port])

# get topic data
print('polling...')
records = consumer.poll(timeout_ms=1000)
print(records)

#read items
for _, consumer_records in records.items():
    # Parse records
    for consumer_record in consumer_records:
        # get information
        varData = consumer_record.value.decode("utf-8").replace("'",'"')

# save as json
with open("data.json", "w") as outfile:
    outfile.write(varData)