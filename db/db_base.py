from mysql.connector import connect, Error
import os
from dotenv import load_dotenv

from utils import dict_to_list

load_dotenv()

class DB:
    DB_HOST = os.getenv('DBSQL_HOST')
    DB_USER = os.getenv('DBSQL_USER')
    DB_PASSWORD = os.getenv('DBSQL_PASSWORD')
    DB = os.getenv('DBSQL')

    def __init__(self, table, validation_fields=[], host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB):
        self.host = host
        self.db = db
        self.user = user
        self.password = password
        self.table = table
        self.validation_fields = validation_fields
        self.print_name = ''
        self.is_valid = False
        self.count = 0

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
                        if type(records[0]) == list:
                            self.execute_many(connection, cursor, query, records)
                        else:
                            print("To use execute_many, records must be a list of lists")
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

    # def is_in_db(self, item):
    #     for record in self.all_records():
    #         if record['bill_id'] == item[0]:
    #             if record['due_date'] == item[4]:
    #                 return True
    #     return False

    def is_in_db(self, item):   # takes 2 dict
        valid_fields = []
        if self.all_records() == []:
            return False
        for record in self.all_records():
            for field in self.validation_fields:
                if record[field] == item[field]:
                    valid_fields.append(item[field])
        return len(set(valid_fields)) == len(self.validation_fields)

    def compare_fields_from_db(self, pdf_fields):
        pdf_fields.append('id')
        db_fields = DB(table=self.table)
        different_fields = list(set(pdf_fields) ^ set(db_fields.fields()))
        if different_fields != []:
            print(f"[MySQL] Fields from TABLE '{self.table}' and class '{type(self)}' do not match: missing '{', '.join(different_fields)}'")
        return different_fields

    # def print_message(self, item, type):
    #     if type == 'insert':
    #         pass
    #     elif type == 'in_db':
    #         pass

    def print_message(self, item, type):
        msg = ''
        # print(item)
        for field in self.validation_fields:
            msg += f" {field.upper()}: [{item[field]}]"
        if type == 'insert':
            msg = f"[MySQL] Entry added for {self.print_name}:{msg}"
        elif type == 'in_db':
            msg = f"[MySQL] {self.print_name}:{msg} is already in DB"
        print(msg)

    def insert(self, fields, query, items, force=False):
        # print(items)
        if self.compare_fields_from_db(fields) == []:     # checks that db fields are the same as inserting fields
            # if force:
            #     self.execute_insert_many(query, item)
            #     if self.records_match(self.fetch_last(), item):
            #         self.print_message(item, type='insert')
            #         self.count += 1
            #     else:
            #         print(f"[MySQL] Something failed inserting record {item}")
            if isinstance(items, dict):
                if force or not self.is_in_db(items):
                    self.execute_insert_many(query, items)
                    if self.records_match(self.fetch_last(), items):
                        self.print_message(items, type='insert')
                        self.count += 1
                    else:
                        print(f"[MySQL] Something failed inserting record {items}")
                else:
                    self.print_message(items, type='in_db')
            elif isinstance(items, list) or force:
                # print(items)
                for item in items:
                    if force or not self.is_in_db(item):
                        self.execute_insert_many(query, item)
                        if self.records_match(self.fetch_last(), item):
                            self.print_message(item, type='insert')
                            self.count += 1
                        else:
                            print(f"[MySQL] Something failed inserting record {item}")
                    else:
                        self.print_message(item, type='in_db')
        if self.count > 0:
            print(f"Total additions: {self.count}\n")
        else:
            print(f"No additions performed\n")

    def records_match(self, db_record, inserted_record):  # takes 2 dict / self.validation_fields = list_of_fields
        if db_record is None:
            return False
        if self.validation_fields != []:
            for field in self.validation_fields:
                if db_record[field] != inserted_record[field]:
                    # return False
                    raise ValueError(f"Error inserting value: {inserted_record}")
            else:
                self.is_valid = True
                return True
        print(f"Couldn't verify if inserted record matches because it was not a list")

    # def execute_insert(self, query, items): # fix it
    #     if type(items[0]) is list:
    #         for entry in items:
    #             self.connect('execute', query, entry)

    # def execute_insert_many(self, query, items):
    #     records = []
    #     if type(items[0]) is list:
    #         for entry in items:
    #             records.append(entry)
    #             print(entry)
    #     else:
    #         records = [items]   # must be a list for execute_many
    #     self.connect('execute_many', query, records)

    def execute_insert_many(self, query, items):
        records = [dict_to_list(items)]   # convert items to list before inserting when only one record
        # print(records)
        self.connect('execute_many', query, records)
