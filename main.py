import os
from pytz import timezone
from datetime import datetime, timezone
import pytz
import logging
from dotenv import load_dotenv

from fastapi import FastAPI, Depends, HTTPException, Response, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from typing import Optional, List
from pydantic import BaseModel  # Pydanticモデルをインポート
from create_db import Product, IncomingInfo, IncomingProduct

from sqlalchemy import create_engine, Column, Integer, String, select, DECIMAL, ForeignKey, Boolean, DateTime, Date
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from azure.storage.blob import BlobServiceClient


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
        "https://tech0-gen-7-step4-studentwebapp-pos-37-bxbfgkg5a7gwa7e9.eastus-01.azurewebsites.net", #Azureでデプロイされたユーザー用のフロントエンドのURL
        "https://tech0-gen-7-step4-studentwebapp-pos-35-cubpd9h4euh3g0d8.eastus-01.azurewebsites.net" #Azureでデプロイされたユーザー用のフロントエンドのURL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 日本時間のタイムゾーンを取得
japan_timezone = pytz.timezone('Asia/Tokyo')
# 現在の日本時間を取得
current_japan_time = datetime.now(japan_timezone)
print(f"Current Japan time: {current_japan_time}")

# ロガーのセットアップ
logger = logging.getLogger("uvicorn.error")

# .env.local ファイルを明示的に指定して環境変数を読み込む
load_dotenv(dotenv_path=".env.local")


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
    product_id = Column(Integer, primary_key=True)
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
    independent_product_id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("Organization.organization_id"))
    product_name = Column(String(255))
    product_image_url = Column(String(255))
    product_explanation = Column(String(255))
    product_category_id = Column(Integer)

class IncomingInformation(Base):
    __tablename__ = "IncomingInformation"
    incoming_id = Column(Integer, primary_key=True, autoincrement=True)
    incoming_date = Column(Date)
    purchase_amount = Column(DECIMAL(10, 2))
    user_id = Column(Integer, ForeignKey("userinformation.user_id"))

class Message(Base):
    __tablename__ = 'message'
    message_id = Column(Integer, primary_key=True, index=True)
    message_content = Column(String(500), nullable=False)
    sender_user_id = Column(Integer, ForeignKey('userinformation.user_id'), nullable=False)  # ユーザーテーブルがある場合
    receiver_user_id = Column(Integer, ForeignKey('userinformation.user_id'), nullable=False)  # ユーザーテーブルがある場合
    product_id = Column(Integer, ForeignKey('MeitexProductMaster.meitex_product_id'), nullable=False)
    send_date = Column(DateTime, nullable=False, default=lambda: datetime.now(japan_timezone))  # デフォルトを日本時間に設定

class UserInformation(Base):
    __tablename__ = 'userinformation'  
    user_id = Column(Integer, primary_key=True)
    user_name = Column(String(255))
    ambassador_flag = Column(Boolean)
    organization_id = Column(Integer, ForeignKey("organization.organization_id"))

class Incoming_Products(Base):
    __tablename__ = "Incoming_Products"
    product_id = Column(Integer, ForeignKey("Inventory_products.product_id"), primary_key=True)
    incoming_id = Column(Integer, ForeignKey("IncomingInformation.incoming_id"), primary_key=True)
    incoming_quantity = Column(Integer)

class Organization(Base):
    __tablename__ = 'organization'  
    organization_id = Column(Integer, primary_key=True)
    organization_name = Column(String(255))


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

class Item(BaseModel):
    product_id: int
    quantity: int

class IncomingRegisterRequest(BaseModel):
    entryDate: datetime
    price: float
    userId: int
    organizationId: int
    items: List[Item]

# ルートエンドポイント: こんにちはを表示
@app.get("/")
def read_root():
    return {"message": "こんにちはOffice Paclicoだよ!"}

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

#アンバサダー向けに商品情報を返すAPI
@app.get("/api/snacks/", response_model=ProductResponseForAmbassadorWithList)
def get_products_by_organization(organization_id: int, db: Session = Depends(get_db)):
    
    try:
        meitex_products = db.query(
            InventoryProduct.product_id,
            MeitexProductMaster.product_name,
            MeitexProductMaster.product_explanation,
            MeitexProductMaster.product_image_url
        ).join(IntegratedProduct, InventoryProduct.product_id == IntegratedProduct.product_id
        ).join(MeitexProductMaster, IntegratedProduct.meitex_product_id == MeitexProductMaster.meitex_product_id
        ).filter(InventoryProduct.organization_id == organization_id).all()

        independent_products = db.query(
            InventoryProduct.product_id,
            IndependentProductMaster.product_name,
            IndependentProductMaster.product_explanation,
            IndependentProductMaster.product_image_url
        ).join(IntegratedProduct, InventoryProduct.product_id == IntegratedProduct.product_id
        ).join(IndependentProductMaster, IntegratedProduct.independent_product_id == IndependentProductMaster.independent_product_id
        ).filter(InventoryProduct.organization_id == organization_id).all()

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

    # IncomingInformation にデータを挿入
    incoming_info = IncomingInformation(
        incoming_date=jst_time.date(),
        purchase_amount=request.price,
        user_id=request.userId,  # リクエストからユーザーIDを使用
    )
    db.add(incoming_info)
    db.commit()
    db.refresh(incoming_info)
    
    try:
        # 商品情報の挿入と在庫更新
        for item in request.items:
            # Inventory_products から商品を取得（組織IDも一致するもの）
            inventory_product = db.query(InventoryProduct).filter(
                InventoryProduct.product_id == item.product_id,
                InventoryProduct.organization_id == request.organizationId
            ).first()

            if not inventory_product:
                #商品が存在しない場合、新規作成
                inventory_product = InventoryProduct(
                    product_id=item.product_id,
                    organization_id=request.organizationId,
                    sales_amount=0,  
                    stock_quantity=item.quantity  
                )
                db.add(inventory_product)

            else:
                #在庫数の更新（すでにあれば加算）
                inventory_product.stock_quantity += item.quantity

            # Incoming_Products にデータを追加
            incoming_product = Incoming_Products(
                product_id=item.product_id,
                incoming_id=incoming_info.incoming_id,
                incoming_quantity=item.quantity
            )
            db.add(incoming_product)

        db.commit()
        return {"message": "商品が正常に登録され、在庫が更新されました"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"エラーが発生しました: {str(e)}")


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
            receiver_user_id=message_data.receiver_user_id,
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


# AzureStorageの接続情報
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = "meitex-sweets-image"

# AzureBlobサービスクライアントの作成
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
blob_container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

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

# main.pyに追加
@app.get("/test")
def test_endpoint():
    return {"message": "Test endpoint"}


# アプリケーションの起動: 環境変数 PORT が指定されていればそれを使用
if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)