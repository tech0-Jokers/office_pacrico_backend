import os
from pytz import timezone
from datetime import datetime, timezone, timedelta
import pytz
import logging
from dotenv import load_dotenv

from fastapi import FastAPI, Depends, HTTPException, Response, File, UploadFile, Form, Response, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware

from typing import Optional, List
from pydantic import BaseModel  # Pydanticモデルをインポート
from create_db import Product, IncomingInfo, IncomingProduct

from sqlalchemy import create_engine, Column, Integer, String, select, DECIMAL, ForeignKey, Boolean, DateTime, Date, Text, func, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session ,aliased, relationship

from azure.storage.blob import BlobServiceClient,ContentSettings
from rapidfuzz import fuzz

import uuid

import jwt

from wordcloud import WordCloud
import io
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt

# .env.local ファイルを明示的に指定して環境変数を読み込む
load_dotenv(dotenv_path=".env.local")

# AzureStorageの接続情報
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
if AZURE_STORAGE_CONNECTION_STRING is None:
    raise ValueError("AZURE_STORAGE_CONNECTION_STRING is not set in the environment variables")

AZURE_CONTAINER_NAME = "meitex-sweets-image"

# AzureBlobサービスクライアントの作成
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
blob_container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

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
        "https://office-paclico-user-frontend.vercel.app/shop", #Vercelでデプロイされたユーザー用のフロントエンドのURL
        "https://office-paclico-user-frontend.vercel.app/development", #Vercelでデプロイされたユーザー用のフロントエンドのURL
        "https://office-paclico-user-frontend.vercel.app/shop", #Vercelでデプロイされたユーザー用のフロントエンドのURL
        "https://office-paclico-user-frontend.vercel.app/development", #Vercelでデプロイされたユーザー用のフロントエンドのURL
        "https://tech0-gen-7-step4-studentwebapp-pos-37-bxbfgkg5a7gwa7e9.eastus-01.azurewebsites.net", #Azureでデプロイされたユーザー用のフロントエンドのURL
        "https://tech0-gen-7-step4-studentwebapp-pos-35-cubpd9h4euh3g0d8.eastus-01.azurewebsites.net" #Azureでデプロイされたユーザー用のフロントエンドのURL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#フォントパス
font_path = os.path.join(os.path.dirname(__file__), "fonts", "ipaexg.ttf")

# JWTの設定
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

# 日本時間のタイムゾーンを取得
japan_timezone = pytz.timezone('Asia/Tokyo')
# 現在の日本時間を取得
current_japan_time = datetime.now(japan_timezone)
print(f"Current Japan time: {current_japan_time}")

# ロガーのセットアップ
logger = logging.getLogger("uvicorn.error")

# デバッグ用: DATABASE_URL が読み込まれているか確認
# print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")

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
# logger.info(f"Using database URL: {SQLALCHEMY_DATABASE_URL}")
# データベースURLの全体をログに出力するのではなく、安全な情報のみを出力
logger.info("データベースに接続しました。")

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
    product_id = Column(Integer, primary_key=True, autoincrement=True)
    meitex_product_id = Column(Integer, ForeignKey("MeitexProductMaster.meitex_product_id"))
    independent_product_id = Column(Integer, ForeignKey("IndependentProductMaster.independent_product_id"))

class MeitexProductMaster(Base):
    __tablename__ = 'MeitexProductMaster'
    meitex_product_id = Column(Integer, primary_key=True)
    product_name = Column(String(255))
    product_image_url = Column(String(255))
    product_explanation = Column(String(255))
    product_category_id = Column(Integer)

class IndependentProductMaster(Base):
    __tablename__ = 'IndependentProductMaster'
    independent_product_id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organization.organization_id"))
    product_name = Column(String(255))
    product_image_url = Column(String(255))
    product_explanation = Column(String(255))
    product_category_id = Column(Integer, nullable=True)

class IncomingInformation(Base):
    __tablename__ = "IncomingInformation"
    incoming_id = Column(Integer, primary_key=True, autoincrement=True)
    incoming_date = Column(Date)
    purchase_amount = Column(DECIMAL(10, 2))
    user_id = Column(Integer, ForeignKey("userinformation.user_id"))

class Message(Base):
    __tablename__ = 'message'

    message_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sender_user_id = Column(Integer, ForeignKey('userinformation.user_id'), nullable=False)
    sender_user_name_manual_input = Column(String(255), default=None) 
    receiver_user_id = Column(Integer, ForeignKey('userinformation.user_id'), nullable=False)
    receiver_user_name_manual_input = Column(String(255), default=None)  
    product_id = Column(Integer, ForeignKey('integrated_products.product_id'), default=None)  
    message_content = Column(Text, nullable=True) 
    send_date = Column(DateTime, nullable=False, default=lambda: datetime.now(japan_timezone))  #デフォルトを日本時間に設定
    count_of_likes = Column(Integer, default=0)

     # リレーションを追加
    sender = relationship("UserInformation", foreign_keys=[sender_user_id], lazy="joined")
    receiver = relationship("UserInformation", foreign_keys=[receiver_user_id], lazy="joined")

