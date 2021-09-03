from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from database import database as db


Base = declarative_base()


class Block(Base):
    __tablename__ = 'blocks'

    number = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    baseFeePerGas = Column(Integer, nullable=False)

    def __repr__(self):
        return "<Block(number='%s', date='%s', baseFeePerGas='%s')>" % (self.number, self.date, self.baseFeePerGas)

    @staticmethod
    def by(number):
        return db.session.query(Block).filter(Block.number == number).first()
    
    @staticmethod
    def create(number, date, baseFeePerGas):
        block = Block(number=number, date=date, baseFeePerGas=baseFeePerGas)
        db.session.add(block)
        db.session.commit()
        return block
