from dotenv import load_dotenv
import os

from utils import make_dir, list_pdfs
from mail.search_mails import Search
from bill import Bill

load_dotenv()

GMAIL_LABEL = os.getenv('GMAIL_LABEL_BILLS')

def main():
    make_dir("creds")
    make_dir("data")
    Search(GMAIL_LABEL, stop_if_unread=True)
    pdfs = list_pdfs()
    if pdfs is not None:
        for pdf in pdfs:
            Bill(pdf, push_to_db=True, upload=True, delete=True)


if __name__ == '__main__':
    main()
