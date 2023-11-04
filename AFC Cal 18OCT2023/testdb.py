import json
import requests   

""" f = open('1680339205_CSM221500018_FAIL.json')
data = json.load(f)
r= requests.post('https://fusion.paygoenergy.io/api/v1/assembly-events', data) """
x = requests.get('https://fusion.paygoenergy.io/api/v1/assembly-parts/SR231000031') 
x=x.json()
#print(r.json())
print(x['overall_result'])