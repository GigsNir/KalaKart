import requests

response = requests.post(
    "https://api.mailgun.net/v3/sandbox4ed6e3bae9da45de9a12da37a849243b.mailgun.org/messages",
    auth=("api", "62caf43ddd2cc9023e8b35b18f13e4e8-667818f5-979cbe34"),
    data={"from": "gigyashaniroula02@gmail.com",
          "to": ["gigyashaniroula02@gmail.com"],
          "subject": "Test Email",
          "text": "This is a test email from Mailgun!"})

print(response.text)



