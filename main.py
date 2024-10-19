import os
import logging
from dotenv import load_dotenv


from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel  # Pydanticモデルをインポート
from create_db import Product  # 商品モデルをインポート

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# .env.local ファイルを明示的に指定して環境変数を読み込む
load_dotenv(dotenv_path=".env.local")

# ロガーのセットアップ
logger = logging.getLogger("uvicorn.error")

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

# データベースエンジンの作成
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

# セッションの設定
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# デバッグ用: 現在のデータベース接続 URL を表示
logger.info(f"Using database URL: {SQLALCHEMY_DATABASE_URL}")

# データベースのテーブルを作成
Base.metadata.create_all(bind=engine)

# FastAPIの作成と初期化
app = FastAPI()


# CORS ミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 開発時のローカルURL
        "https://office-pacrico-frontend.vercel.app",  # VercelでデプロイされたフロントエンドのURL
        "https://office-pacrico-user-frontend.vercel.app", #Vercelでデプロイされたユーザー用のフロントエンドのURL
        "https://tech0-gen-7-step4-studentwebapp-pos-37-bxbfgkg5a7gwa7e9.eastus-01.azurewebsites.net" ,#Azureでデプロイされたユーザー用のフロントエンドのURL
        "https://tech0-gen-7-step4-studentwebapp-pos-35-cubpd9h4euh3g0d8.eastus-01.azurewebsites.net" #Azureでデプロイされたユーザー用のフロントエンドのURL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# お菓子のテーブル定義
class CandyDB(Base):
    __tablename__ = "candies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)  # VARCHAR(255)
    price = Column(Integer)
    image = Column(String(255))  # VARCHAR(255)
    description = Column(String(500))  # VARCHAR(500)


# お菓子のデータモデル（リクエスト/レスポンス用）
class Candy(BaseModel):
    id: int
    name: str
    price: int
    image: str
    description: str

# DBセッションを取得する依存関係
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydanticモデルの定義
class ProductCreate(BaseModel):
    barcode: str
    name: str


# エンドポイント: お菓子のデータを取得する
@app.get("/candies", response_model=list[Candy])
def get_candies(db: Session = Depends(get_db)):
    return db.query(CandyDB).all()

# ルートエンドポイント: こんにちはを表示
@app.get("/")
def read_root():
    return {"message": "こんにちは"}

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