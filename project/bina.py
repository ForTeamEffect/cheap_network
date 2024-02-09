import requests
import time
import hmac
import hashlib

from settings import api_key_bin, api_secret_bin

timestamp = int(time.time() * 1000)
params = {
    'timestamp': timestamp,
    # 'currency': 'USDT',
    # 'chain': 'TRC20'
}

query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
signature = hmac.new(api_secret_bin.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

headers = {
    'X-MBX-APIKEY': api_key_bin
}

def get_trc_bin():
    try:
        response = requests.get('https://api.binance.com/sapi/v1/capital/config/getall', headers=headers,
                                params={**params, 'signature': signature})
        response.raise_for_status()
        withdraw_fees = response.json()

        for coin_info in withdraw_fees:
            if coin_info['coin'] == 'USDT':
                trx_network = [network for network in coin_info['networkList'] if network['network'] == 'TRX']
                if trx_network:
                    trx_network = trx_network[0]
                    if 'maintenance' not in trx_network['depositDesc'].lower() and not trx_network['withdrawDesc']:
                        # return {"min_size": trx_network['withdrawMin'],
                        comsa = trx_network['withdrawFee']
                        return float(comsa)


    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')

print(get_trc_bin())
