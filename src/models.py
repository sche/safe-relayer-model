from sqlalchemy import Column, ForeignKey, Integer, DateTime, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from database import database as db
import requests
from dotenv import dotenv_values
from web3 import Web3
from datetime import datetime, timedelta
import time


Base = declarative_base()
config = dotenv_values(".env")
w3 = Web3(Web3.HTTPProvider(config['INFURA_MAINNET']))
AVARAGE_BLOCK_TIME = timedelta(seconds=13)


def parse_date(date_string):
    try:
        return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)
    except Exception:
        return datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%f%z').replace(tzinfo=None)


class Block(Base):
    __tablename__ = 'blocks'

    number = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    base_fee_per_gas = Column(Integer, nullable=False)
    gas_used = Column(Integer, nullable=False)

    def __repr__(self):
        return "<Block(number='%s', date='%s', base_fee_per_gas='%s', gas_used='%s')>" \
            % (self.number, self.date, self.base_fee_per_gas, self.gas_used)

    @staticmethod
    def by(number):
        return db.session.query(Block).filter(Block.number == number).first()

    @staticmethod
    def create(number, date, base_fee_per_gas, gas_used):
        block = Block(number=number,
                      date=date,
                      base_fee_per_gas=base_fee_per_gas,
                      gas_used=gas_used)
        db.session.add(block)
        db.session.commit()
        return block

    @staticmethod
    def get_block(number):
        attempts = 0
        b = Block.by(number)
        while b is None and attempts < 5:
            b = Block.__index_block(number)
            if attempts > 0:
                time.sleep(3)
            attempts += 1
        return b

    @staticmethod
    def __index_block(number):
        block = w3.eth.get_block(number)
        if block.number is not None:
            print("Indexed block #{}".format(block.number))
            return Block.create(number=number,
                                date=datetime.utcfromtimestamp(
                                    block.timestamp),
                                base_fee_per_gas=block.baseFeePerGas,
                                gas_used=block.gasUsed)
        else:
            return None


class SafeTx(Base):
    __tablename__ = 'transactions'

    tx_hash = Column(String, primary_key=True)
    block_number = Column(Integer, nullable=False)
    tx_initiation_to_execution_time_sec = Column(Integer, nullable=False)
    base_fee_per_gas_price_difference = Column(Float, nullable=False)
    actual_fee_per_gas_price_difference = Column(Float, nullable=False)

    def __repr__(self):
        return "<SafeTx(tx_hash='%s', block_number='%s', tx_initiation_to_execution_time_sec='%s', base_fee_per_gas_price_difference='%s', actual_fee_per_gas_price_difference='%s')>" \
            % (self.tx_hash, self.block_number, self.tx_initiation_to_execution_time_sec, self.base_fee_per_gas_price_difference, self.actual_fee_per_gas_price_difference)

    @staticmethod
    def all():
        return db.session.query(SafeTx).all()

    @staticmethod
    def __by(tx_hash):
        return db.session.query(SafeTx).filter(SafeTx.tx_hash == tx_hash).first()

    @staticmethod
    def create(tx_hash, block_number, tx_initiation_to_execution_time_sec, base_fee_per_gas_price_difference, actual_fee_per_gas_price_difference):
        tx = SafeTx(tx_hash=tx_hash,
                    block_number=block_number,
                    tx_initiation_to_execution_time_sec=tx_initiation_to_execution_time_sec,
                    base_fee_per_gas_price_difference=base_fee_per_gas_price_difference,
                    actual_fee_per_gas_price_difference=actual_fee_per_gas_price_difference)
        db.session.add(tx)
        db.session.commit()
        return tx

    @staticmethod
    def process_transaction(safe_tx_hash):
        attempts = 0
        t = SafeTx.__by(safe_tx_hash)
        while t is None and attempts < 5:
            t = SafeTx.__index_transaction(safe_tx_hash)
            if attempts > 0:
                time.sleep(3)
            attempts += 1
        return t

    @staticmethod
    def __index_transaction(safe_tx_hash):
        r = requests.get(
            '{}api/v1/multisig-transactions/{}/'.format(config['TX_SERVICE_MAINNET'], safe_tx_hash))
        if r.status_code == 200:
            print("Indexed safe_tx_hash=", safe_tx_hash)
            tx_data = r.json()

            tx_initiation_to_execution_time_sec = SafeTx.__get_tx_initiation_to_execution_time(
                tx_data).total_seconds()

            block_for_first_confirmation = SafeTx.__get_block_for_first_confirmation(
                tx_data)
            block_for_execution = Block.get_block(tx_data['blockNumber'])
            base_fee_per_gas_price_difference = block_for_execution.base_fee_per_gas - \
                block_for_first_confirmation.base_fee_per_gas

            # TODO: find actual price
            # block reward - 2 Ether / gas used = tip gas fee

            tx = SafeTx.create(tx_hash=safe_tx_hash,
                               block_number=tx_data['blockNumber'],
                               tx_initiation_to_execution_time_sec=tx_initiation_to_execution_time_sec,
                               base_fee_per_gas_price_difference=base_fee_per_gas_price_difference,
                               actual_fee_per_gas_price_difference=0)
            return tx
        return None

    @staticmethod
    def __get_block_for_first_confirmation(tx_data):
        init_to_execute_time = SafeTx.__get_tx_initiation_to_execution_time(
            tx_data)
        init_to_execute_blocks = int(
            init_to_execute_time.total_seconds() / AVARAGE_BLOCK_TIME.total_seconds())
        expected_block_number_for_first_confirmation = tx_data['blockNumber'] - \
            init_to_execute_blocks

        search_block = Block.get_block(
            expected_block_number_for_first_confirmation)
        first_confirmation_date = SafeTx.__get_confirmation_dates(tx_data)[0]

        while search_block.date < first_confirmation_date:
            expected_block_number_for_first_confirmation += 1
            search_block = Block.get_block(
                expected_block_number_for_first_confirmation)

        while search_block.date > first_confirmation_date:
            expected_block_number_for_first_confirmation -= 1
            search_block = Block.get_block(
                expected_block_number_for_first_confirmation)

        return search_block

    @staticmethod
    def __get_tx_initiation_to_execution_time(tx_data):
        confirmation_dates = SafeTx.__get_confirmation_dates(tx_data)
        execution_date = parse_date(tx_data['executionDate'])
        return execution_date - confirmation_dates[0]

    @staticmethod
    def __get_confirmation_dates(tx_data):
        return sorted([parse_date(c['submissionDate']) for c in tx_data['confirmations']])


class Model(Base):
    __tablename__ = 'model'

    id = Column(Integer, primary_key=True)
    tx = relationship(SafeTx)
    tx_hash = Column(Integer, ForeignKey('transactions.tx_hash'))
    predicted_price = Column(Integer, nullable=False)
    actual_price = Column(Integer, nullable=False)

    def __repr__(self):
        return "<Model(id='%s', tx='%s', predicted_price='%s', actual_price='%s')>" \
            % (self.id, self.tx, self.predicted_price, self.actual_price)

    @staticmethod
    def by(tx_hash):
        return db.session.query(SafeTx).filter(SafeTx.tx.tx_hash == tx_hash).first()

    @staticmethod
    def create(tx, predicted_price, actual_price):
        model = Model(tx=tx,
                      predicted_price=predicted_price,
                      actual_price=actual_price)
        db.session.add(model)
        db.session.commit()
        return model
