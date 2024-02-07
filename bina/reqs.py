# from binance.client import Client
#
api_key = 'owZvGkCXVvThmxrspryOxALk0Cb0RZMf8FrsCGdN0ccVzLsJGHM6FjksUliQke9V'
api_secret = 'weD680gnO4p1JOSg3b4Oi7BWwf8aB35s9ygrtp3GLvfhaaqLhFIIykaDlTyIgyrD'
#
# client = Client(api_key, api_secret)
#
# # Получение информации о комиссиях для USDT на блокчейне Tron (TRC20)
# # Учти, что символ и блокчейн могут отличаться, проверь актуальные данные на момент реализации
# fees = client.get_trade_fee(symbol='TRXUSDT', recvWindow=60000)
#
# print(fees)


# import requests
#
# api_url = "https://api.binance.com"
# endpoint = "/wapi/v3/withdrawFee.html"
# params = {"asset": "USDT"}
#
# response = requests.get(f"{api_url}{endpoint}", params=params)
# if response.status_code == 200:
#     data = response.json()
#     print(data)
# else:
#     print("Ошибка запроса", response.status_code)
import requests
import time
import hmac
import hashlib


timestamp = int(time.time() * 1000)
params = {
    'timestamp': timestamp
}

query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

headers = {
    'X-MBX-APIKEY': api_key
}

try:
    response = requests.get('https://api.binance.com/sapi/v1/capital/config/getall', headers=headers,
                            params={**params, 'signature': signature})
    response.raise_for_status()
    withdraw_fees = response.json()

    for coin_info in withdraw_fees:
        if coin_info['coin'] == 'USDT' and any(network['network'] == 'TRX' for network in coin_info['networkList']):
            print(coin_info['coin'] == 'USDT')
            print(coin_info['networkList'])
            for nw in coin_info['networkList']:
                if not 'The wallet is currently undergoing maintenance' in nw['depositDesc'] and not nw['withdrawDesc']:
                    print(nw['network'], '-', nw['name'], ' = ', nw['withdrawFee'])
            print(
                f"Комиссия за вывод USDT в сети TRX: {next(network for network in coin_info['networkList'] if network['network'] == 'TRX')['withdrawFee']}")
except requests.exceptions.HTTPError as http_err:
    print(f'HTTP error occurred: {http_err}')
except Exception as err:
    print(f'Other error occurred: {err}')
