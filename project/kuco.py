import requests
from requests.exceptions import HTTPError
import hmac
import hashlib
import time
import base64

from settings import api_key_ku, api_secret_ku, api_passphrase_ku


# Параметры для аутентификации запросов на KuCoin используют другой подход
timestamp = str(int(time.time() * 1000))
method = 'GET'
endpoint = '/api/v1/withdrawals/quotas'
params = '?currency=USDT&chain=TRC20'
url = 'https://api.kucoin.com' + endpoint + params
str_to_sign = timestamp + method + endpoint + params
signature = base64.b64encode(
    hmac.new(api_secret_ku.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest()
)

headers = {
    "KC-API-SIGN": signature,
    "KC-API-TIMESTAMP": timestamp,
    "KC-API-KEY": api_key_ku,
    "KC-API-PASSPHRASE": api_passphrase_ku,  # The passphrase you set when creating the API key
}


def get_trc_kucoin():
    try:
        response = requests.request(method, url, headers=headers)
        response.raise_for_status()
        # Обработка ответа от KuCoin
        data = response.json()
        # print(data)
        # Извлечение данных о комиссии для Tron
        if data and 'data' in data:
            tron_data = data['data']
            # return {"min_size": tron_data['withdrawMinSize'],
            comsa = tron_data['withdrawMinFee']
            return float(comsa)


    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')  # КуКоин возвращает подробную информацию об ошибке
    except Exception as err:
        print(f'Other error occurred: {err}')  # Ошибка, не связанная с HTTP

print(get_trc_kucoin())