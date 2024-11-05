import os
from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, DATETIME
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

Base = declarative_base()

# テーブル定義（省略して以前と同じ内容）
class Product(Base):
    __tablename__ = 'product_master'
    product_id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String(255), nullable=False)
    product_category = Column(String(255))
    manufacturer_name = Column(String(255))
    barcode_number = Column(VARCHAR(255))
    product_image_url = Column(VARCHAR(255))

class InventoryProduct(Base):
    __tablename__ = 'inventory_products'
    inventory_product_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('product_master.product_id'), nullable=False)
    selling_price = Column(Float)
    stock_quantity = Column(Integer)
    product = relationship("Product")

class IncomingInfo(Base):
    __tablename__ = 'incoming_info'
    incoming_id = Column(Integer, primary_key=True, autoincrement=True)
    incoming_date = Column(DATETIME, nullable=False)
    purchase_amount = Column(Float)
    user_id = Column(Integer, ForeignKey('user_info.user_id'))

class IncomingProduct(Base):
    __tablename__ = 'incoming_products'
    incoming_product_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('product_master.product_id'), nullable=False)
    incoming_id = Column(Integer, ForeignKey('incoming_info.incoming_id'))
    incoming_quantity = Column(Integer)

class OutgoingInfo(Base):
    __tablename__ = 'outgoing_info'
    outgoing_id = Column(Integer, primary_key=True, autoincrement=True)
    outgoing_date = Column(DATETIME, nullable=False)
    user_id = Column(Integer, ForeignKey('user_info.user_id'))
    message = Column(TEXT)

class OutgoingProduct(Base):
    __tablename__ = 'outgoing_products'
    outgoing_product_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('product_master.product_id'), nullable=False)
    outgoing_id = Column(Integer, ForeignKey('outgoing_info.outgoing_id'))
    outgoing_quantity = Column(Integer)
    outgoing_price = Column(Float)

class UserInfo(Base):
    __tablename__ = 'user_info'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(255), nullable=False)
    ambassador_flag = Column(Integer)  # 1 for ambassador, 0 for not

class Chat(Base):
    __tablename__ = 'chat'
    chat_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user_info.user_id'), nullable=False)
    chat_message = Column(TEXT)
    sent_datetime = Column(DATETIME)

# MySQLへの接続
def create_db():
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL, echo=True)
    Base.metadata.create_all(engine)

    return engine

# データ追加関数
def add_sample_products(engine):
    Session = sessionmaker(bind=engine)
    session = Session()

   # お菓子データのリストを作成
    products = [
        Product(product_name="チョコレート", product_category="お菓子", manufacturer_name="メーカーA", barcode_number="1234567890123", product_image_url="http://example.com/chocolate.jpg"),
        Product(product_name="キャンディ", product_category="お菓子", manufacturer_name="メーカーB", barcode_number="1234567890124", product_image_url="http://example.com/candy.jpg"),
        Product(product_name="クッキー", product_category="お菓子", manufacturer_name="メーカーC", barcode_number="1234567890125", product_image_url="http://example.com/cookie.jpg"),
        Product(product_name="ポテトチップス", product_category="お菓子", manufacturer_name="メーカーD", barcode_number="1234567890126", product_image_url="http://example.com/chips.jpg"),
        Product(product_name="グミ", product_category="お菓子", manufacturer_name="メーカーE", barcode_number="1234567890127", product_image_url="http://example.com/gummy.jpg"),
        Product(product_name="マカロン", product_category="お菓子", manufacturer_name="メーカーF", barcode_number="1234567890128", product_image_url="http://example.com/macaron.jpg"),
        Product(product_name="ドーナツ", product_category="お菓子", manufacturer_name="メーカーG", barcode_number="1234567890129", product_image_url="http://example.com/donut.jpg"),
        Product(product_name="アイスクリーム", product_category="お菓子", manufacturer_name="メーカーH", barcode_number="1234567890130", product_image_url="http://example.com/icecream.jpg"),
        Product(product_name="餅", product_category="お菓子", manufacturer_name="メーカーI", barcode_number="1234567890131", product_image_url="http://example.com/mochi.jpg"),
        Product(product_name="チュロス", product_category="お菓子", manufacturer_name="メーカーJ", barcode_number="1234567890132", product_image_url="http://example.com/churros.jpg"),
        Product(product_name="フロスピック", product_category="お菓子", manufacturer_name="デンタルプロ", barcode_number="4973227411835", product_image_url="http://example.com/fresh.jpg"),
    ]

    # データをセッションに追加
    session.add_all(products)
    
    # コミットしてデータを保存
    session.commit()
    session.close()

if __name__ == "__main__":
    engine = create_db()
    add_sample_products(engine)