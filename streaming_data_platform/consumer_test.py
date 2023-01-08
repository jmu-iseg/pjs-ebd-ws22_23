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
consumer = KafkaConsumer(auto_offset_reset='earliest',
                         client_id='local-test',
                         bootstrap_servers=['localhost:9092'])

# empty set
weather_topics = set()

# check if topic starts with 'weather' and write it to a new set
for sub_topic in consumer.topics():
    if sub_topic.startswith("weather"):
        
        #remove 'weather'
        sub_topic = sub_topic.removeprefix("weather")
        
        # check if sub_topic is not empty
        if sub_topic:
            # checking if format matches the date
            res = True
            
            # using try-except to check for truth value
            try:
                res = bool(datetime.datetime.strptime(sub_topic, '%y-%m-%d-%H-%M-%S'))
            except ValueError:
                res = False
            
            # add subtopic to new set
            if res:
                weather_topics.add(sub_topic)

print(weather_topics)
print(max(weather_topics, key=lambda x: datetime.datetime.strptime(x, '%y-%m-%d-%H-%M-%S')))

top_topic = "weather"+max(weather_topics, key=lambda x: datetime.datetime.strptime(x, '%y-%m-%d-%H-%M-%S'))

# Subscribe to topics
consumer.subscribe(topics=top_topic)

print('polling...')
records = consumer.poll(timeout_ms=1000)

print("Test")
print(records)

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
df = df.reset_index()

json_object = "("
for index, row in df.iterrows():
    if index != 0:
        print(row['value'])
        json_object+=str(","+row['value'])
    else:
        print(row['value'])
        json_object+=str(row['value'])
json_object+=")"
# save as json
with open("data.json", "w") as outfile:
    outfile.write(json_object)