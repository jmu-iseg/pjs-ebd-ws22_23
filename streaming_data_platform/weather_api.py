import requests
import json

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

# Get forecast for every day
for day in response_content["list"]:
    print(day)
    print("____")

# safe as json
#with open('data.json', 'w') as fp:
#    json.dump(response_content, fp)