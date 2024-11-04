import os
from pytz import timezone
from datetime import datetime
import pytz
import logging
from dotenv import load_dotenv

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel  # Pydanticモデルをインポート
from create_db import Product, IncomingInfo, IncomingProduct

from sqlalchemy import create_engine, Column, Integer, String, select, DECIMAL, ForeignKey

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# FastAPIの作成と初期化
app = FastAPI()

# CORS ミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 開発時のローカルURL
        "http://127.0.0.1:3000", # 開発時のローカルURL
        "https://office-pacrico-frontend.vercel.app",  # VercelでデプロイされたフロントエンドのURL
        "https://office-pacrico-user-frontend.vercel.app", #Vercelでデプロイされたユーザー用のフロントエンドのURL
        "https://office-paclico-user-frontend.vercel.app", #Vercelでデプロイされたユーザー用のフロントエンドのURL
        "https://tech0-gen-7-step4-studentwebapp-pos-37-bxbfgkg5a7gwa7e9.eastus-01.azurewebsites.net", #Azureでデプロイされたユーザー用のフロントエンドのURL
        "https://tech0-gen-7-step4-studentwebapp-pos-35-cubpd9h4euh3g0d8.eastus-01.azurewebsites.net" #Azureでデプロイされたユーザー用のフロントエンドのURL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ロガーのセットアップ
logger = logging.getLogger("uvicorn.error")

# .env.local ファイルを明示的に指定して環境変数を読み込む
load_dotenv(dotenv_path=".env.local")


# デバッグ用: DATABASE_URL が読み込まれているか確認
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")

# データベース接続設定
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # DATABASE_URL が未設定の場合は SQLite を使う
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
else:
    # DATABASE_URL が設定されている場合はその URL を使う
    SQLALCHEMY_DATABASE_URL = DATABASE_URL

# Candy用のデータベースエンジンの作成
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

# デバッグ用: 現在のデータベース接続 URL を表示
logger.info(f"Using database URL: {SQLALCHEMY_DATABASE_URL}")

# セッションの設定
# SQLAlchemyのセッションを作成するためのファクトリ関数を定義します。
# autocommit=False: トランザクションを自動的にコミットしないように設定します。
# autoflush=False: セッションが自動的にフラッシュされないように設定します。
# bind=engine: このセッションが使用するデータベースエンジンを指定します。
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemyのベースクラスを作成します。
# これにより、すべてのモデルクラスがこのベースクラスを継承することになります。
Base = declarative_base()

# データベースのテーブルを作成
Base.metadata.create_all(bind=engine)

# DBセッションを取得する依存関係
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# チョコレートのデータベースを読み込む
CHOCOLATES_DATABASE_URL = "sqlite:///./chocolate_data.db"

# チョコレートのデータベースエンジンの作成
chocolates_engine = create_engine(
    CHOCOLATES_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in CHOCOLATES_DATABASE_URL else {}
)

# チョコレートのデータベースのセッションの設定
chocolates_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=chocolates_engine)


# チョコレートデータベースセッションを取得する関数
def get_chocolates_db():
    db = chocolates_SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 新たなベースクラスの作成
ChocolatesBase = declarative_base()


# チョコレートのデータベースのテーブル定義
class ChocolateDB(ChocolatesBase):
    __tablename__ = "chocolate_data"
    Index = Column(Integer, primary_key=True, index=True)
    Product_Name = Column(String(255), index=True)
    Image_Url = Column(String(255))

# チョコレート用のテーブルを作成
ChocolatesBase.metadata.create_all(bind=chocolates_engine)

# お菓子のテーブル定義
class CandyDB(Base):
    __tablename__ = "candies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)  # VARCHAR(255)
    price = Column(Integer)
    image = Column(String(255))  # VARCHAR(255)
    description = Column(String(500))  # VARCHAR(500)

class InventoryProduct(Base):
    __tablename__ = 'Inventory_products'
    product_id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organization.organization_id"), primary_key=True)
    sales_amount = Column(DECIMAL(10, 2))
    stock_quantity = Column(Integer)

class IntegratedProduct(Base):
    __tablename__ = 'integrated_products'
    product_id = Column(Integer, primary_key=True)
    meitex_product_id = Column(Integer, ForeignKey("MeitexProductMaster.meitex_product_id"))
    independent_product_id = Column(Integer, ForeignKey("IndependentProductMaster.independent_product_id"))

class MeitexProductMaster(Base):
    __tablename__ = 'MeitexProductMaster'
    meitex_product_id = Column(Integer, primary_key=True)
    product_name = Column(String(255))
    product_image_url = Column(String(255))



# お菓子のデータモデル（リクエスト/レスポンス用）
class Candy(BaseModel):
    id: int
    name: str
    price: int
    image: str
    description: str

# Pydanticモデルの定義
class ProductCreate(BaseModel):
    barcode: str
    name: str

class IncomingRegisterRequest(BaseModel):
    price: float
    items: list
    entryDate: datetime

class ProductResponse(BaseModel):
    product_id: int
    product_name: str
    product_image_url: str
    sales_amount: float
    stock_quantity: int

    class Config:
        orm_mode = True  # SQLAlchemy オブジェクトをサポート
        from_attributes = True  # 必要に応じて追加

