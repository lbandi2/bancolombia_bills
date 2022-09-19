import re
from datetime import datetime

from utils import utc_to_local
from pdf.pdf_operation import PDFOperation
from pdf.pdf_op_compare import Compare

class PDFPage:
    def __init__(self, content: str, card_id: int, exchange_rate: float):
        self.content = content
        self.card_id = card_id
        self.exchange_rate = 1
        self.currency = self.find_currency()
        if self.find_currency() == 'usd':
            self.exchange_rate = exchange_rate
        self.cargos_prev = []
        self.desde = self.find_period()[0]
        self.hasta = self.find_period()[1]
        self.operations = self.parse_page()
        self.num_operations = len(self.operations)

    def find_currency(self) -> str:
        phrase = 'estado de cuenta en: '
        for item in self.content.split('\n'):
            if phrase in item.lower():
                if 'dolares' in item.split(phrase)[-1].lower():
                    return 'usd'
                elif 'pesos' in item.split(phrase)[-1].lower():
                    return 'cop'
        else:
            raise ValueError("[PDF] Could not find currency type of page")


    def find_period(self) -> list:
        for index, item in enumerate(self.content.split('\n')):
            exp = re.findall("\d{2}/\d{2}/\d{4}", item)
            if len(exp) == 2:
                desde = exp[0]
                hasta = exp[1]
                desde_date = utc_to_local(datetime.strptime(desde, '%d/%m/%Y'))
                hasta_date = utc_to_local(datetime.strptime(hasta, '%d/%m/%Y'))
                return [desde_date, hasta_date]
        else:
            raise ValueError("Couldn't find billable period, missing 'desde' and 'hasta'")

    def fix_authorization(self, line) -> str:
        if 'INTERESES CORRIENTES' in line or 'INTERESES MORA' in line or 'GMF JURIDICO' in line or 'GMF SALDO A FAVOR' in line:
            line = '000000 ' + line
        return line

    def find_operations(self) -> list:      # strategy: find operations starting with (R00000|000000) 11/11/2014
        ops = []
        exp = re.compile(r'(\d{6}|[A-Z]\d{5}) \d{2}/\d{2}/\d{4}') 
        for line in self.content.split('\n'):
            line = self.fix_authorization(line)
            if exp.match(line):
                operation = PDFOperation(line, self.exchange_rate)
                compare = Compare(operation, self.desde, self.hasta, self.card_id)
                if compare.is_matched:
                    operation.is_matched = True
                    operation.matched_op = compare.matched_op
                ops.append(operation)
        return ops

    def check_duplicates(self, operations) -> list:
        final_lst = []
        for op in operations:
            if op.autorizacion == '000000':
                final_lst.append(op)
            else:
                for prev_op in final_lst:
                    if prev_op.autorizacion == op.autorizacion:
                        if prev_op.nombre == op.nombre:
                            if float(prev_op.cargos_y_abonos) + float(op.cargos_y_abonos) == 0:
                                final_lst.remove(prev_op)
                else:
                    final_lst.append(op)
        return final_lst

    def parse_page(self) -> list:
        all_operations = self.find_operations()
        operations = all_operations
        return operations
