###
#    TODO: Diese Datei regelmäßig über einen Cron ausführen
###
from kafka import KafkaConsumer
#import mysql.connector
import pandas as pd
import functools as ft
import datetime

#cursor.execute("CREATE TABLE phData (datetime DATETIME, output FLOAT, basicConsumption FLOAT, managementConsumption FLOAT, productionConsumption FLOAT)")

df = pd.DataFrame()
   
""" Consumer """
consumer = KafkaConsumer('weather_data',
                         auto_offset_reset='earliest',
                         group_id='weather-consumer',
                         bootstrap_servers=['localhost:9092'])


print('polling...')
records = consumer.poll(timeout_ms=1000)

print(records)


#read items
for _, consumer_records in records.items():
    # Parse records
    for consumer_record in consumer_records:
        # get information
        varData = consumer_record.value.decode("utf-8")


# save as json
with open("data.json", "w") as outfile:
    outfile.write(varData)