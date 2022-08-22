import os
from datetime import datetime
from dotenv import load_dotenv

from pdf.pdf_main import PDF
from db.db_main import DBBill, DBCard
from compare.compare import Compare

load_dotenv()

TODAY = datetime.now().date().strftime('%Y-%m-%d')

class Bill:
    def __init__(self, pdf_file, push_to_db=False):
        self.pdf_file = pdf_file
        print(f"Processing {self.pdf_file}..")
        self.pdf_password = self.get_password()
        self.pdf_content = PDF(self.pdf_file, password=self.pdf_password, date_received=TODAY, upload=True) # remove upload and use method
        if push_to_db:
            self.push_to_db()
            self.delete_pdf()

    def get_password(self):
        card_from_pdf = self.pdf_file.split('_')[-1].replace('.pdf', '')
        card_owner = [card['owner'].split(' ')[0] for card in DBCard().all_cards() if card['number'] == card_from_pdf][0].upper()
        return os.getenv(f'PDF_PASSWORD_{card_owner}')

    def push_to_db(self):
        if self.pdf_content.is_valid:
            db = DBBill()
            # TODO: compare pdf to period operations (try comparing after db_push) # this doesn't work
            comparison = Compare(self.pdf_content)
            if len(comparison.unmatched) != 0:
                self.pdf_content.has_inconsistency = True
                self.pdf_content.bill_db_formatted['has_inconsistency'] = True
            for index, op in enumerate(self.pdf_content.operations):
                if op in comparison.matched:
                    self.pdf_content.operations[index]['is_matched'] = True
                    self.pdf_content.ops_db_formatted[index]['is_matched'] = True
                    # print(f"Matched to DB: {op}")

            # print(self.pdf_content.operations) #temp #TODO: this is TRUE

            db.push_to_db(self.pdf_content)
            print(f"Finished processing {self.pdf_file}")
        else:
            print("Skipping because there are no operations.")

    # def upload_pdf(self):
    #     mega_file = MegaFile(self.pdf_file)
    #     return mega_file.get_link()

    def delete_pdf(self):
        if os.path.exists(self.pdf_file):
            os.remove(self.pdf_file)
            print("Cleaning up folder..")
        else:
            print("Cannot remove PDF because the file does not exist")