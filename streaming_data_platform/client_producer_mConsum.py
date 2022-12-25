import asyncio
import logging
import pandas as pd
from asyncua import Client, Node, ua
import sys
sys.path.insert(0, "..")

import matplotlib.cbook
import warnings

warnings.filterwarnings("ignore",category=matplotlib.cbook.mplDeprecation)

from datetime import datetime
from kafka import KafkaProducer

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('asyncua')

class SubHandler(object):
    # Subscription Handler.
    def datachange_notification(self, node, val, data):
        print("New data change event", node, val)

    def event_notification(self, event):
        print("New event", event)

async def main():
    # Connect with opc-ua server
    url = 'opc.tcp://0.0.0.0:4842/opcua/server_mConsum/'
    client = Client(url=url)

    # Create a Kafka Producer
    producer = KafkaProducer(bootstrap_servers='localhost:9092')
    
    async with client:

        uri = 'http://pjs.uni-wue.de'
        idx = await client.get_namespace_index(uri)
 
        varDateTime = await client.nodes.root.get_child(["0:Objects", f"{idx}:SEHO Sensors", f"{idx}:dateTime"])
        varMConsum = await client.nodes.root.get_child(["0:Objects", f"{idx}:SEHO Sensors", f"{idx}:managementConsumption (kWh)"])

        # subscribing to a variable node
        handler = SubHandler()
        sub = await client.create_subscription(10, handler)
        handle0 = await sub.subscribe_data_change(varDateTime)
        handle3 = await sub.subscribe_data_change(varMConsum)
        await asyncio.sleep(0.1)
        
        # subscribe to events from server
        await sub.subscribe_events()
        
        while True:
            await asyncio.sleep(1)
            
            # requesting the values
            dateTimeStr = await varDateTime.read_value()
            mConsumValue = await varMConsum.read_value()
            
            # convert DateTime String to type DateTime object
            dateTimeValue = datetime.strptime(dateTimeStr, '%Y-%m-%d %H:%M:%S')
            
            """ Push to Kafka """
            # Push DateTime as Key and management consumption (kWh) as Value
            producer.send('mConsum', key=bytes(str(dateTimeValue), 'utf-8'), value=bytes(str(mConsumValue), 'utf-8'))

if __name__ == '__main__':
    asyncio.run(main())
