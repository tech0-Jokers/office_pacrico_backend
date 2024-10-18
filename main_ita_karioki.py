import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from create_db import Product  # Productクラスをインポート

# 環境変数の読み込み
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

# FastAPIアプリのインスタンス化
app = FastAPI()

# CORS ミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # 開発時のローカルURL
        "https://office-pacrico-frontend.vercel.app",  # VercelでデプロイされたフロントエンドのURL
        "https://office-pacrico-user-frontend.vercel.app", #Vercelでデプロイされたユーザー用のフロントエンドのURL
        "https://tech0-gen-7-step4-studentwebapp-pos-37-bxbfgkg5a7gwa7e9.eastus-01.azurewebsites.net" ,#Azureでデプロイされたユーザー用のフロントエンドのURL
        "https://tech0-gen-7-step4-studentwebapp-pos-35-cubpd9h4euh3g0d8.eastus-01.azurewebsites.net/" #Azureでデプロイされたユーザー用のフロントエンドのURL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# バーコードから商品名を取得するエンドポイント
@app.get("/get_product_name")
def get_product_name(barcode: str):
    print(barcode)
    session = SessionLocal()
    try:
        print("OK!")
        # バーコードに基づいて商品を検索
        product = session.execute(select(Product).where(Product.barcode_number == barcode)).scalars().first()
        print(product)
        if product:
            return {"product_name": product.product_name}
        else:
            raise HTTPException(status_code=404, detail="商品が見つかりません")
    finally:
        session.close()

# アプリの起動
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
