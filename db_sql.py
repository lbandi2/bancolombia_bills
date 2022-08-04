from mysql.connector import connect, Error
import os
from dotenv import load_dotenv

from utils import string_to_datetime, last_pdf

load_dotenv()

class DB:
    DB_HOST = os.getenv('DBSQL_HOST')
    DB_USER = os.getenv('DBSQL_USER')
    DB_PASSWORD = os.getenv('DBSQL_PASSWORD')
    DB = os.getenv('DBSQL')

    def __init__(self, table, host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB):
        self.host = host
        self.db = db
        self.user = user
        self.password = password
        self.table = table
        self.in_db = False
        # self.connect()

    def connect(self, db_action='fetch', query='', records=[], dictionary=True):

        config = {
            'user': self.DB_USER,
            'password': self.DB_PASSWORD,
            'host': self.DB_HOST,
            'database': self.DB,
            'raise_on_warnings': True
            }
        try:
            with connect(**config) as connection:
                with connection.cursor(dictionary=dictionary) as cursor:
                    if db_action == 'fetch':
                        return self.fetch(cursor, query)
                    elif db_action == 'execute':
                        self.execute(connection, cursor, query, records)
                    elif db_action == 'execute_many':
                        self.execute_many(connection, cursor, query, records)
        except Error as e:
            print(e)

    def fetch(self, cursor, query):
        cursor.execute(query)
        result = cursor.fetchall()
        return result

    def execute(self, connection, cursor, query, records):
        cursor.execute(query)
        connection.commit()

    def execute_many(self, connection, cursor, query, records):
        cursor.executemany(query, records)
        connection.commit()

    def all_records(self):
        query = f"SELECT * FROM {self.table}"
        records = self.connect('fetch', query)
        return records

    def fetch_last(self):
        query = f"SELECT * FROM {self.table} ORDER BY id DESC LIMIT 1"
        records = self.connect('fetch', query)
        if records != []:
            return records[0]
        return None

    def fields(self):
        query = f"SELECT `COLUMN_NAME` FROM `INFORMATION_SCHEMA`.`COLUMNS` WHERE `TABLE_SCHEMA`='{self.db}' AND `TABLE_NAME`='{self.table}'"
        records = self.connect('fetch', query, dictionary=False)
        return list(sum(records, ()))

    def update_category(self, item, category):
        query = f"UPDATE {self.table} SET category = '{category}' WHERE id = {item[0]}"
        self.connect('execute', query)

    def find_date(self, date):
        query = f"SELECT * FROM {self.table} WHERE datetime LIKE '{date}%'"
        records = self.connect('fetch', query)
        return records

    def is_in_db(self, item):
        for record in self.all_records():
            if record['bill_id'] == item[0]:
                if record['due_date'] == item[4]:
                    return True
        return False

    def compare_fields_from_db(self, pdf_object):
        pdf_fields = pdf_object
        pdf_fields.append('id')
        db_fields = DB(table=self.table)
        different_fields = list(set(pdf_fields) ^ set(db_fields.fields()))
        if different_fields != []:
            print(f"[MySQL] Fields from TABLE '{self.table}' and PDF object do not match: missing '{', '.join(different_fields)}'")
        return different_fields

    def insert(self, fields, query, item, force=False):
        print("item is list", type(item[0]))
        if self.compare_fields_from_db(fields) == []:     # checks that db fields are the same as inserting fields
            if force:
                print(f"[MySQL] Added a bunch of entries")
                self.execute_insert_many(query, item)
            elif not self.is_in_db(item):
                self.execute_insert_many(query, item)
                if self.records_match(self.fetch_last(), item):
                    print(f"[MySQL] Entry for Extracto: {item[0]} due_date: {item[4]} added")
                    self.in_db = True
                else:
                    print(f"[MySQL] Something failed inserting record")
            else:
                print(f"[MySQL] Entry for Extracto: {item[0]} due_date: {item[4]} is already in DB")

    def records_match(self, db_record, inserted_record):
        pass

    def execute_insert(self, query, items):
        if type(items[0]) is list:
            for entry in items:
                self.connect('execute', query, entry)

    def execute_insert_many(self, query, items):
        records = []
        if type(items[0]) is list:
            for entry in items:
                records.append(entry)
                print(entry)
        else:
            records = [items]   # must be a list for execute_many
        self.connect('execute_many', query, records)


class DBCard(DB):
    DB_CARDS = os.getenv('DBSQL_TABLE_CARDS')

    def __init__(self, table=DB_CARDS):
        super().__init__(table)

    def all_cards(self):
        return self.all_records()

    def card_id(self, card_num):
        for item in self.all_cards():
            if item['number'] == card_num:
                return item['id']
        print(f"Card not found with number '{card_num}'")
        return None

    def card_owner(self, card_num):
        for item in self.all_cards():
            if item['number'] == card_num:
                return item['owner'].split(' ')[0].upper()
        print(f"Card not found with number '{card_num}'")
        return None


class DBBillOp(DB):
    DB_BILL_OPS = os.getenv('DBSQL_TABLE_BILL_OPERATIONS')

    def __init__(self, table=DB_BILL_OPS):
        super().__init__(table)
        # self.op_objects = op_objects

    def records_match(self, db_record, inserted_record):
        if db_record is None:
            return True
        elif db_record['authorization'] == inserted_record[2]:
            if db_record['original_value'] == inserted_record[4]:
                return True
        return False



class DBBill(DB):
    DB_BILLS = os.getenv('DBSQL_TABLE_BILLS')
    DB_BILL_OPS = os.getenv('DBSQL_TABLE_BILL_OPERATIONS')

    def __init__(self, file_link='', table=DB_BILLS):
        super().__init__(table)
        self.file_link = file_link
        self.in_db = False

    def push_to_db(self, pdf_object):
        self.push_bill_to_db(pdf_object)
        pushed_bill_id = self.fetch_last()['id']
        if self.in_db:
            self.push_ops_to_db(pdf_object, pushed_bill_id)

    def push_bill_to_db(self, pdf_object, table=DB_BILLS):
        query = f"INSERT INTO {table} \
        ({', '.join(pdf_object.bill_db_fields)}) \
        VALUES ( {', '.join(['%s'] * len(pdf_object.bill_db_fields))} )"

        self.insert(pdf_object.bill_db_fields, query, pdf_object.bill_db_formatted)

    def push_ops_to_db(self, pdf_object, bill_id, table=DB_BILL_OPS):
        query = f"INSERT INTO {table} \
        ({', '.join(pdf_object.ops_db_fields)}) \
        VALUES ( {', '.join(['%s'] * len(pdf_object.ops_db_fields))} )"

        db_ops = DBBillOp()

        for item in pdf_object.ops_db_formatted:
            item.append(bill_id)

        db_ops.insert(pdf_object.ops_db_fields, query, pdf_object.ops_db_formatted)

    def records_match(self, db_record, inserted_record):
        if db_record is None:
            return True
        elif db_record['bill_id'] == inserted_record[0]:
            if db_record['due_date'] == inserted_record[4]:
                return True
        return False