class UserInformation(Base):
    __tablename__ = "userinformation"
    user_id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(255))
    ambassador_flag = Column(Boolean, default=False)
    organization_id = Column(Integer, ForeignKey("organization.organization_id"), nullable=False)
    email_address = Column(String(255))
    password = Column(String(255))
    github_user_name = Column(String(255), unique=True, nullable=True)
    github_id = Column(String(255), unique=True, nullable=True)

class Incoming_Products(Base):
    __tablename__ = "Incoming_Products"
    product_id = Column(Integer, ForeignKey("Inventory_products.product_id"), primary_key=True)
    incoming_id = Column(Integer, ForeignKey("IncomingInformation.incoming_id"), primary_key=True)
    incoming_quantity = Column(Integer)

class Organization(Base):
    __tablename__ = "organization"
    organization_id = Column(Integer, primary_key=True, index=True)  # 組織ID
    organization_name = Column(String(255), nullable=True)  # 組織名
    qr_generation_token = Column(String(255), nullable=True)  # トークン
    token_expiry_date = Column(DateTime, nullable=True)  # トークン有効期限
    token_status = Column(Boolean, default=True)  # トークン状態（有効/無効）

class ReplyComments(Base):
    __tablename__ = 'reply_comments'
    reply_comment_id = Column(Integer, primary_key=True, index=True)  
    message_id = Column(Integer, ForeignKey('message.message_id'), nullable=False)  
    comment_user_id = Column(Integer, ForeignKey('userinformation.user_id'), nullable=False)  
    comment_user_name_manual_input = Column(String(255), default=None)
    message_content = Column(Text, nullable=True)  
    send_date = Column(DateTime, nullable=False, default=lambda: datetime.now(japan_timezone))  

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

# メッセージモデルの定義
class MessageCreate(BaseModel):
    message_content: str
    sender_user_id: int # 送信者のID
    receiver_user_id: int  # 受信者のID
    sender_user_name_manual_input: str
    receiver_user_name_manual_input: str
    product_id: int  # 商品のID

class ProductResponse(BaseModel):
    product_id: int
    product_name: str
    product_image_url: Optional[str]
    sales_amount: float
    stock_quantity: int

    class Config:
        orm_mode = True  # SQLAlchemy オブジェクトをサポート
        from_attributes = True  # 必要に応じて追加

class ProductResponseForAmbassador(BaseModel):
    product_id: int
    product_name: str
    product_explanation: Optional[str]
    product_image_url: Optional[str]

    class Config:
        orm_mode = True  # SQLAlchemy オブジェクトをサポート
        from_attributes = True  # 必要に応じて追加

class ProductResponseForAmbassadorWithList(BaseModel):
    products: List[ProductResponseForAmbassador]

class UserInformationResponse(BaseModel):
    user_id: int
    user_name: str

    class Config:
        orm_mode = True

class Item(BaseModel):
    product_id: int
    incoming_quantity: int

class IncomingRegisterRequest(BaseModel):
    entryDate: datetime
    purchase_amount: float
    user_id: int
    organization_id: int
    items: List[Item]

class UpdatePriceRequest(BaseModel):
    sales_amount: float

class CommentRequest(BaseModel):
    message_id: int
    comment_user_id: int
    comment_user_name_manual_input: str
    message_content: str

class MessageCountResponse(BaseModel):
    sender_name: str
    message_count: int

class ReceiverMessageCountResponse(BaseModel):
    receiver_name: str
    message_count: int

class SnackRankingResponse(BaseModel):
    product_name: str
    purchase_count: int

# ルートエンドポイント: こんにちはを表示
@app.get("/")
def read_root():
    return {"message": "こんにちはOffice Paclicoだよ!"}

