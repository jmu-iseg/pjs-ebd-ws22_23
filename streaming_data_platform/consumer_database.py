from kafka import KafkaConsumer
import mysql.connector
import pandas as pd
import functools as ft


# Connect to MySQL
cnx = mysql.connector.connect(user='p625051d1',
                              password='y5!,t1oAasthnj',
                              host='db4407.mydbserver.com',
                              database='usr_p625051_1')
cursor = cnx.cursor()

#cursor.execute("CREATE TABLE phData (datetime DATETIME, output FLOAT, basicConsumption FLOAT, managementConsumption FLOAT, productionConsumption FLOAT)")

df = pd.DataFrame()

# Define topics
topics = ["phOutput", "bConsum", "mConsum", "pConsum"]
   
""" Consumer """
consumer = KafkaConsumer(auto_offset_reset='earliest',
                         client_id='local-test',
                         bootstrap_servers=['localhost:9092'])
# Subscribe to topics
consumer.subscribe(topics=topics)

while True:
    print('polling...')
    records = consumer.poll(timeout_ms=1000)
    
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
    dfPhOutput = df[df['topic'] == "phOutput"].rename({'value': 'output'}, axis=1).drop('topic', axis=1)
    dfBConsum = df[df['topic'] == "bConsum"].rename({'value': 'bConsum'}, axis=1).drop('topic', axis=1)
    dfMConsum = df[df['topic'] == "mConsum"].rename({'value': 'mConsum'}, axis=1).drop('topic', axis=1)
    dfPConsum = df[df['topic'] == "pConsum"].rename({'value': 'pConsum'}, axis=1).drop('topic', axis=1)
    
    # Merge DataFrames together on dateTime
    dfs = [dfPhOutput, dfBConsum, dfMConsum, dfPConsum]
    dfFinal = ft.reduce(lambda left, right: pd.merge(left, right, on='dateTime'), dfs)
    # Sammeln
    
    
    for index, row in dfFinal.iterrows():
        # Select Data and save them to the DataBase
        add_data = ("INSERT INTO phData "
                       "(datetime, output, basicConsumption, managementConsumption, productionConsumption) "
                       "VALUES (%(dateTime)s, %(output)s, %(bConsum)s, %(mConsum)s, %(pConsum)s)")
        
        data_ph = {
          'dateTime': row['dateTime'],
          'output': row['output'],
          'bConsum': row['bConsum'],
          'mConsum': row['mConsum'],
          'pConsum': row['pConsum']
        }
        
        cursor.execute(add_data, data_ph)
        
        # Make sure data is committed to the database
        cnx.commit()
    
    cursor.close()
    cnx.close()