from datetime import datetime
import pdfplumber
from pdfminer import pdfdocument
import math
import re

from utils import utc_to_local, convert_money
from pdf.pdf_page import PDFPage
from db.db_main import DBCard
#TODO: remove password from pdf file
from file_upload.mega_fs import MegaFile

TODAY = datetime.now().date().strftime('%Y-%m-%d')

class PDF:
    def __init__(self, file, password, date_received=TODAY, upload=False):
        self.date_received = date_received
        self.file = file
        self.filename = file.split('/')[-1]
        self.password = password
        self.file_link = 'placeholder'
        self.pages = []
        self.has_inconsistency = False
        self.inconsistencies = []
        self.bill_id = self.get_bill_id()
        self.db_cards = DBCard()
        self.open_file()
        self.card_id = self.get_card_id()
        self.card_owner = self.get_card_owner()
        self.desde = self.pages[0].period[0]
        self.hasta = self.pages[0].period[1]
        self.due_date = self.find_duedate()
        self.num_pages = len(self.pages)
        self.operations = self.get_all_operations()
        self.num_operations = len(self.operations)
        # self.find_min_pay()
        self.is_valid = self.validate()
        if self.validate():
            if upload:
                self.file_link = self.upload_pdf()
        self.bill_db_fields = self.get_bill_db_fields()
        self.ops_db_fields = self.get_ops_db_fields()
        self.bill_db_formatted = self.format_bill_for_db()
        self.ops_db_formatted = self.format_ops_for_db()
    
    def validate(self):
        if self.due_date is None:
            return False
        if len(self.operations) == 0:
            if self.pago_minimo == 0 and self.pago_total == 0:
                return False
        return True

    def upload_pdf(self):
        mega_file = MegaFile(self.file)
        return mega_file.get_link()

    def open_file(self):
        try:
            with pdfplumber.open(f'{self.file}', password=self.password) as pdf:
                for item in pdf.pages:
                    page = PDFPage(item.extract_text())
                    self.pages.append(page)
        except pdfdocument.PDFPasswordIncorrect:
            raise ValueError(f"[PDF] Incorrect password '{self.password}', try again.")

    def get_bill_db_fields(self):
        return [
            'bill_id', 
            'date_received', 
            'start_date', 
            'end_date', 
            'due_date',
            'min_pay', 
            'total_pay', 
            'installments_pay', 
            'file_link', 
            'is_paid', 
            'card_id', 
            'has_inconsistency'
            ]

    def format_bill_for_db(self):
        result = {
                'bill_id': self.bill_id, 
                'date_received': self.date_received,
                'start_date': self.desde, 
                'end_date': self.hasta,
                'due_date': self.due_date,
                'min_pay': self.pago_minimo,
                'total_pay': self.pago_total,
                'installments_pay': self.pendiente_en_cuotas,
                'file_link': self.file_link,
                'is_paid': False,
                'card_id': self.card_id,
                'has_inconsistency': self.has_inconsistency
            }
        return result

    def get_ops_db_fields(self):
        return [
            'date',
            'type',
            'authorization',
            'name', 
            'original_value', 
            'agreed_rate', 
            'billed_rate', 
            'debits_and_credits', 
            'deferred_balance', 
            'dues', 
            'is_matched', 
            'bill_id'  # this id bill_id from db, not object
        ]

    def format_ops_for_db(self):
        result = []
        for item in self.operations:
            result.append(
                {
                    'date': item['fecha'],
                    'type': item['tipo'],
                    'authorization': item['autorizacion'],
                    'name': item['nombre'],
                    'original_value': item['valor_original'],
                    'agreed_rate': item['tasa_pactada'],
                    'billed_rate': item['tasa_ea_facturada'],
                    'debits_and_credits': item['cargos_y_abonos'],
                    'deferred_balance': item['saldo_a_diferir'],
                    'dues': item['cuotas'],
                    # 'is_matched': False
                    'is_matched': item['is_matched']
                    # self.bill_id
                }
            )
        return result

    def get_bill_id(self):
        parts = self.file.split('Extracto')[1].replace('pdf', '').split('_')
        return f"{parts[1]}"

    def get_card_id(self):
        card_num = self.filename.split('_')[-1].replace('.pdf', '')
        return self.db_cards.card_id(card_num)

    def get_card_owner(self):
        card_num = self.filename.split('_')[-1].replace('.pdf', '')
        return self.db_cards.card_owner(card_num)

    def get_all_operations(self):
        ops = []
        for page in self.pages:
            for op in page.operations:
                ops.append(op)
        print(f"[PDF] File '{self.file.split('/')[-1]}' successfully loaded.")
        return ops

    @property
    def tax_operations(self):
        ops = []
        for page in self.pages:
            for op in page.operations:
                if op['tipo'] == 'tax':
                    ops.append(op)
        return ops

    @property
    def expense_operations(self):
        ops = []
        for page in self.pages:
            for op in page.operations:
                if op['tipo'] == 'expense' or op['tipo'] == 'reimbursement':
                    ops.append(op)
        return ops

    @property
    def payment_operations(self):
        ops = []
        for page in self.pages:
            for op in page.operations:
                if op['tipo'] == 'payment':
                    ops.append(op)
        return ops

    @property
    def en_cuotas(self):
        ops = []
        for page in self.pages:
            for op in page.operations:
                if op['cuotas']:
                    if op['cuotas'] != '1/1':
                        ops.append(op)
        return ops

    @property
    def cuotas_pendientes(self):
        ops = []
        for page in self.pages:
            for op in page.operations:
                if op['cuotas']:
                    num1 = op['cuotas'].split('/')[0]
                    num2 = op['cuotas'].split('/')[1]
                    if num1 != num2:
                        ops.append(op)
        return ops

    def find_inconsistency(self, total, reference, message, tolerance=50):
        self.has_inconsistency = True
        for op in self.operations:
            if abs(op['cargos_y_abonos'] - tolerance) > abs(reference - total) > abs(op['cargos_y_abonos'] + tolerance):
                if op not in self.inconsistencies:
                    self.inconsistencies.append(op)
            elif abs(op['cargos_y_abonos'] - tolerance) < abs(reference - total) < abs(op['cargos_y_abonos'] + tolerance):
                if op not in self.inconsistencies:
                    self.inconsistencies.append(op)
        if self.has_inconsistency:
            print(f"[WARNING] Found an inconsistency: {message}")
            for item in self.inconsistencies:
                print(item)

    @property
    def pago_minimo(self):
        total = 0.0
        for op in self.operations:
            if op['tipo'] != 'payment':
                total += op['cargos_y_abonos']
        total = math.ceil(total)
        reference = self.find_min_pay_reference()
        if reference != total:
            message = f"[Min pay] Total: {total} / Reference: {reference}"
            self.find_inconsistency(total, reference, message)
        return reference

    @property
    def pago_total(self):
        total = 0.0
        for op in self.operations:
            if op['tipo'] != 'payment':
                total += op['cargos_y_abonos'] + op['saldo_a_diferir']
        total = math.ceil(total)
        reference = self.find_total_pay_reference()
        if reference != total:
            message = f"[Total pay] Total: {total} / Reference: {reference}"
            self.find_inconsistency(total, reference, message)
        return reference

    @property
    def pendiente_en_cuotas(self):
        total = 0
        for op in self.operations:
            if op['tipo'] == 'expense':
                total += op['saldo_a_diferir']
        return math.ceil(total)

    def find_min_pay_reference(self):
        for page in self.pages:
            for item in page.content.split('\n'):
                if '= Pago mínimo' in item:
                    pago = item.split('= Pago mínimo')[1].strip()
                    if pago != '0.00':
                        return convert_money(pago)
        print("Could not find min_pay reference in PDF")
        return 0

    def find_total_pay_reference(self):
        for page in self.pages:
            for item in page.content.split('\n'):
                if '= Pago mínimo' in item:
                    pago = item.split('= Pago mínimo')[0].replace('= Pagos total', '').strip()
                    if pago != '0.00':
                        return convert_money(pago)
        print("Could not find total_pay reference in PDF")
        return 0

    def find_duedate(self):
        for page in self.pages:
            all_dates = re.findall("\d{2}/\d{2}/\d{4}", page.content)
            all_dates = set(all_dates)
            dates_as_dates = [utc_to_local(datetime.strptime(x, '%d/%m/%Y')) for x in all_dates if x != '00/00/0000']
            if max(dates_as_dates) > self.hasta:
                due_date = utc_to_local(max(dates_as_dates))
                return due_date.date()
        else:
            return None
            # raise ValueError("Couldn't find due date")
