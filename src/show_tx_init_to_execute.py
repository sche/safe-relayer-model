
from models import SafeTx
import matplotlib.pyplot as plt
from statistics import mean
import numpy as np
import scipy.stats as stats


def main():
    transactions = SafeTx.all()
    
    fig = plt.figure(constrained_layout=True)
    fig.suptitle('Safe tranasactions data sample')
    
    subfigs = fig.subfigures(5, 1)
    subfigs[0].suptitle('tx initiation to execution (time in min)')
    subfigs[1].suptitle('cumulative')
    subfigs[2].suptitle('base fee per gas price differences')
    subfigs[3].suptitle('base fee per gas price differences without zeroes')
    subfigs[4].suptitle('without zeroes cumulative')
    
    axs0 = subfigs[0].subplots(1, 3)
    axs1 = subfigs[1].subplots(1, 3)
    axs2 = subfigs[2].subplots(1, 3)
    axs3 = subfigs[3].subplots(1, 3)
    axs4 = subfigs[4].subplots(1, 3)
    
    # Transaction times
    times = [round(t.tx_initiation_to_execution_time_sec / 60, 2) for t in transactions]
    axs0[0].plot(range(len(times)), times, 'bo')
    axs0[0].set_title('raw data with outliers\n(total={}, mean={})'.format(len(times), round(mean(times), 2)))
    
    irm_transactions = removeOutliersIRM(transactions, 10)
    irm_times = [round(t.tx_initiation_to_execution_time_sec / 60, 2) for t in irm_transactions]
    axs0[1].plot(range(len(irm_times)), irm_times, 'bo')
    axs0[1].set_title('without outliers IRM (multiplier=10)\n(total={}, mean={})'.format(len(irm_times), round(mean(irm_times), 2)))
    
    zscore_transactions = removeOutliersZScore(transactions)
    zscore_times = [round(t.tx_initiation_to_execution_time_sec / 60, 2) for t in zscore_transactions]
    axs0[2].plot(range(len(zscore_times)), zscore_times, 'bo')
    axs0[2].set_title('without outliers Z-score\n(total={}, mean={})'.format(len(zscore_times), round(mean(zscore_times), 2)))
    
    # Transaction times histogram
    
    axs1[0].hist(times, 100, density=True, cumulative=True)
    axs1[0].grid(True)
    
    axs1[1].hist(irm_times, 100, density=True, cumulative=True)
    axs1[1].grid(True)
    
    axs1[2].hist(zscore_times, 100, density=True, cumulative=True)
    axs1[2].grid(True)
    
    # Transaction gas difference
    
    gweis = [round(t.base_fee_per_gas_price_difference / 1_000_000_000) for t in transactions]
    axs2[0].hist(gweis, 50)
    
    irm_gweis = [round(t.base_fee_per_gas_price_difference / 1_000_000_000) for t in irm_transactions]
    axs2[1].hist(irm_gweis, 50)
    
    zscore_gweis = [round(t.base_fee_per_gas_price_difference / 1_000_000_000) for t in zscore_transactions]
    axs2[2].hist(zscore_gweis, 50)
    
    # Transaction gas difference without zeroes
    
    gweis_without_zeroes = [round(t.base_fee_per_gas_price_difference / 1_000_000_000) for t in transactions if t.base_fee_per_gas_price_difference != 0]
    axs3[0].hist(gweis_without_zeroes, 50)
    axs3[0].spines.left.set_position('zero')
    
    irm_gweis_without_zeroes = [round(t.base_fee_per_gas_price_difference / 1_000_000_000) for t in irm_transactions if t.base_fee_per_gas_price_difference != 0]
    axs3[1].hist(irm_gweis_without_zeroes, 50)
    axs3[1].spines.left.set_position('zero')
    
    zscore_gweis_without_zeroes = [round(t.base_fee_per_gas_price_difference / 1_000_000_000) for t in zscore_transactions if t.base_fee_per_gas_price_difference != 0]
    axs3[2].hist(zscore_gweis_without_zeroes, 50)
    axs3[2].spines.left.set_position('zero')
    
    # Transaction gas difference without zeroes cumulative
    
    axs4[0].hist(gweis_without_zeroes, 50, density=True, cumulative=True)
    axs4[0].spines.left.set_position('zero')
    
    axs4[1].hist(irm_gweis_without_zeroes, 50, density=True, cumulative=True)
    axs4[1].spines.left.set_position('zero')
    
    axs4[2].hist(zscore_gweis_without_zeroes, 50, density=True, cumulative=True)
    axs4[2].spines.left.set_position('zero')
    
    plt.show()


def removeOutliersIRM(transactions, outlierConstant):
    """ remove outliers using interquartile range method
    https://www.statology.org/remove-outliers-python/
    https://gist.github.com/vishalkuo/f4aec300cf6252ed28d3 
    """
    a = np.array(transactions)
    times = [round(t.tx_initiation_to_execution_time_sec / 60, 2) for t in transactions]
    b = np.array(times)
    
    upper_quartile = np.percentile(b, 75)
    lower_quartile = np.percentile(b, 25)
    IQR = (upper_quartile - lower_quartile) * outlierConstant
    quartileSet = (lower_quartile - IQR, upper_quartile + IQR)
    result = a[np.where((b >= quartileSet[0]) & (b <= quartileSet[1]))]
    return result.tolist()


def removeOutliersZScore(transactions):
    """ remove outliers using Z-score method
    https://www.statology.org/remove-outliers-python/
    """
    a = np.array(transactions)
    times = [round(t.tx_initiation_to_execution_time_sec / 60, 2) for t in transactions]
    b = np.array(times)
    
    z = np.abs(stats.zscore(b))
    result = a[np.where(z < 3)]
    return result.tolist()


if __name__ == '__main__':
    main()
