import os  # OSモジュールをインポート（環境変数の操作に使用）
import mysql.connector  # MySQLデータベース接続用モジュールをインポート
from mysql.connector import errorcode  # MySQLエラーコードをインポート
from dotenv import load_dotenv  # .envファイルから環境変数を読み込むためのモジュールをインポート

# .envファイルをロード
load_dotenv()

# ポータルから接続文字列情報を取得
config = {
    'host': 'tech0-gen-7-step4-studentrdb-18.mysql.database.azure.com',  # データベースのホスト名
    'user': 'tech0gen7student',  # データベースのユーザー名
    'password': os.getenv('DB_PASSWORD'),  # 環境変数からパスワードを取得
    'database': 'pos_meitex',  # 使用するデータベース名
    'client_flags': [mysql.connector.ClientFlag.SSL],  # SSL接続を使用するためのフラグ
    'ssl_ca': 'C:\\DigiCertGlobalRootCA.crt.pem'  # SSL証明書ファイルのパス
}

try:
    # 接続の確立
    print("接続開始...")
    conn = mysql.connector.connect(**config)
    print("接続成功")

    cursor = conn.cursor()

    # テーブル作成クエリを適切な順序で配置
    table_creation_queries = [
        """
        CREATE TABLE integrated_products (
            product_id INT PRIMARY KEY,
            meitex_product_id INT,
            independent_product_id INT,
            FOREIGN KEY (meitex_product_id) REFERENCES MeitexProductMaster(meitex_product_id),
            FOREIGN KEY (independent_product_id) REFERENCES IndependentProductMaster(independent_product_id)
        )
        """,
        """
        CREATE TABLE Inventory_products (
            product_id INT,
            organization_id INT,
            sales_amount DECIMAL(10, 2),
            stock_quantity INT,
            PRIMARY KEY (product_id, organization_id),
            FOREIGN KEY (product_id) REFERENCES integrated_products(product_id),
            FOREIGN KEY (organization_id) REFERENCES Organization(organization_id)
        )
        """,
        """
        CREATE TABLE UserInformation (
            user_id INT PRIMARY KEY,
            user_name VARCHAR(255),
            ambassador_flag BOOLEAN,
            organization_id INT,
            FOREIGN KEY (organization_id) REFERENCES Organization(organization_id)
        )
        """,
        """
        CREATE TABLE Message (
            message_id INT PRIMARY KEY,
            sender_user_id INT,
            receiver_user_id INT,
            message_content TEXT,
            product_id INT,
            send_date DATE,
            FOREIGN KEY (sender_user_id) REFERENCES UserInformation(user_id),
            FOREIGN KEY (receiver_user_id) REFERENCES UserInformation(user_id),
            FOREIGN KEY (product_id) REFERENCES integrated_products(product_id)
        )
        """,
        """
        CREATE TABLE Likes (
            message_id INT,
            user_id INT,
            PRIMARY KEY (message_id, user_id),
            FOREIGN KEY (message_id) REFERENCES Message(message_id),
            FOREIGN KEY (user_id) REFERENCES UserInformation(user_id)
        )
        """,
        """
        CREATE TABLE IncomingInformation (
            incoming_id INT PRIMARY KEY,
            incoming_date DATE,
            purchase_amount DECIMAL(10, 2),
            user_id INT,
            FOREIGN KEY (user_id) REFERENCES UserInformation(user_id)
        )
        """,
        """
        CREATE TABLE Incoming_Products (
            product_id INT,
            incoming_id INT,
            incoming_quantity INT,
            PRIMARY KEY (product_id, incoming_id),
            FOREIGN KEY (product_id) REFERENCES Inventory_products(product_id),
            FOREIGN KEY (incoming_id) REFERENCES IncomingInformation(incoming_id)
        )
        """,
        """
        CREATE TABLE OutgoingInformation (
            outgoing_id INT PRIMARY KEY,
            outgoing_date DATE,
            user_id INT,
            FOREIGN KEY (user_id) REFERENCES UserInformation(user_id)
        )
        """,
        """
        CREATE TABLE OutgoingProducts (
            product_id INT,
            outgoing_id INT,
            outgoing_quantity INT,
            price DECIMAL(10, 2),
            PRIMARY KEY (product_id, outgoing_id),
            FOREIGN KEY (product_id) REFERENCES Inventory_products(product_id),
            FOREIGN KEY (outgoing_id) REFERENCES OutgoingInformation(outgoing_id)
        )
        """
    ]

    # クエリの実行
    for query in table_creation_queries:
        cursor.execute(query)
        print(f"テーブル作成完了: {query.splitlines()[1].strip()}")  # 実行したクエリの確認

    conn.commit()
    cursor.close()
    conn.close()
    print("すべてのテーブルが正常に作成されました。")

except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("ユーザー名またはパスワードに問題があります")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("データベースが存在しません")
    else:
        print("エラー:", err)
