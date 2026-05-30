from datetime import datetime
import io
import os
import requests
import urllib3
import pandas as pd
import pymysql
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_data():
    print("取得PM2.5資料中...")
    try:
        api_url = "https://data.moenv.gov.tw/api/v2/aqx_p_02?api_key=846e44e1-8cc5-4893-ad87-c79d2d383706&limit=1000&sort=datacreationdate%20desc&format=JSON"
        resp = requests.get(api_url, verify=False)

        res_json = resp.json()

        # 檢查 API 是否有正確回傳 records
        if "records" not in res_json:
            print(f"API 未回傳 records 欄位，原始回應內容: {res_json}")
            return None

        df = pd.DataFrame(res_json["records"])

        if df.empty:
            print("API 回傳的 records 清單為空")
            return None

        # 【重要】將所有欄位名稱轉為小寫，防止 API 欄位變成大寫 (例如 PM2.5 或 Datacreationdate)
        df.columns = df.columns.str.lower()

        # 如果環境部的欄位叫 'pm2.5'，將其更名為 'pm25' 以符合你的資料庫
        if "pm2.5" in df.columns:
            df = df.rename(columns={"pm2.5": "pm25"})

        # 檢查必備欄位是否存在
        target_cols = ["site", "county", "pm25", "datacreationdate", "itemunit"]
        missing_cols = [col for col in target_cols if col not in df.columns]
        if missing_cols:
            print(
                f"API 缺少必要的欄位: {missing_cols}。當前 API 擁有的欄位有: {list(df.columns)}"
            )
            return None

        # 資料清洗：將 pm25 轉為數字
        df["pm25"] = pd.to_numeric(df["pm25"], errors="coerce")

        # 篩選欄位、去重、去缺失值
        df1 = (
            df[target_cols]
            .drop_duplicates(subset=["site", "datacreationdate"])
            .dropna()
        )

        # 轉換成 list of tuples
        data = [tuple(x) for x in df1.values]
        return data

    except Exception as e:
        # 這裡非常重要！印出真正的錯誤原因，才不會被「API 回傳格式錯誤」遮蔽真相
        print(f"抓取資料發生未知錯誤: {e}")
        import traceback

        traceback.print_exc()
    return None


def insert_data(pm25_data):
    try:
        # 使用與 get_data() 中 target_cols 順序完全一致的佔位符
        sqlstr = """
        INSERT IGNORE INTO data (site, county, pm25, datacreationdate, itemunit) 
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.executemany(sqlstr, pm25_data)
        conn.commit()

        if cursor.rowcount <= 0:
            print("目前無更新資料（資料皆已存在）")
        else:
            print(f"成功更新 {cursor.rowcount} 筆資料")
    except Exception as e:
        print(f"寫入資料庫發生錯誤: {e}")


def open_db():
    try:
        conn = pymysql.connect(
            host=os.environ.get("HOST"),
            port=int(os.environ.get("PORT", 3306)),
            user=os.environ.get("USER"),
            password=os.environ.get("PASSWORD"),
            database=os.environ.get("NAME"),
            ssl={"ca": None},  # TiDB Cloud 通常需要啟用 SSL 連線
            autocommit=False,
        )
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print(f"資料庫連線失敗: {e}")
    return None, None


def create_table():
    try:
        # 建立符合 PM2.5 結構的 data 資料表
        sqlstr = """
        CREATE TABLE IF NOT EXISTS data (
            id INT PRIMARY KEY AUTO_INCREMENT,
            site VARCHAR(50),
            county VARCHAR(20),
            pm25 INT,
            datacreationdate DATETIME,
            itemunit VARCHAR(20),
            UNIQUE KEY uq_site_datacreationdate (site, datacreationdate)
        );
        """
        cursor.execute(sqlstr)
        conn.commit()
        print("資料表檢查/建立完成")
    except Exception as e:
        print(f"建立資料表失敗: {e}")


print("-----------------------------------------")
print(f"運行時間: {datetime.now()}")

conn, cursor = open_db()
if conn:
    print("開啟資料庫成功")
    create_table()
    pm25_list = get_data()
    if pm25_list:
        insert_data(pm25_list)
    else:
        print("目前無新資料可供寫入")
    conn.close()
else:
    print("資料庫開啟失敗！")
