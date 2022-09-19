import os
from datetime import datetime
from dotenv import load_dotenv

from pdf.pdf_main import PDF
from db.db_main import DBBill, DBCard, Dolar
from file_upload.mega_fs import MegaFile

load_dotenv()

TODAY = datetime.now().date().strftime('%Y-%m-%d')

class Bill:
    def __init__(self, pdf_file: str, mega_obj=MegaFile(file=None), push_to_db=False, upload=False, delete=False):
        self.pdf_file = pdf_file
        print(f"Processing {self.pdf_file}..")
        self.pdf_password = self.get_password()
        self.exchange_rate = Dolar().last_cop_rate()
        self.mega = mega_obj
        self.pdf_content = PDF(self.pdf_file, password=self.pdf_password, exchange_rate=self.exchange_rate, mega_obj=self.mega, date_received=TODAY, upload=upload)
        if push_to_db:
            self.push_to_db()
        if delete:
            self.delete_pdf()

    def get_password(self) -> str:
        card_from_pdf = self.pdf_file.split('_')[-1].replace('.pdf', '')
        card_owner = [card['owner'].split(' ')[0] for card in DBCard().all_cards() if card['number'] == card_from_pdf][0].upper()
        return os.getenv(f'PDF_PASSWORD_{card_owner}')

    def push_to_db(self) -> None:
        if self.pdf_content.is_valid:
            db = DBBill()
            db.push_to_db(self.pdf_content)
            print(f"Finished processing {self.pdf_file}")
        else:
            print("Skipping because there are no operations.")

    # def upload_pdf(self):
    #     mega_file = MegaFile(self.pdf_file)
    #     return mega_file.get_link()

    def delete_pdf(self) -> None:
        if os.path.exists(self.pdf_file):
            os.remove(self.pdf_file)
            print("Cleaning up folder..")
        else:
            print("Cannot remove PDF because the file does not exist")