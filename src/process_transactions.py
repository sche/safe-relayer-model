
from models import SafeTx


def main():
    # parse file and load transactions data
    lines = tuple(open('safe_tx_hashes_test.txt', 'r'))
    for line in lines:
        safe_tx_hash = line.strip()
        SafeTx.process_transaction(safe_tx_hash)


if __name__ == '__main__':
    main()
