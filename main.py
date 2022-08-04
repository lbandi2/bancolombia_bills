from datetime import datetime
from utils import make_dir, last_pdf
# from search import Search
from pdf import PDF
from db_sql import DBBill, DBCard
from dotenv import load_dotenv
import os

load_dotenv()

GMAIL_LABEL = os.getenv('GMAIL_LABEL')
# DB_CARDS = os.getenv('DBSQL_TABLE_CARDS')
# DB_BILLS = os.getenv('DBSQL_TABLE_BILLS')
# DB_OPERATIONS = os.getenv('DBSQL_TABLE_BILL_OPERATIONS')
TODAY = datetime.now().date().strftime('%Y-%m-%d')

def main():
    make_dir("creds")
    pdf_file = last_pdf()
    card_from_pdf = pdf_file.split('_')[-1].replace('.pdf', '')
    card_owner = [card['owner'].split(' ')[0] for card in DBCard().all_cards() if card['number'] == card_from_pdf][0].upper()
    password = os.getenv(f'PDF_PASSWORD_{card_owner}')

    if pdf_file is not None:
        pdf = PDF(pdf_file, password=password, date_received=TODAY)
        db = DBBill()
        db.push_to_db(pdf)

    # for item in pdf.operations:
    #     print(item)

if __name__ == '__main__':
    main()
