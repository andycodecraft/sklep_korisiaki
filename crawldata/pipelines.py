#pip install mysql-connector-python
import mysql.connector,re,json,html
from mysql.connector import Error
from crawldata.functions import *
from datetime import datetime
class CrawldataPipeline:
    def open_spider(self,spider):
        self.DATABASE_NAME='PARTAO_Product_Data'
        self.HOST='partaodb.cpy6cs0k6e9n.eu-central-1.rds.amazonaws.com'
        self.username='admin'
        self.password='dC3EiEq9QO3G65Ztm3XPsIS3bRb0m5n1Yx295t3Qb'

        # self.DATABASE_NAME='crawler'
        # self.HOST='localhost'
        # self.username='root'
        # self.password='Crawler@2025'

        self.TABLE='A18_sklep_korisiaki'
        # ALTER TABLE A3_hochrather AUTO_INCREMENT = 1
        try:
            self.conn = mysql.connector.connect(host=self.HOST,database=self.DATABASE_NAME,user=self.username,password=self.password,charset='utf8',auth_plugin='mysql_native_password')
            if self.conn.is_connected():
                print('Connected to DB')
                db_Info = self.conn.get_server_info()
                print("Connected to MySQL Server version ", db_Info)
            else:
                print('Not connect to DB')
        except Error as e:
            print("Error while connecting to MySQL", e)
            self.conn=None
    def close_spider(self,spider):
        if self.conn.is_connected():
            self.conn.close()
    def process_item(self, item, spider):
        FIELDS = ['created_at']
        VALUES = ["'" + spider.DATE_CRAWL + "'"]

        for k, v in item.items():
            if v:
                FIELDS.append(k)
                if k in ('reviews'):
                    VALUES.append("'" + json.dumps(v).replace("'", "''").replace("\\n", "\\\\n") + "'")
                elif k in ('qty','price', 'review_number'):
                    VALUES.append(str(v))
                else:
                    VALUES.append("'" + str(v).replace("'", "\'") + "'")
        sql = "INSERT INTO `" + self.TABLE + "` (" + (",".join(FIELDS)) + ") VALUES (" + (",".join(VALUES)) + ") " \
            "ON DUPLICATE KEY UPDATE updated_at='" + spider.DATE_CRAWL + "', "

        update_fields = []
        for k, v in item.items():
            if k != 'original_page_url':
                if v:
                    if k in ('reviews'):
                        update_fields.append(k + "='" + json.dumps(v).replace("'", "''").replace("\\n", "\\\\n") + "'")
                    elif k in ('qty','price', 'review_number'):
                        update_fields.append(k + "=" + str(v))
                    else:
                        update_fields.append(k + "='" + str(v).replace("'", "\'") + "'")

        sql += ", ".join(update_fields)

        try:
            RUNSQL(self.conn, sql)
        except:
            self.conn = mysql.connector.connect(host=self.HOST, database=self.DATABASE_NAME, user=self.username, password=self.password, charset='utf8')
            print(sql)
            RUNSQL(self.conn, sql)

        return item
