import requests
from dotenv import dotenv_values
from web3 import Web3
from datetime import datetime, timedelta
import time
from models import Block

AVARAGE_BLOCK_TIME = timedelta(seconds=13)

config = dotenv_values(".env")
w3 = Web3(Web3.HTTPProvider(config['INFURA_MAINNET']))


def main():
    # parse file and load transactions data
    lines = tuple(open('safe_tx_hashes_test.txt', 'r'))
    transactions_data = []
    for line in lines:
        safe_tx_hash = line.strip()
        r = get_tx(safe_tx_hash)
        if r.status_code != 200:
            print('Failed to load data for safe_tx_hash: {}'.format(safe_tx_hash))
            continue
        transactions_data.append(r.json())

    for tx in transactions_data:
        block_for_first_confirmation = get_block_for_first_confirmation(tx)
        block_for_execution = get_block(tx['blockNumber'])
        print("block_for_first_confirmation: {}; block_for_execution: {}".format(block_for_first_confirmation, block_for_execution))


def get_block(number):
    attempts = 0
    b = Block.by(number)
    while b is None and attempts < 5:
        b = index_block(number)
        if attempts > 0:
            time.sleep(3)
        attempts += 1
    return b


def index_block(number):
    block = w3.eth.get_block(number)
    if block.number is not None:
        print("Indexed block #", block.number)
        return Block.create(number=number,
                            date=datetime.utcfromtimestamp(block.timestamp),
                            baseFeePerGas=block.baseFeePerGas)
    else:
        return None


def get_tx(safe_tx_hash):
    return requests.get('{}api/v1/multisig-transactions/{}/'.format(config['TX_SERVICE_MAINNET'], safe_tx_hash))


def get_tx_initiation_to_execution_time(tx_data):
    confirmation_dates = get_confirmation_dates(tx_data)
    execution_date = parse_date(tx_data['executionDate'])
    return execution_date - confirmation_dates[0]


def get_confirmation_dates(tx_data):
    return sorted([parse_date(c['submissionDate']) for c in tx_data['confirmations']])


def get_block_for_first_confirmation(tx_data):
    init_to_execute_time = get_tx_initiation_to_execution_time(tx_data)
    init_to_execute_blocks = int(
        init_to_execute_time.total_seconds() / AVARAGE_BLOCK_TIME.total_seconds())
    expected_block_number_for_first_confirmation = tx_data['blockNumber'] - \
        init_to_execute_blocks

    search_block = get_block(expected_block_number_for_first_confirmation)
    first_confirmation_date = get_confirmation_dates(tx_data)[0]

    while search_block.date < first_confirmation_date:
        expected_block_number_for_first_confirmation += 1
        search_block = get_block(expected_block_number_for_first_confirmation)

    while search_block.date > first_confirmation_date:
        expected_block_number_for_first_confirmation -= 1
        search_block = get_block(expected_block_number_for_first_confirmation)

    return search_block


def parse_date(date_string):
    try:
        return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)
    except Exception:
        return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%f%z').replace(tzinfo=None)


if __name__ == '__main__':
    main()
