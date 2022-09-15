import os
from dotenv import load_dotenv

from db.db_base import DB

load_dotenv()

class Dolar(DB):
    DB_DOLAR = os.getenv('DBSQL_TABLE_DOLAR')

    def __init__(self, table=DB_DOLAR):
        super().__init__(table)

    def last_cop_rate(self):
        query = f"SELECT * FROM {self.table} WHERE currency='COP' order by datetime DESC limit 1"
        records = self.connect('fetch', query)
        return records[0]['other']


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


class DBCardOp(DB):
    DB_CARD_OPS = os.getenv('DBSQL_TABLE_CARD_OPERATIONS')
    VALIDATION = ['date', 'entity', 'amount', 'card_id']

    def __init__(self, validation_fields=VALIDATION, table=DB_CARD_OPS):
        super().__init__(table, validation_fields)

    def matching_records(self, desde, hasta, card_id):
        query = f"SELECT * FROM {self.table} WHERE date between '{desde}' and '{hasta}' AND card_id='{card_id}'"
        records = self.connect('fetch', query)
        return records

class DBBillOp(DB):
    DB_BILL_OPS = os.getenv('DBSQL_TABLE_BILL_OPERATIONS')
    VALIDATION = ['date', 'name', 'authorization', 'original_value', 'bill_id', 'dues']

    def __init__(self, validation_fields=VALIDATION, table=DB_BILL_OPS):
        super().__init__(table, validation_fields)
        self.print_name = 'Operation'

    def all_unmatched_records(self):
        query = f"SELECT * FROM {self.table} WHERE op_match_id IS NULL ORDER BY date DESC"
        records = self.connect('fetch', query)
        return records


class DBBill(DB):
    DB_BILLS = os.getenv('DBSQL_TABLE_BILLS')
    DB_BILL_OPS = os.getenv('DBSQL_TABLE_BILL_OPERATIONS')
    VALIDATION = ['bill_id', 'due_date', 'card_id']

    def __init__(self, validation_fields=VALIDATION, table=DB_BILLS):
        super().__init__(table, validation_fields)
        # self.in_db = False
        self.print_name = 'Extracto'

    def push_to_db(self, pdf_object):
        self.push_bill_to_db(pdf_object)
        if self.is_valid:
            pushed_bill_id = self.fetch_last()['id']
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
            item['bill_id'] = bill_id

        db_ops.insert(pdf_object.ops_db_fields, query, pdf_object.ops_db_formatted, force=True)  #TODO: fix the force, remove it

    # def records_match(self, db_record, inserted_record):
    #     if db_record is None:
    #         return True
    #     elif db_record['bill_id'] == inserted_record[0]:
    #         if db_record['due_date'] == inserted_record[4]:
    #             return True
    #     return False

