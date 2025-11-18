import requests

sample_input = {
    "columns": [
        "CRIM","ZN","INDUS","CHAS","NOX","RM","AGE","DIS",
        "RAD","TAX","PTRATIO","B","LSTAT"
    ],
    "data": [[0.2, 0.0, 7.0, 0, 0.5, 6.0, 40, 5.2, 4, 300, 15.0, 390, 10.5]]
}

url = "http://127.0.0.1:5002/invocations"

response = requests.post(url, json=sample_input)
print(response.json())
