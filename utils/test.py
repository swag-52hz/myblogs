from utils import zhenzismsclient as smsclient
import random


code = ''
for num in range(1, 5):
    code = code + str(random.randint(0,9))
print(code)
client = smsclient.ZhenziSmsClient('https://sms_developer.zhenzikj.com', '101357', 'bf00ccbc-1f60-4f1c-a739-ba9ec7f4872d')
result = client.send('13576252623', '您的验证码为'+code)
print(result)

