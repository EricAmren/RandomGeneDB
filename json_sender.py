import requests
res = requests.post('http://amren.pythonanywhere.com/api/Genes/?offset=100', json={"mytext":"lalala"})
if res.ok:
    print(res.json())
else :
    print("Error")
