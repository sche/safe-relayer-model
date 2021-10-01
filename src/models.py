from sqlalchemy import Column, ForeignKey, Integer, DateTime, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from database import database as db
import requests
from dotenv import dotenv_values
from web3 import Web3
from datetime import datetime, timedelta
import time
from dateutil import tz


Base = declarative_base()
config = dotenv_values(".env")
w3 = Web3(Web3.HTTPProvider(config['INFURA_MAINNET']))


class Block(Base):
    __tablename__ = 'blocks'

    number = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    base_fee_per_gas = Column(Integer, nullable=False)
    gas_used = Column(Integer, nullable=False)
    block_reward = Column(Integer, nullable=True)

    def __repr__(self):
        return "<Block(number='%s', date='%s', base_fee_per_gas='%s', gas_used='%s', block_reward='%s')>" \
            % (self.number, self.date, self.base_fee_per_gas, self.gas_used, self.block_reward)

    @staticmethod
    def by(number):
        return db.session.query(Block).filter(Block.number == number).first()

    @staticmethod
    def create(number, date, base_fee_per_gas, gas_used, block_reward):
        block = Block(number=number,
                      date=date,
                      base_fee_per_gas=base_fee_per_gas,
                      gas_used=gas_used,
                      block_reward=block_reward)
        db.session.add(block)
        db.session.commit()
        return block

    @staticmethod
    def get_block_by_number(number):
        attempts = 0
        b = Block.by(number)
        if b:
            return b

        while b is None and attempts < 5:
            b = Block.__index_block(number)
            if attempts > 0:
                print("[INFO] Failed to get block by number #{}. Retrying...".format(
                    block.number))
                time.sleep(3)
            attempts += 1

        if b is None:
            print("[WARNING] Failed to get block by number %s" % number)

        print("[INFO] Indexed block #{}".format(number))

        return b

    @staticmethod
    def get_block_by_time(block_time):
        attempts = 0
        number = Block.__get_block_number_by_time(block_time)
        while number is None and attempts < 5:
            print(
                "[INFO] Failed to fetch block by timestamp of time %s. Retrying..." % block_time)
            time.sleep(3)
            attempts += 1
            number = Block.__get_block_number_by_time(block_time)

        if number is None:
            print("[WARNING] Failed to get block by time %s" % block_time)
            return None

        return Block.get_block_by_number(int(number))

    @staticmethod
    def __get_block_number_by_time(time):
        # inpurt date format example: '2021-10-01 14:50:03.065392+00' or '2021-10-01 14:12:02+00'
        assert(time[-3:] == '+00')
        try:
            date = datetime.strptime(
                time[:-3], '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=tz.tzutc())
        except Exception:
            date = datetime.strptime(
                time[:-3], '%Y-%m-%d %H:%M:%S').replace(tzinfo=tz.tzutc())

        timestamp = int(datetime.timestamp(date))

        url = "https://api.etherscan.io/api?module=block&action=getblocknobytime&timestamp={}&closest=before&apikey={}".format(
            timestamp, config['ETHERSCAN_API_KEY'])
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()['result']
        else:
            return None

    @staticmethod
    def __index_block(number):
        block = w3.eth.get_block(number)
        block_reward = Block.__get_block_reward(number)
        if block.number is not None:
            return Block.create(number=number,
                                date=datetime.utcfromtimestamp(
                                    block.timestamp),
                                base_fee_per_gas=block.baseFeePerGas,
                                gas_used=block.gasUsed,
                                block_reward=block_reward)
        else:
            return None

    @staticmethod
    def __get_block_reward(number):
        url = "https://api.etherscan.io/api?module=block&action=getblockreward&blockno={}&apikey={}".format(
            number, config['ETHERSCAN_API_KEY'])

        attempts = 0
        r = requests.get(url)
        while r.status_code != 200 and attempts < 5:
            print(
                "[INFO] Failed to get block reward for number %s. Retrying..." % number)
            time.sleep(3)
            attempts += 1
            r = requests.get(url)

        if r.status_code != 200:
            print("[WARNING] Failed to get block reward for number %s" % number)
            return None

        return r.json()['result']['blockReward']


class SafeTx(Base):
    __tablename__ = 'transactions'

    safe_tx_hash = Column(String, primary_key=True)
    block_number = Column(Integer, nullable=False)
    # exectution time minus first confirmation time
    tx_initiation_to_execution_time_sec = Column(Integer, nullable=False)
    # execution block base fee minus first confirmation (previous) block base fee
    execution_to_initiation_base_fee_difference = Column(Float, nullable=False)
    # execution tx fee payed minus first confirmation (previous) block estimated avarage tx fee
    execution_to_initiation_paied_fee_difference = Column(
        Float, nullable=False)
    # execution tx fee payed minus execution tx block estimated avarage tx fee
    execution_fee_to_avarage_fee_difference = Column(Float, nullable=False)

    def __repr__(self):
        return "<SafeTx(safe_tx_hash='%s', block_number='%s', tx_initiation_to_execution_time_sec='%s', execution_to_initiation_base_fee_difference='%s', execution_to_initiation_paied_fee_difference='%s', execution_fee_to_avarage_fee_difference='%s')>" \
            % (self.safe_tx_hash, self.block_number, self.tx_initiation_to_execution_time_sec, self.execution_to_initiation_base_fee_difference, self.execution_to_initiation_paied_fee_difference, self.execution_fee_to_avarage_fee_difference)

    @staticmethod
    def all():
        return db.session.query(SafeTx).all()

    @staticmethod
    def __by(safe_tx_hash):
        return db.session.query(SafeTx).filter(SafeTx.safe_tx_hash == safe_tx_hash).first()

    @staticmethod
    def create(safe_tx_hash,
               block_number,
               tx_initiation_to_execution_time_sec,
               execution_to_initiation_base_fee_difference,
               execution_to_initiation_paied_fee_difference,
               execution_fee_to_avarage_fee_difference):
        tx = SafeTx(safe_tx_hash=safe_tx_hash,
                    block_number=block_number,
                    tx_initiation_to_execution_time_sec=tx_initiation_to_execution_time_sec,
                    execution_to_initiation_base_fee_difference=execution_to_initiation_base_fee_difference,
                    execution_to_initiation_paied_fee_difference=execution_to_initiation_paied_fee_difference,
                    execution_fee_to_avarage_fee_difference=execution_fee_to_avarage_fee_difference)
        db.session.add(tx)
        db.session.commit()
        return tx

    @staticmethod
    def process_transaction(data):
        """
        data: [safe_tx_hash, block_number, created, executed, created_to_executed, eth_tx_hash]
        """
        (safe_tx_hash, block_number, created, executed,
         created_to_executed, eth_tx_hash) = tuple(data)

        block_of_initiation = Block.get_block_by_time(created)
        block_of_execution = Block.get_block_by_number(int(block_number))

        execution_to_initiation_base_fee_difference = block_of_execution.base_fee_per_gas - \
            block_of_initiation.base_fee_per_gas

        # Get block reward
        # Substract 2
        # Devide it by gas used --> reward per block
        # Calculate estimated tx price at the moment of initiation


# class Model(Base):
#     __tablename__ = 'model'

#     id = Column(Integer, primary_key=True)
#     tx = relationship(SafeTx)
#     tx_hash = Column(Integer, ForeignKey('transactions.tx_hash'))
#     predicted_price = Column(Integer, nullable=False)
#     actual_price = Column(Integer, nullable=False)

#     def __repr__(self):
#         return "<Model(id='%s', tx='%s', predicted_price='%s', actual_price='%s')>" \
#             % (self.id, self.tx, self.predicted_price, self.actual_price)

#     @staticmethod
#     def by(tx_hash):
#         return db.session.query(SafeTx).filter(SafeTx.tx.tx_hash == tx_hash).first()

#     @staticmethod
#     def create(tx, predicted_price, actual_price):
#         model = Model(tx=tx,
#                       predicted_price=predicted_price,
#                       actual_price=actual_price)
#         db.session.add(model)
#         db.session.commit()
#         return model
