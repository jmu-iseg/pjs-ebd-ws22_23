import logging
import asyncio
import pandas as pd

from asyncua import ua, Server
from asyncua.common.methods import uamethod

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger('asyncua')

@uamethod
def func(parent, value):
    return value * 2

async def main():
    # setup our server
    server = Server()
    await server.init()
    server.set_endpoint('opc.tcp://127.0.0.1:4840/opcua/')
    server.set_server_name("DevNet OPC-UA Test Server")

    # setup our own namespace, not really necessary but should as spec
    uri = 'http://devnetiot.com/opcua/'
    idx = await server.register_namespace(uri)

    # populating our address space
    # server.nodes, contains links to very common nodes like objects and root
    obj_vplc = await server.nodes.objects.add_object(idx, 'vPLC1')
    var_output = await obj_vplc.add_variable(idx, 'output (kWh)', 0)
    var_basicConsumption = await obj_vplc.add_variable(idx, 'basicConsumption (kWh)', 0)

    # Read Sensor Data from Kaggle
    df = pd.read_csv("sensor.csv")
    # Only use sensor data from 03 and 01 (preference)
    sensor_data = pd.concat([df["output (kWh)"], df["basicConsumption (kWh)"]], axis=1)

    _logger.info('Starting server!')
    async with server:
        # run forever and iterate over the dataframe
        while True:
            for row in sensor_data.itertuples():
                # Writing Variables
                await var_output.write_value(float(row[1]))
                await var_basicConsumption.write_value(float(row[2]))
                await asyncio.sleep(1)

if __name__ == '__main__':
    #python 3.6 or lower
    #loop = asyncio.get_event_loop()
    #loop.run_until_complete(main())
    #python 3.7 onwards (comment lines above)
    asyncio.run(main())