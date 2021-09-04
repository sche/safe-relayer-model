
from models import SafeTx
import matplotlib.pyplot as plt
from statistics import mean


def main():
    # parse file and load transactions data
    lines = tuple(open('safe_tx_hashes_test.txt', 'r'))
    for line in lines:
        safe_tx_hash = line.strip()
        SafeTx.process_transaction(safe_tx_hash)

    transactions = SafeTx.all()
    
    # show tx initiation to execution times
    x = range(len(transactions))
    times = [t.tx_initiation_to_execution_time_sec / 60 for t in transactions]
    print("Mean in min: ", mean(times))
    plt.plot(x, times, 'bo', label="tx initiation to execution time in min")
    plt.legend(loc='upper left')
    plt.show()

if __name__ == '__main__':
    main()
