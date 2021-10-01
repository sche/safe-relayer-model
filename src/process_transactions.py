from models import SafeTx
from csv import reader


def main():
    with open('transactions.csv', 'r') as read_obj:
        csv_reader = reader(read_obj)
        header = next(csv_reader)
        for row in csv_reader:
            SafeTx.process_transaction(row)


if __name__ == '__main__':
    main()
