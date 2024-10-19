import os
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
from pydantic import BaseModel  # Pydanticモデルをインポート
from create_db import Product  # 商品モデルをインポート

# 環境変数の読み込み
load_dotenv()

# ロガーのセットアップ
logger = logging.getLogger("uvicorn.error")

# データベース接続設定
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URLが設定されていません。")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

# FastAPIアプリケーションの作成
app = FastAPI()

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 開発環境のURL
        "https://office-pacrico-frontend.vercel.app",  # Vercelでデプロイされたフロントエンド
        "https://office-pacrico-user-frontend.vercel.app", # ユーザー用フロントエンド
        "https://tech0-gen-7-step4-studentwebapp-pos-37-bxbfgkg5a7gwa7e9.eastus-01.azurewebsites.net",  # Azureデプロイ
        "https://tech0-gen-7-step4-studentwebapp-pos-35-cubpd9h4euh3g0d8.eastus-01.azurewebsites.net"  # Azureデプロイ
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベースセッションの依存性
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

# アプリケーションの起動
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
