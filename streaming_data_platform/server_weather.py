import requests
import json
import logging
import asyncio
import sys
import pandas as pd
sys.path.insert(0, "..")

from asyncua import ua, Server
from asyncua.common.methods import uamethod

@uamethod
def func(parent, value):
    return value * 2

async def main():
    _logger = logging.getLogger('asyncua')
    # setup the server
    server = Server()
    await server.init()
    server.set_endpoint('opc.tcp://0.0.0.0:4840/opcua/weather/')

    # setup the namespace
    uri = 'http://pjs.uni-wue.de/weather'
    idx = await server.register_namespace(uri)

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

    # populating our address space
    # server.nodes, contains links to very common nodes like objects and root
    obj = await server.nodes.objects.add_object(idx, 'Weather')
    varDateTime = await obj.add_variable(idx, 'dateTime', 0, ua.VariantType.String)
    varWeather = await obj.add_variable(idx, 'weather', 0, ua.VariantType.String)
    
    # Set Variables to be writable by clients
    await varDateTime.set_writable()
    await varWeather.set_writable() 
    
    await server.nodes.objects.add_method(ua.NodeId('ServerMethod', 2), ua.QualifiedName('ServerMethod', 2), func, [ua.VariantType.Int64], [ua.VariantType.Int64])
    _logger.info('Starting server!')
    async with server:
        while True:
            for day in response_content["list"]:
                valDateTime = 'test'
                print(type(day))
                # giving values
                await varDateTime.write_value(valDateTime)
                await varWeather.write_value(str(day))
                
                # wait 1 day before repeating
                #await asyncio.sleep(3600)
                
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main(), debug=True)