# ルートエンドポイント: こんにちはを表示
@app.get("/")
def read_root():
    return {"message": "こんにちはOffice Paclicoだよ!"}

@app.get("/products/{organization_id}", response_model=list[ProductResponse])
def get_products_by_organization(organization_id: int, db: Session = Depends(get_db)):
    print(organization_id)
    try:
        products = db.query(
            InventoryProduct.product_id,
            MeitexProductMaster.product_name,
            MeitexProductMaster.product_image_url,
            InventoryProduct.sales_amount,
            InventoryProduct.stock_quantity
        ).join(IntegratedProduct, InventoryProduct.product_id == IntegratedProduct.product_id
        ).join(MeitexProductMaster, IntegratedProduct.meitex_product_id == MeitexProductMaster.meitex_product_id
        ).filter(InventoryProduct.organization_id == organization_id).all()

        if not products:
            print("miss")
            raise HTTPException(status_code=404, detail="No products found for this organization")

        # Pydantic モデルに変換して返す
        return [ProductResponse.from_orm(product) for product in products]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# お菓子データを取得するエンドポイント（Candy用）
@app.get("/candies", response_model=list[Candy])
def get_candies(db: Session = Depends(get_db)):
    return db.query(CandyDB).all()

# お菓子データをIDで取得するエンドポイント
@app.get("/candies/{candy_id}", response_model=Candy)
def get_candy(candy_id: int, db: Session = Depends(get_db)):
    candy = db.query(CandyDB).filter(CandyDB.id == candy_id).first()
    if not candy:
        raise HTTPException(status_code=404, detail="お菓子が見つかりません")
    return candy

# チョコレートデータを取得するエンドポイント
@app.get("/chocolates")
def get_chocolates(db: Session = Depends(get_chocolates_db)):
    chocolates = db.query(ChocolateDB).limit(6).all()
    return chocolates

# チョコレートデータを取得するエンドポイント
@app.get("/chocolates/{chocolate_id}")
def get_chocolate(chocolate_id: int, db: Session = Depends(get_chocolates_db)):
    try:
        chocolate = db.query(ChocolateDB).filter(ChocolateDB.Index == chocolate_id).first()
        if not chocolate:
            raise HTTPException(status_code=404, detail="チョコレートが見つかりません")
        return chocolate
    except Exception as e:
        logger.error(f"チョコレートデータ取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail="サーバー内部エラー")

# バーコードから商品名を取得するエンドポイント
@app.get("/get_product_name")
def get_product_name(barcode: str, db: Session = Depends(get_db)):
    try:
        # バーコードに基づいて商品を検索
        product = db.execute(select(Product).where(Product.barcode_number == barcode)).scalars().first()
        if product:
            return {"product_name": product.product_name}
        else:
            raise HTTPException(status_code=404, detail="商品が見つかりません")
    except Exception as e:
        logger.error(f"商品検索時のエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="サーバー内部エラー")

# 新しい商品を商品マスタに追加するエンドポイント（名前とバーコードのみ）
@app.post("/add_product/")
def add_product(product: ProductCreate, db: Session = Depends(get_db)):
    print(product.barcode)
    print(product.name)
    try:
        # 商品がすでに存在するか確認
        existing_product = db.execute(select(Product).where(Product.barcode_number == product.barcode)).scalars().first()
        if not existing_product:
            # 新しい商品を追加（名前とバーコードのみ）
            new_product = Product(
                barcode_number=product.barcode,
                product_name=product.name
            )
            db.add(new_product)
            db.commit()
            return {"message": "商品が追加されました"}
    except Exception as e:
        logger.error(f"商品追加時のエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="商品を追加できませんでした")

@app.post("/recieving_register")
async def register_incoming_products(request: IncomingRegisterRequest, db: Session = Depends(get_db)):
    # 送信された entryDate を UTC から JST に変換
    utc_time = request.entryDate  # entryDate は UTC と仮定
    jst_timezone = pytz.timezone('Asia/Tokyo')
    
    # UTC を日本時間に変換
    jst_time = utc_time.astimezone(jst_timezone)

    # 入庫情報を挿入
    incoming_info = IncomingInfo(
        incoming_date=jst_time,  # 日本時間に変換した日時を使う
        purchase_amount=request.price,
        user_id=2  #仮
    )
    db.add(incoming_info)
    db.commit()
    db.refresh(incoming_info)

    # 商品情報の挿入
    for item in request.items:
        product = db.query(Product).filter(Product.product_name == item["name"]).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"商品 {item['name']} が見つかりません")
        
        incoming_product = IncomingProduct(
            product_id=product.product_id,
            incoming_id=incoming_info.incoming_id,
            incoming_quantity=item["quantity"]
        )
        db.add(incoming_product)

    db.commit()
    return {"message": "商品が正常に登録されました"}

# アプリケーションの起動: 環境変数 PORT が指定されていればそれを使用
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))  # 環境変数 PORT があればそれを使用し、なければデフォルトで8000を使用
    app.run(host="0.0.0.0", port=port)