from sqlalchemy import Column, Integer, String, Float, Time, ForeignKey, Enum
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

from project.exchange_points import *

Base = declarative_base()


class Commission(Base):
    __tablename__ = 'commission'

    id = Column(Integer, primary_key=True)
    exchange_point = Column(Enum(*exchange_points, name='exchange_names'), unique=True, nullable=False)
    tron_commission = Column(Float, nullable=False)
    update_time = Column(Integer, nullable=False)

    wallets = relationship("Wallet", back_populates="exchange")

    def __repr__(self):
        return f"<Exchange(name='{self.exchange_point}', tron_commission='{self.tron_commission}', update_time='{self.update_time}')>"


class Wallet(Base):
    __tablename__ = 'wallets'

    id = Column(Integer, primary_key=True)
    wallet_number = Column(String, nullable=False)
    amount = Column(Float, nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="wallets")
    exchange_id = Column(Integer, ForeignKey('commission.id'), nullable=False)

    exchange = relationship("Commission", back_populates="wallets")

    def __repr__(self):
        return f"<Wallet(wallet_number='{self.wallet_number}', amount='{self.amount}', user_id='{self.user_id}')>"


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    chat_id = Column(Integer)
    nickname = Column(String)
    password = Column(String)

    wallets = relationship("Wallet", back_populates="user", order_by=Wallet.id)

    def __repr__(self):
        return f"<User(name='{self.name}', chat_id='{self.chat_id}', nickname='{self.nickname}')>"


