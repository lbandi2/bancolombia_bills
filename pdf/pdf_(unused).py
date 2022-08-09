import pdfplumber
from pdfminer import pdfdocument
import re
from datetime import datetime
import math

from utils import is_num, utc_to_local, convert_money, string_to_date
from db.db_main import DBCard

TODAY = datetime.now().date().strftime('%Y-%m-%d')

class PDF:
    def __init__(self, file, password, date_received=TODAY):
        self.date_received = date_received
        self.file = file
        self.filename = file.split('/')[-1]
        self.password = password
        self.pages = []
        self.bill_id = self.get_bill_id()
        self.open_file()
        self.card_id = self.get_card_id()
        self.card_owner = self.get_card_owner()
        self.desde = self.pages[0].period[0]
        self.hasta = self.pages[0].period[1]
        self.due_date = self.find_duedate().date()
        self.num_pages = len(self.pages)
        self.operations = self.get_all_operations()
        self.num_operations = len(self.operations)
        self.bill_db_fields = self.get_bill_db_fields()
        self.ops_db_fields = self.get_ops_db_fields()
        self.bill_db_formatted = self.format_bill_for_db()
        self.ops_db_formatted = self.format_ops_for_db()

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
            ]

    def format_bill_for_db(self):
        result = [
                self.bill_id, 
                self.date_received,
                self.desde, 
                self.hasta,
                self.due_date,
                self.pago_minimo,
                self.pago_total,
                self.pendiente_en_cuotas,
                'no_file',
                False,
                self.card_id
            ]
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
            'bill_id'
        ]

    def format_ops_for_db(self):
        result = []
        for item in self.operations:
            result.append(
                [
                    item['fecha'],
                    item['tipo'],
                    item['autorizacion'],
                    item['nombre'],
                    item['valor_original'],
                    item['tasa_pactada'],
                    item['tasa_ea_facturada'],
                    item['cargos_y_abonos'],
                    item['saldo_a_diferir'],
                    item['cuotas'],
                    False
                    # self.bill_id
                ]
            )
        return result

    def get_bill_id(self):
        parts = self.file.split('Extracto')[1].replace('pdf', '').split('_')
        return f"{parts[1]}"

    def get_card_id(self):
        card_num = self.filename.split('_')[-1].replace('.pdf', '')
        cards = DBCard() 
        return cards.card_id(card_num)

    def get_card_owner(self):
        card_num = self.filename.split('_')[-1].replace('.pdf', '')
        cards = DBCard() 
        return cards.card_owner(card_num)

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
                if op['tipo'] == 'expense':
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

    @property
    def pago_minimo(self):
        total = 0
        for op in self.operations:
            if op['tipo'] == 'expense' or op['tipo'] == 'tax':
                total += op['cargos_y_abonos']
        return math.ceil(total)

    @property
    def pago_total(self):
        total = 0
        for op in self.operations:
            if op['tipo'] == 'expense' or op['tipo'] == 'tax':
                total += op['cargos_y_abonos'] + op['saldo_a_diferir']
        return math.ceil(total)

    @property
    def pendiente_en_cuotas(self):
        total = 0
        for op in self.operations:
            if op['tipo'] == 'expense':
                total += op['saldo_a_diferir']
        return math.ceil(total)

    def find_duedate(self):
        for page in self.pages:
            all_dates = re.findall("\d{2}/\d{2}/\d{4}", page.content)
            all_dates = set(all_dates)
            dates_as_dates = [utc_to_local(datetime.strptime(x, '%d/%m/%Y')) for x in all_dates if x != '00/00/0000']
            if max(dates_as_dates) > self.hasta:
                due_date = utc_to_local(max(dates_as_dates))
                return due_date
        else:
            raise ValueError("Couldn't find due date")

class PDFPage:
    def __init__(self, content):
        self.content = content
        self.cargos_prev = []
        self.period = self.find_period()
        self.operations = self.parse_page()
        self.num_operations = len(self.operations)  # revisar para que solo queden las compras

    def find_period(self):
        for index, item in enumerate(self.content.split('\n')):
            exp = re.findall("\d{2}/\d{2}/\d{4}", item)
            if len(exp) == 2:
                desde = exp[0]
                hasta = exp[1]
                # desde_date = utc_to_local(datetime.strptime(desde, '%d/%m/%Y')).isoformat()
                # hasta_date = utc_to_local(datetime.strptime(hasta, '%d/%m/%Y')).isoformat()
                desde_date = utc_to_local(datetime.strptime(desde, '%d/%m/%Y'))
                hasta_date = utc_to_local(datetime.strptime(hasta, '%d/%m/%Y'))
                return [desde_date, hasta_date]
        else:
            raise ValueError("Couldn't find billable period, missing 'desde' and 'hasta'")

    def fix_authorization(self, line):
        if 'INTERESES CORRIENTES' in line or 'INTERESES MORA' in line or 'GMF JURIDICO' in line:
            line = '000000 ' + line
        return line

    def find_operations(self):      # strategy: find operations starting with (R00000|000000) 11/11/2014
        ops = []
        exp = re.compile(r'(\d{6}|[A-Z]\d{5}) \d{2}/\d{2}/\d{4}') 
        for line in self.content.split('\n'):
            line = self.fix_authorization(line)
            if exp.match(line):
                operation = PDFOperation(line)
                ops.append(operation.values)
        return ops

    def remove_operation(self, lst, op):
        for index, item in enumerate(lst):
            if item['autorizacion'] == op['autorizacion']:
                if item['valor_original'] == op['valor_original']:
                    lst.pop(index)
        return lst

    def check_duplicates(self, operations):
        cargos_prev = []
        lst = []
        for op in operations:
            if op['autorizacion'] == '000000':
                lst.append(op)
            elif op['autorizacion'] not in cargos_prev:
                cargos_prev.append(op['autorizacion'])
                lst.append(op)
            elif op['autorizacion'] in cargos_prev:   # check if duplicate, then remove previous
                self.remove_operation(lst, op)
        return lst

    def parse_page(self):
        all_operations = self.find_operations()
        operations = self.check_duplicates(all_operations)
        return operations