@app.get("/organization/{github_id}")
def get_organization(
    github_id: str,
    github_username: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    指定されたGitHub IDとユーザー名に基づき、organization_idを返す。
    """
    # ステップ1: GitHub IDが既に登録されている場合
    user = db.query(UserInformation).filter(UserInformation.github_id == github_id).first()
    if user:
        return {"organization_id": user.organization_id}

    # ステップ2: GitHubユーザー名が登録されている場合
    if github_username:
        user_with_username = db.query(UserInformation).filter(UserInformation.github_user_name == github_username).first()
        if user_with_username:
            # 初回認証としてGitHub IDを登録
            user_with_username.github_id = github_id
            db.commit()
            return {"organization_id": user_with_username.organization_id}

    # ステップ3: ユーザーが未登録の場合
    return {"organization_id": 404}

#組織IDに応じて在庫情報を返すAPI
@app.get("/products/{organization_id}", response_model=list[ProductResponse], tags=["Product Operations"])
def get_products_by_organization(organization_id: int, db: Session = Depends(get_db)):
    print(organization_id)
    try:
        meitex_products = db.query(
            InventoryProduct.product_id,
            MeitexProductMaster.product_name,
            MeitexProductMaster.product_image_url,
            InventoryProduct.sales_amount,
            InventoryProduct.stock_quantity
        ).join(IntegratedProduct, InventoryProduct.product_id == IntegratedProduct.product_id
        ).join(MeitexProductMaster, IntegratedProduct.meitex_product_id == MeitexProductMaster.meitex_product_id
        ).filter(InventoryProduct.organization_id == organization_id).all()

        independent_products = db.query(
            InventoryProduct.product_id,
            IndependentProductMaster.product_name,
            IndependentProductMaster.product_image_url,
            InventoryProduct.sales_amount,
            InventoryProduct.stock_quantity
        ).join(IntegratedProduct, InventoryProduct.product_id == IntegratedProduct.product_id
        ).join(IndependentProductMaster, IntegratedProduct.independent_product_id == IndependentProductMaster.independent_product_id
        ).filter(InventoryProduct.organization_id == organization_id).all()

        #結合
        all_products = meitex_products + independent_products

        if not all_products:
            print("miss")
            raise HTTPException(status_code=404, detail="No products found for this organization")

        # Pydantic モデルに変換して返す
        return [ProductResponse.from_orm(product) for product in all_products]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#アンバサダー向けに商品情報を返すAPI（meitex商品+独自商品）
@app.get("/api/snacks/", response_model=ProductResponseForAmbassadorWithList)
def get_products_by_organization(organization_id: int, db: Session = Depends(get_db)):
    
    try:
        meitex_products = db.query(
            IntegratedProduct.product_id,
            MeitexProductMaster.product_name,
            MeitexProductMaster.product_explanation,
            MeitexProductMaster.product_image_url
        ).join(MeitexProductMaster, IntegratedProduct.meitex_product_id == MeitexProductMaster.meitex_product_id
        ).all()

        independent_products = db.query(
            IntegratedProduct.product_id,
            IndependentProductMaster.product_name,
            IndependentProductMaster.product_explanation,
            IndependentProductMaster.product_image_url
        ).join(IndependentProductMaster, IntegratedProduct.independent_product_id == IndependentProductMaster.independent_product_id
        ).filter(IndependentProductMaster.organization_id == organization_id).all()

        #結合
        all_products = meitex_products + independent_products

        if not all_products:
            print("miss")
            raise HTTPException(status_code=404, detail="No products found for this organization")

        # Pydantic モデルに変換して返す
        product_list=[ProductResponseForAmbassador.from_orm(product) for product in all_products]
        return {"products": product_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#組織IDに応じて在庫情報を返すAPI
@app.get("/inventory_products/{organization_id}")
def get_inventory_products(organization_id: int, db: Session = Depends(get_db)):
    try:
        # データベースクエリ
        results = (
            db.query(
                InventoryProduct.product_id,
                InventoryProduct.sales_amount,
                InventoryProduct.stock_quantity,
                IndependentProductMaster.product_name.label("independent_product_name"),
                IndependentProductMaster.product_explanation.label("independent_product_explanation"),
                IndependentProductMaster.product_image_url.label("independent_product_image_url"),
                MeitexProductMaster.product_name.label("meitex_product_name"),
                MeitexProductMaster.product_explanation.label("meitex_product_explanation"),
                MeitexProductMaster.product_image_url.label("meitex_product_image_url")
            )
            .join(IntegratedProduct, InventoryProduct.product_id == IntegratedProduct.product_id)
            .outerjoin(IndependentProductMaster, IntegratedProduct.independent_product_id == IndependentProductMaster.independent_product_id)
            .outerjoin(MeitexProductMaster, IntegratedProduct.meitex_product_id == MeitexProductMaster.meitex_product_id)
            .filter(InventoryProduct.organization_id == organization_id)
            .all()
        )

        # レスポンスデータ作成
        response = [
            {
                "product_id": result.product_id,
                "sales_amount": int(result.sales_amount),
                "stock_quantity": result.stock_quantity,
                "product_name": result.independent_product_name or result.meitex_product_name,
                "product_explanation": result.independent_product_explanation or result.meitex_product_explanation,
                "product_image_url": result.independent_product_image_url or result.meitex_product_image_url
            }
            for result in results
        ]

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

        
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
@app.get("/get_product_name", tags=["Product Operations"])
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
@app.post("/add_product/", tags=["Product Operations"])
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

# 新しい商品を商品マスタに追加するエンドポイント（名前とバーコードのみ）
@app.post("/receiving_register")
async def register_incoming_products(
    request: IncomingRegisterRequest,
    db: Session = Depends(get_db)
):
    # entryDate を UTC から JST に変換
    utc_time = request.entryDate
    jst_timezone = pytz.timezone('Asia/Tokyo')
    jst_time = utc_time.astimezone(jst_timezone)

    # トランザクション開始
    try:
        # IncomingInformation にデータを挿入
        incoming_info = IncomingInformation(
            incoming_date=jst_time.date(),
            purchase_amount=request.purchase_amount,
            user_id=request.user_id,  # リクエストからユーザーIDを使用
        )
        db.add(incoming_info)
        db.commit()
        db.refresh(incoming_info)

        # 商品情報の挿入と在庫更新
        for item in request.items:
            # Inventory_products から商品を取得（組織IDも一致するもの）
            inventory_product = db.query(InventoryProduct).filter(
                InventoryProduct.product_id == item.product_id,
                InventoryProduct.organization_id == request.organization_id
            ).first()

            if not inventory_product:
                # 商品が存在しない場合、新規作成
                inventory_product = InventoryProduct(
                    product_id=item.product_id,
                    organization_id=request.organization_id,
                    sales_amount=0,  
                    stock_quantity=item.incoming_quantity  
                )
                db.add(inventory_product)

            else:
                # 在庫数の更新（すでにあれば加算）
                inventory_product.stock_quantity += item.incoming_quantity

            db.commit()  # 在庫の更新を確定

            # Incoming_Products にデータを追加
            incoming_product = Incoming_Products(
                product_id=item.product_id,
                incoming_id=incoming_info.incoming_id,
                incoming_quantity=item.incoming_quantity
            )
            db.add(incoming_product)

        db.commit()  # すべての変更を確定
        return {"message": "商品が正常に登録され、在庫が更新されました"}

    except Exception as e:
        db.rollback()  # すべての変更をロールバック
        raise HTTPException(status_code=500, detail=f"エラーが発生しました: {str(e)}")


# 独自商品を新規で登録するエンドポイント
@app.post("/api/newsnacks/")
async def upload_product(
    organization_id: int = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...)
):
    # 画像のユニークなBlob名を生成
    blob_name = f"{uuid.uuid4()}_{image.filename}"
    blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=blob_name)

    # 画像をAzure Blob Storageにアップロード
    try:
        # Content-Typeを設定
        content_settings = ContentSettings(content_type=image.content_type)

        # Blob Storageにアップロード
        blob_client.upload_blob(image.file, overwrite=True, content_settings=content_settings)

        # アップロードされた画像のURLを生成
        image_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{blob_name}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"画像のアップロードに失敗しました: {str(e)}")

    # データベース操作
    db: Session = SessionLocal()
    try:
        # IndependentProductMaster に新しいレコードを追加
        new_product = IndependentProductMaster(
            organization_id=organization_id,
            product_name=name,
            product_image_url=image_url,
            product_explanation=description,
        )
        db.add(new_product)
        db.commit()
        db.refresh(new_product)

        # IntegratedProduct に新しいレコードを追加
        new_integrated_product = IntegratedProduct(
            independent_product_id=new_product.independent_product_id
        )
        db.add(new_integrated_product)
        db.commit()
        db.refresh(new_integrated_product)

        return {
            "message": "独自商品と統合製品が正常にアップロードされました",
            "independent_product_id": new_product.independent_product_id,
            "product_id": new_integrated_product.product_id,
            "product_name": new_product.product_name
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"データベースへの製品情報の挿入に失敗しました: {str(e)}")
    finally:
        db.close()

#販売価格設定のエンドポイント
@app.put("/inventory_products/{organization_id}/update_price/{product_id}")
def update_price(
    organization_id: int,
    product_id: int,
    request: UpdatePriceRequest,
    db: Session = Depends(get_db)
):
    # 指定された商品を検索
    product = db.query(InventoryProduct).filter_by(
        organization_id=organization_id,
        product_id=product_id
    ).first()

    if not product:
        # 商品が見つからない場合はエラーを返す
        raise HTTPException(status_code=404, detail="Invalid product_id or organization_id")

    # 値段を更新
    product.sales_amount = request.sales_amount
    db.commit()
    db.refresh(product)

    # 成功レスポンス
    return {
        "message": "Price updated successfully",
        "updated_product": {
            "organization_id": organization_id,
            "product_id": product_id,
            "sales_amount": product.sales_amount
        }
    }

#指定された組織IDに紐づくユーザー情報を取得するエンドポイント
@app.get("/get_user_information/", response_model=list[UserInformationResponse], tags=["DateBase"])
def get_user_information(organization_id: int, db: Session = Depends(get_db)):
    try:
        if not isinstance(organization_id, int):
            raise HTTPException(status_code=400, detail="organization_id は整数で指定してください")
        
        user_information = db.query(UserInformation).filter(
            UserInformation.organization_id == organization_id
        ).all()

        if not user_information:
            raise HTTPException(status_code=404, detail="指定された組織にユーザーが見つかりません")
        
        return user_information
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"内部エラーが発生しました: {str(e)}"
        )

#指定された組織IDに紐づくメッセージ情報をすべて取得するエンドポイント
@app.get("/messages/", tags=["Message Operations"])
def get_messages(organization_id: int, db: Session = Depends(get_db)):
    # UserInformationテーブルのエイリアスを作成
    sender_alias = aliased(UserInformation)
    receiver_alias = aliased(UserInformation)
    comment_user_alias = aliased(UserInformation)  # コメントしたユーザー用エイリアス

    # クエリの実行
    messages = (
        db.query(
            Message,
            IntegratedProduct,
            IndependentProductMaster,
            MeitexProductMaster,
            ReplyComments,
            sender_alias.user_name.label("sender_user_name"),
            receiver_alias.user_name.label("receiver_user_name"),
            comment_user_alias.user_name.label("comment_user_name"),  # コメントユーザー名を取得
        )
        .join(sender_alias, Message.sender_user_id == sender_alias.user_id)
        .join(receiver_alias, Message.receiver_user_id == receiver_alias.user_id)
        .join(IntegratedProduct, Message.product_id == IntegratedProduct.product_id)
        .outerjoin(
            IndependentProductMaster,
            IntegratedProduct.independent_product_id == IndependentProductMaster.independent_product_id,
        )
        .outerjoin(
            MeitexProductMaster,
            IntegratedProduct.meitex_product_id == MeitexProductMaster.meitex_product_id,
        )
        .outerjoin(ReplyComments, ReplyComments.message_id == Message.message_id)
        .outerjoin(comment_user_alias, ReplyComments.comment_user_id == comment_user_alias.user_id)
        .filter(sender_alias.organization_id == organization_id)
        .filter(receiver_alias.organization_id == organization_id)
        .order_by(ReplyComments.reply_comment_id.asc())  # reply_comment_idの昇順でソート
        .all()
    )

    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for this organization")

    # メッセージごとのデータを構造化
    result = {}
    for message in messages:
        message_id = message.Message.message_id
        if message_id not in result:
            result[message_id] = {
                "message_id": message.Message.message_id,
                "sender_user_id": message.Message.sender_user_id,
                "sender_user_name": message.sender_user_name,
                "sender_user_name_manual_input": message.Message.sender_user_name_manual_input,  # 手入力の送信者名
                "receiver_user_id": message.Message.receiver_user_id,
                "receiver_user_name": message.receiver_user_name,
                "receiver_user_name_manual_input": message.Message.receiver_user_name_manual_input,  # 手入力の受信者名
                "message_content": message.Message.message_content,
                "product_id": message.Message.product_id,
                "product_name": (
                    message.IndependentProductMaster.product_name
                    if message.IndependentProductMaster
                    else None
                )
                or (
                    message.MeitexProductMaster.product_name
                    if message.MeitexProductMaster
                    else None
                ),
                "product_image_url": (
                    message.IndependentProductMaster.product_image_url
                    if message.IndependentProductMaster
                    else None
                )
                or (
                    message.MeitexProductMaster.product_image_url
                    if message.MeitexProductMaster
                    else None
                ),
                "send_date": message.Message.send_date.isoformat()
                if message.Message.send_date
                else None,
                "reply_comments": [],
                "count_of_likes": message.Message.count_of_likes,
            }

        # コメントを追加
        if message.ReplyComments:
            result[message_id]["reply_comments"].append(
                {
                    "reply_comment_id": message.ReplyComments.reply_comment_id,
                    "comment_user_id": message.ReplyComments.comment_user_id,
                    "comment_user_name": message.comment_user_name,
                    "comment_user_name_manual_input": message.ReplyComments.comment_user_name_manual_input,  # 手入力のコメントユーザー名
                    "message_content": message.ReplyComments.message_content,
                    "send_date": message.ReplyComments.send_date.isoformat()
                    if message.ReplyComments.send_date
                    else None,
                }
            )

    return {"messages": list(result.values())}

#指定された組織IDに紐づくメッセージの回数を取得するエンドポイント
@app.get("/send_messages/count/", tags=["DashBoard"])
def get_messages_count(organization_id: int, db: Session = Depends(get_db)):
    try:
        messages_count = (
            db.query(func.count(Message.message_id))
            .join(UserInformation,
                (Message.sender_user_id == UserInformation.user_id) 
            )
            .filter(UserInformation.organization_id == organization_id)
            .scalar()
        )
        
        return {
            "organization_id": organization_id,
            "total_messages": messages_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"メッセージ数の取得中にエラーが発生しました: {str(e)}"
        )

#メッセージを取得するエンドポイント
@app.get("/get_messages/", tags=["Message Operations"])
def get_messages(sender_user_id: int, receiver_user_id: int, product_id: int, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(
        ((Message.sender_user_id == sender_user_id) & (Message.receiver_user_id == receiver_user_id) & (Message.product_id == product_id)) |
        ((Message.sender_user_id == receiver_user_id) & (Message.receiver_user_id == sender_user_id) & (Message.product_id == product_id))
    ).order_by(Message.send_date.desc()).all()
    
    if not messages:
        return {"message": "No messages found between the specified users."}
    
    return messages

# メッセージのいいね数を増やすエンドポイント
@app.put("/like_message/{message_id}", tags=["Message Operations"])
def like_message(message_id: int, db: Session = Depends(get_db)):
    try:
        # メッセージを取得
        message = db.query(Message).filter(Message.message_id == message_id).first()
        
        # メッセージが存在しない場合のエラーハンドリング
        if not message:
            raise HTTPException(status_code=404, detail="メッセージが見つかりません")
        
        # いいね数を増やす
        message.count_of_likes += 1
        db.commit()
        
        return {"message": "いいね数が増加しました"}
    
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="いいね数の増加中にエラーが発生しました")

# 新しいメッセージを追加するエンドポイント
@app.post("/add_message/", tags=["Message Operations"])
def add_message(message_data: MessageCreate, db: Session = Depends(get_db)):
    print(f"Received message_data: {message_data}")
    print(f"MessageCreate module: {MessageCreate.__module__}")
    print(f"MessageCreate name: {MessageCreate.__name__}")
    try:
        # 新しいメッセージを追加
        new_message = Message(
            message_content=message_data.message_content,  # フィールド名を合わせる
            sender_user_id=message_data.sender_user_id,    # フィールド名を合わせる
            sender_user_name_manual_input=message_data.sender_user_name_manual_input,
            receiver_user_id=message_data.receiver_user_id,
            receiver_user_name_manual_input=message_data.receiver_user_name_manual_input,
            product_id=message_data.product_id,
            send_date=datetime.now(japan_timezone)  # UTCに統一
        )
        print(f"send_date: {new_message.send_date}")

        db.add(new_message)
        db.commit()
        db.refresh(new_message)
        
        logger.info(f"メッセージが追加されました: {new_message.message_id}")
        return {"message": "メッセージが追加されました"}
    
    except IntegrityError as e:
        logger.error(f"Integrity error when adding message: {str(e)}")
        raise HTTPException(status_code=400, detail="メッセージの追加に失敗しました: 外部キーが無効です")
    
    except Exception as e:
        logger.error(f"メッセージ追加時のエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="メッセージを追加できませんでした")

@app.post("/add_comments/", tags=["Message Operations"])
def add_comment(request: CommentRequest, db: Session = Depends(get_db)):
    # 新しいコメントを作成
    new_comment = ReplyComments(
        message_id=request.message_id,
        comment_user_id=request.comment_user_id,
        comment_user_name_manual_input=request.comment_user_name_manual_input,
        message_content=request.message_content,
        send_date=datetime.now(japan_timezone)
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return {"message": "Comment added successfully", "comment": new_comment}


# 画像データを取得するエンドポイント
@app.get("/images/{image_name}", tags=["Image Operations"])
async def get_image(image_name: str):
    """
    AzureBlobから指定された画像データを取得する
    
    Args:
        image_name (str): 取得したい画像ファイル名
    
    Returns:
        Response: 画像データを含むレスポンス
    """
    try:
        # Blobクライアントの取得
        blob_client = blob_container_client.get_blob_client(image_name)
        
        # Blobデータの取得
        blob_data = blob_client.download_blob().readall()  # 修正: readall() -> readall() を readall() に変更
        
        # レスポンスとしてデータを返す
        return Response(content=blob_data, media_type="image/png")
    
    except Exception as e:
        # エラー処理
        print(f"Error retrieving image: {e}")
        return Response(status_code=404)

# Azure Blob Storageの接続文字列
container_name = "your-container"

class UploadImageResponse(BaseModel):
    message: str
    filename: str

# 画像をアップロードするエンドポイント
@app.post("/upload_image", response_model=UploadImageResponse, tags=["Image Operations"])
async def upload_image(file: UploadFile = File(...)):
    blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=file.filename)
    
    # ファイルをBlobにアップロード
    content = await file.read()
    with open(file.filename, "wb") as image:
        image.write(content)
    
    with open(file.filename, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    
    # BlobにアップロードしたファイルのURLを取得
    blob_url = blob_client.url

    os.remove(file.filename)  # ローカルに保存したファイルを削除
    return {"message": "Image uploaded successfully", "filename": file.filename, "url": blob_url}

class PurchaseItem(BaseModel):
    product_id: int
    purchase_quantity: int

class PurchaseRequest(BaseModel):
    organization_id: int
    purchases: List[PurchaseItem]

# 在庫数を更新するエンドポイント
@app.put("/inventory_products/purchase/", tags=["Product Operations"])
def purchase_products(purchase_request: PurchaseRequest, db: Session = Depends(get_db)):
    try:
        organization_id = purchase_request.organization_id
        results = []

        for purchase in purchase_request.purchases:
            # 在庫情報を取得
            inventory_product = (
                db.query(InventoryProduct)
                .filter(
                    InventoryProduct.organization_id == organization_id,
                    InventoryProduct.product_id == purchase.product_id
                )
                .first()
            )

            # 商品が存在しない場合のエラーハンドリング
            if not inventory_product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product with ID {purchase.product_id} not found"
                )

            # 在庫数が不足している場合のエラーハンドリング
            if inventory_product.stock_quantity < purchase.purchase_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for product ID {purchase.product_id}"
                )

            # 在庫数を更新
            inventory_product.stock_quantity -= purchase.purchase_quantity

            # 結果を収集
            results.append({
                "product_id": purchase.product_id,
                "purchased_quantity": purchase.purchase_quantity,
                "remaining_stock": inventory_product.stock_quantity
            })

        # データベースを保存
        db.commit()

        # レスポンス作成
        return {
            "message": "Purchase successful",
            "results": results
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()  # 失敗した場合はロールバック
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

#トークン取得・生成エンドポイント
@app.get("/get_token/{organization_id}", tags=["Token"])
def get_or_generate_token(organization_id: int, db: Session = Depends(get_db)):
    # データベースから該当する組織を検索
    organization = db.query(Organization).filter(Organization.organization_id == organization_id).first()

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    # 現在の日本時間を取得（タイムゾーンあり）
    current_time = datetime.now(japan_timezone)

    # 既存トークンが有効か確認
    if organization.qr_generation_token and organization.token_expiry_date:
        # `organization.token_expiry_date` を日本時間に変換
        expiry_date_jst = organization.token_expiry_date
        if expiry_date_jst.tzinfo is None:  # タイムゾーンがない場合
            expiry_date_jst = expiry_date_jst.replace(tzinfo=japan_timezone)

        # 有効期限と現在時刻を比較
        if expiry_date_jst > current_time:
            return {
                "token": organization.qr_generation_token
            }

    # 新しいトークンを生成
    new_token = jwt.encode(
        {"organization_id": organization_id, "exp": current_time + timedelta(hours=1)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    # 新しい有効期限を日本時間で設定
    new_expiry_date = current_time + timedelta(hours=1)

    # データベースを更新（日本時間で保存）
    organization.qr_generation_token = new_token
    organization.token_expiry_date = new_expiry_date
    organization.token_status = True  # トークン状態を有効に設定
    db.commit()

    #新しいトークンを返す
    return {
        "token": new_token
    }

class ValidateTokenRequest(BaseModel):
    organization_id: int
    qr_generation_token: str

# トークン有効性チェックAPI
@app.post("/validate-token")
@app.post("/validate-token/")
def validate_token(request: ValidateTokenRequest, db: Session = Depends(get_db)):
    # データベースから組織情報を取得
    organization = db.query(Organization).filter(
        Organization.organization_id == request.organization_id,
        Organization.qr_generation_token == request.qr_generation_token
    ).first()

    #レコードが存在しない場合
    if not organization:
        raise HTTPException(status_code=404, detail="Invalid organization ID or token.")

    #トークンの有効期限と状態をチェック
    if not organization.token_status:
        raise HTTPException(status_code=400, detail="Token is inactive.")
    if organization.token_expiry_date:
        token_expiry_date_aware = japan_timezone.localize(organization.token_expiry_date)
        if token_expiry_date_aware < datetime.now(japan_timezone):
            raise HTTPException(status_code=400, detail="Token has expired.")

    #トークンが有効
    return {"status": "valid", "organization_name": organization.organization_name}

@app.get("/api/messages/", tags=["DashBoard"])
def get_latest_messages(organization_id: int, db: Session = Depends(get_db)):
    #最新の3件のメッセージを取得
    messages = (
        db.query(Message)
        .join(UserInformation, Message.sender_user_id == UserInformation.user_id)
        .filter(UserInformation.organization_id == organization_id)
        .order_by(Message.send_date.desc())
        .limit(3)
        .all()
    )

    #結果を整形しつつ格納
    result = [
        {
            "send_date": message.send_date.strftime("%Y-%m-%d %H:%M"),
            "sender_name": message.sender_user_name_manual_input or message.sender.user_name,  # 手動入力を優先
            "receiver_name": message.receiver_user_name_manual_input or message.receiver.user_name,  # 手動入力を優先
            "message_content": message.message_content,
        }
        for message in messages
    ]

    return result

@app.get("/api/messages/send", response_model=List[MessageCountResponse], tags=["DashBoard"])
def get_message_send_count(
    organization_id: int = Query(...), 
    db: Session = Depends(get_db)
):
    try:
        #データベースからメッセージ送信データを取得
        raw_results = (
            db.query(
                Message.sender_user_name_manual_input.label("manual_name"),
                UserInformation.user_name.label("default_name"),
                func.count(Message.message_id).label("message_count")
            )
            .join(UserInformation, Message.sender_user_id == UserInformation.user_id)
            .filter(UserInformation.organization_id == organization_id)
            .group_by(Message.sender_user_name_manual_input, UserInformation.user_name)
            .order_by(desc("message_count"))
            .all()
        )

        #名前ごとにカウントを集約
        name_counts = {}
        for result in raw_results:
            name = result.manual_name or result.default_name  #手動入力名を優先
            count = result.message_count

            #既存の名前に類似している場合はそのグループに追加
            added = False
            for existing_name in name_counts:
                if fuzz.ratio(name, existing_name) > 60:  #類似度の閾値、今は仮で60%で設定
                    name_counts[existing_name] += count
                    added = True
                    break

            if not added:
                name_counts[name] = count

        # 結果を降順にソートしてトップ5を返却
        sorted_results = sorted(
            [
                {"sender_name": name, "message_count": count}
                for name, count in name_counts.items()
            ],
            key=lambda x: x["message_count"],
            reverse=True
        )[:5]

        return sorted_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/messages/receive", response_model=List[ReceiverMessageCountResponse], tags=["DashBoard"])
def get_message_receive_count(
    organization_id: int = Query(...), 
    db: Session = Depends(get_db)
):
    try:
        # データベースからメッセージ受信データを取得
        raw_results = (
            db.query(
                Message.receiver_user_name_manual_input.label("manual_name"),
                UserInformation.user_name.label("default_name"),
                func.count(Message.message_id).label("message_count")
            )
            .join(UserInformation, Message.receiver_user_id == UserInformation.user_id)
            .filter(UserInformation.organization_id == organization_id)
            .group_by(Message.receiver_user_name_manual_input, UserInformation.user_name)
            .order_by(desc("message_count"))
            .all()
        )

        #名前ごとにカウントを集約
        name_counts = {}
        for result in raw_results:
            name = result.manual_name or result.default_name  
            count = result.message_count

            #既存の名前に類似している場合はそのグループに追加
            added = False
            for existing_name in name_counts:
                if fuzz.ratio(name, existing_name) > 60:  
                    name_counts[existing_name] += count
                    added = True
                    break

            if not added:
                name_counts[name] = count

        # 結果を降順にソートしてトップ5を返却
        sorted_results = sorted(
            [
                {"receiver_name": name, "message_count": count}
                for name, count in name_counts.items()
            ],
            key=lambda x: x["message_count"],
            reverse=True
        )[:5]

        return sorted_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#お菓子購入ランキングに関するAPI
@app.get("/api/snacks/ranking", response_model=List[SnackRankingResponse], tags=["DashBoard"])
def get_snack_ranking(
    organization_id: int = Query(...),
    db: Session = Depends(get_db)
):
    try:
        product_counts = (
            db.query(
                Message.product_id,
                func.count(Message.message_id).label("purchase_count")
            )
            .join(UserInformation, Message.sender_user_id == UserInformation.user_id)  # UserInformationからorganization_idを取得
            .filter(UserInformation.organization_id == organization_id)  # organization_idでフィルタ
            .group_by(Message.product_id)
            .order_by(desc("purchase_count"))
            .all()
        )

        #product_idをもとにproduct_nameを特定
        ranking = []
        for product_id, purchase_count in product_counts[:3]:  #トップ3を取得
            product_name = None

            product = (
                db.query(IntegratedProduct, MeitexProductMaster.product_name, IndependentProductMaster.product_name)
                .outerjoin(MeitexProductMaster, IntegratedProduct.meitex_product_id == MeitexProductMaster.meitex_product_id)
                .outerjoin(IndependentProductMaster, IntegratedProduct.independent_product_id == IndependentProductMaster.independent_product_id)
                .filter(IntegratedProduct.product_id == product_id)
                .first()
            )


            if product:
                product_name = product[1] or product[2]  

            if product_name:
                ranking.append({
                    "product_name": product_name,
                    "purchase_count": purchase_count
                })

        return ranking

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/snacks/wordcloud", tags=["DashBoard"])
def get_snack_wordcloud(
    organization_id: int = Query(...),
    db: Session = Depends(get_db)
):
    try:
        # product_id, product_name, message_contentを取得
        product_messages = (
            db.query(
                Message.product_id,
                Message.message_content,
                func.coalesce(MeitexProductMaster.product_name, IndependentProductMaster.product_name).label("product_name")
            )
            .join(UserInformation, Message.sender_user_id == UserInformation.user_id)
            .outerjoin(IntegratedProduct, Message.product_id == IntegratedProduct.product_id)
            .outerjoin(MeitexProductMaster, IntegratedProduct.meitex_product_id == MeitexProductMaster.meitex_product_id)
            .outerjoin(IndependentProductMaster, IntegratedProduct.independent_product_id == IndependentProductMaster.independent_product_id)
            .filter(UserInformation.organization_id == organization_id)
            .all()
        )

        # product_nameごとにmessage_contentを集約
        product_message_map = {}
        for product_id, message_content, product_name in product_messages:
            if product_name not in product_message_map:
                product_message_map[product_name] = []
            product_message_map[product_name].append(message_content)

        return product_message_map

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/snacks/wordcloud/images", tags=["DashBoard"])
def generate_wordclouds(
    organization_id: int = Query(...),
    db: Session = Depends(get_db)
):
    try:
        # データ取得
        product_message_map = get_snack_wordcloud(organization_id, db)

        # データが存在しない場合
        if not product_message_map:
            raise HTTPException(status_code=404, detail="No messages found for this organization_id.")

        # ワードクラウド生成
        wordclouds = {}
        for product_name, messages in product_message_map.items():
            combined_text = " ".join(messages)
            
            # 日本語対応のフォントを指定
            wordcloud = WordCloud(
                width=800,
                height=400,
                background_color="white",
                font_path = font_path
            ).generate(combined_text)
            
            # 画像をメモリに保存
            img_buffer = io.BytesIO()
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation="bilinear")
            plt.axis("off")
            plt.savefig(img_buffer, format="PNG")
            img_buffer.seek(0)

            # 商品名ごとに画像を保存
            wordclouds[product_name] = img_buffer

        # デバッグ用：生成した商品名リスト
        print(f"Generated wordclouds for: {list(wordclouds.keys())}")

        # 一例として最初の商品を返却（フロントエンドでは商品選択ロジックを適用）
        first_product_name = next(iter(wordclouds.keys()))
        return StreamingResponse(wordclouds[first_product_name], media_type="image/png")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# アプリケーションの起動: 環境変数 PORT が指定されていればそれを使用
if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)