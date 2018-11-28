import requests
res = requests.post('http://127.0.0.1:5000/api/Genes/?offset=100', json={"mytext":"lalala"})
if res.ok:
    print(res.json())
else :
    print("Error")