class PDFOperation:
    def __init__(self, line):
        self.original_line = line
        self.line = line
        self.values = {}
        self.get_values()

    def get_values(self):
        self.values['autorizacion'] = self.get_autorizacion()
        self.values['fecha'] = self.get_fecha().date()
        self.values['cuotas'] = self.get_cuotas()
        self.values['tipo'] = self.get_tipo()
        self.values['saldo_a_diferir'] = self.get_last_value()
        self.values['cargos_y_abonos'] = self.get_last_value()
        self.values['tasa_ea_facturada'] = 0.0
        self.values['tasa_pactada'] = 0.0
        if self.values['tipo'] != 'payment' and self.values['tipo'] != 'tax':
            self.values['tasa_ea_facturada'] = self.get_last_value()
            self.values['tasa_pactada'] = self.get_last_value()
        self.values['valor_original'] = self.get_last_value()
        self.values['nombre'] = self.get_nombre()

    def get_autorizacion(self):
        aut = self.line.split(" ")[0]
        self.line = self.line.replace(f'{aut} ', '')
        return aut

    def get_fecha(self):
        exp = re.compile(r'\d{2}/\d{2}/\d{4}')
        for item in self.line.split(" "):
            if exp.match(item):
                self.line = self.line.replace(f'{item} ', '')
                # fecha = datetime.strptime(item, "%d/%m/%Y").isoformat()
                fecha = utc_to_local(datetime.strptime(item, '%d/%m/%Y'))
                return fecha

    def get_nombre(self):
        return self.line.strip()
        # nombre = ''
        # for item in self.line.split(" "):
        #     if not is_num(item):
        #         nombre += f"{item} "
        # else:
        #     self.line = self.line.replace(f'{nombre}', '')
        #     return nombre.strip()

        # words = []
        # for index, x in enumerate(self.line.split(" ")): # this doesn't work
        #     if ',' not in x and '.' not in x:
        #         words.append(index)
        # print(words)
        # nombre = " ".join(self.line.split(" ")[words[0]:words[-1]+1])
        # self.line = self.line.replace(f'{nombre}', '')
        # # print(nombre)
        # return nombre.strip()

    def get_tipo(self):
        num = len(self.line.split(' '))
        if '-' in self.line.split(' ')[-2]:
            return 'payment'
        elif 'INTERESES CORRIENTES' in self.line\
            or 'INTERESES MORA' in self.line\
            or 'GMF JURIDICO' in self.line\
            or 'CUOTA DE MANEJO' in self.line:
            return 'tax'
        else:
            return 'expense'
    
    def get_cuotas(self):
        exp = re.compile(r"(\d{1,2})/(\d{1,2})$")
        for item in self.line.split(" "):
            if exp.match(item):
                self.line = self.line.replace(f' {item}', '')
                return item
        return '0'
    
    def get_last_value(self, type='float'):
        value = self.line.split(' ')[-1].replace(',', '')
        if '-' in value:
            value = '-' + value[:-1]
        if type == 'float':
            self.line = " ".join(self.line.split(' ')[:-1])
            return float(value)
        elif type == 'percentage':
            self.line = " ".join(self.line.split(' ')[:-1])
            return float(value)


# a = PDF(file, password=password)

# with pdfplumber.open(r'./data/Extracto_167236926_202204_TARJETA_VISA_9299.pdf' , password = '1196864') as pdf:
#     first_page = pdf.pages[0]
#     second_page = pdf.pages[1]
#     text_first = first_page.extract_text()
#     text_second = second_page.extract_text()
#     # text = text.split("Período Facturado")[1].split("Disponible Total")[0]
#     # desde = text.split("Desde:")[1].split("Hasta")[0].strip()
#     # hasta = text.split("Hasta:")[1].strip()
#     # print(desde, hasta)
#     exp = re.compile(r'^\d{6} \d{2}/\d{2}/\d{4}')
#     # print(text)
#     for item in text_first.split('\n'):
#         if exp.match(item) or 'INTERESES CORRIENTES' in item:
#             print(item)
#     for item in text_second.split('\n'):
#         if exp.match(item):
#             print(item)

#     print(len(pdf.pages))
