from kafka import KafkaConsumer
import mysql.connector
import pandas as pd
import functools as ft

#cursor.execute("CREATE TABLE phData (datetime DATETIME, output FLOAT, basicConsumption FLOAT, managementConsumption FLOAT, productionConsumption FLOAT)")

df = pd.DataFrame()

# Define topics
topics = ["weather"]
   
""" Consumer """
consumer = KafkaConsumer(auto_offset_reset='earliest',
                         client_id='local-test',
                         bootstrap_servers=['localhost:9092'])
# Subscribe to topics
consumer.subscribe(topics=topics)

while True:
    print('polling...')
    records = consumer.poll(timeout_ms=360000)
    
    #read items
    for _, consumer_records in records.items():
        # Parse records
        for consumer_record in consumer_records:
            # get information
            dataTemp = [[consumer_record.topic, consumer_record.key.decode("utf-8") , consumer_record.value.decode("utf-8") ]]
            dfTemp = pd.DataFrame(dataTemp, columns=["topic", "dateTime", "value"])
            
            # add the information to the DataFrame
            df = pd.concat([df, dfTemp], axis=0)

        continue
    
    # Create a DataFrame for each topic and rename value and drop column "topic"
    dfWeather = df[df['topic'] == "weather"].rename({'value': 'weather'}, axis=1).drop('topic', axis=1)

    print(dfWeather)

