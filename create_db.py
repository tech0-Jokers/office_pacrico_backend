import os
from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, DATETIME
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

Base = declarative_base()

# 商品マスタ (Product Master)
class Product(Base):
    __tablename__ = '商品マスタ'
    商品id = Column(Integer, primary_key=True, autoincrement=True)
    商品名 = Column(String(255), nullable=False)
    商品カテゴリ = Column(String(255))
    メーカー名 = Column(String(255))
    バーコード番号 = Column(VARCHAR(255))
    商品画像URL = Column(VARCHAR(255))

# 在庫商品 (Inventory Products)
class InventoryProduct(Base):
    __tablename__ = '在庫商品'
    在庫商品id = Column(Integer, primary_key=True, autoincrement=True)
    商品id = Column(Integer, ForeignKey('商品マスタ.商品id'), nullable=False)
    販売価格 = Column(Float)
    在庫数 = Column(Integer)

    product = relationship("Product")

# 入庫情報 (Incoming Information)
class IncomingInfo(Base):
    __tablename__ = '入庫情報'
    入庫id = Column(Integer, primary_key=True, autoincrement=True)
    入庫日 = Column(DATETIME, nullable=False)
    仕入れ金額 = Column(Float)
    ユーザーid = Column(Integer, ForeignKey('ユーザー情報.ユーザーid'))

# 入庫商品 (Incoming Products)
class IncomingProduct(Base):
    __tablename__ = '入庫商品'
    商品_入庫id = Column(Integer, primary_key=True, autoincrement=True)
    商品id = Column(Integer, ForeignKey('商品マスタ.商品id'), nullable=False)
    入庫id = Column(Integer, ForeignKey('入庫情報.入庫id'))
    入庫個数 = Column(Integer)

# 出庫情報 (Outgoing Information)
class OutgoingInfo(Base):
    __tablename__ = '出庫情報'
    出庫id = Column(Integer, primary_key=True, autoincrement=True)
    出庫日 = Column(DATETIME, nullable=False)
    ユーザーid = Column(Integer, ForeignKey('ユーザー情報.ユーザーid'))
    メッセージ = Column(TEXT)

# 出庫商品 (Outgoing Products)
class OutgoingProduct(Base):
    __tablename__ = '出庫商品'
    商品_出庫id = Column(Integer, primary_key=True, autoincrement=True)
    商品id = Column(Integer, ForeignKey('商品マスタ.商品id'), nullable=False)
    出庫id = Column(Integer, ForeignKey('出庫情報.出庫id'))
    出庫個数 = Column(Integer)
    出庫価格 = Column(Float)

# ユーザー情報 (User Information)
class UserInfo(Base):
    __tablename__ = 'ユーザー情報'
    ユーザーid = Column(Integer, primary_key=True, autoincrement=True)
    ユーザー名 = Column(String(255), nullable=False)
    アンバサダーフラグ = Column(Integer)  # 1はアンバサダー、0はそうではない

# チャット (Chat)
class Chat(Base):
    __tablename__ = 'チャット'
    チャットid = Column(Integer, primary_key=True, autoincrement=True)
    ユーザーid = Column(Integer, ForeignKey('ユーザー情報.ユーザーid'), nullable=False)
    チャットメッセージ = Column(TEXT)
    送信日時 = Column(DATETIME)

# MySQLへの接続
def create_db():
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL, echo=True)
    Base.metadata.create_all(engine)

create_db()