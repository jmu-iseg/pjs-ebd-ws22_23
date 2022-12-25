from flask import Flask, render_template
from kafka import KafkaConsumer
import pandas as pd
import functools as ft

df = pd.DataFrame()

topics = ["phOutput", "bConsum", "mConsum", "pConsum"]
   
""" Consumer """
consumer = KafkaConsumer(auto_offset_reset='earliest',
                         client_id='local-test',
                         bootstrap_servers=['localhost:9092'])
# Subscribe to topics
consumer.subscribe(topics=topics)

# poll data
records = consumer.poll(timeout_ms=1000)

# read items
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
dfPhOutput = df[df['topic'] == "phOutput"].rename({'value': 'output'}, axis=1).drop('topic', axis=1)
dfBConsum = df[df['topic'] == "bConsum"].rename({'value': 'bConsum'}, axis=1).drop('topic', axis=1)
dfMConsum = df[df['topic'] == "mConsum"].rename({'value': 'mConsum'}, axis=1).drop('topic', axis=1)
dfPConsum = df[df['topic'] == "pConsum"].rename({'value': 'pConsum'}, axis=1).drop('topic', axis=1)

# Merge DataFrames together on dateTime
dfs = [dfPhOutput, dfBConsum, dfMConsum, dfPConsum]
dfFinal = ft.reduce(lambda left, right: pd.merge(left, right, on='dateTime'), dfs)




# Convert DateDtime Series to string list
dateTimeStr = dfFinal['dateTime'].tolist()

# Create the Webserver

app = Flask(__name__)
@app.route("/")

def home():
    return render_template("graph.html", labels=dfFinal['dateTime'].tolist(), output=dfFinal['output'].tolist(), bConsum=dfFinal['bConsum'].tolist(), mConsum=dfFinal['mConsum'].tolist(), pConsum=dfFinal['pConsum'].tolist())
