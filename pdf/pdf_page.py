import re
from datetime import datetime

from utils import utc_to_local
from pdf.pdf_operation import PDFOperation

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

    # def remove_operation(self, lst, op):
    #     for index, item in enumerate(lst):
    #         if item['autorizacion'] == op['autorizacion']:
    #             if item['valor_original'] == op['valor_original']:
    #                 if item['nombre'] == op['nombre']:
    #                     lst.pop(index)
    #     return lst

    # def check_duplicates(self, operations):  #TODO: This fails, need to redo it
    #     cargos_prev = []
    #     final_lst = []
    #     for op in operations:
    #         if op['autorizacion'] == '000000':
    #             final_lst.append(op)
    #         elif op['autorizacion'] not in cargos_prev:
    #             cargos_prev.append(op['autorizacion'])
    #             final_lst.append(op)
    #         elif op['autorizacion'] in cargos_prev:   # check if duplicate, then remove previous
    #             self.remove_operation(final_lst, op)
    #     return final_lst

    def check_duplicates(self, operations):
        final_lst = []
        for op in operations:
            if op['autorizacion'] == '000000':
                final_lst.append(op)
            else:
                for prev_op in final_lst:
                    if prev_op['autorizacion'] == op['autorizacion']:
                        if prev_op['nombre'] == op['nombre']:
                            if float(prev_op['cargos_y_abonos']) + float(op['cargos_y_abonos']) == 0:
                                final_lst.remove(prev_op)
                else:
                    final_lst.append(op)
        return final_lst

    def parse_page(self):
        all_operations = self.find_operations()
        # operations = self.check_duplicates(all_operations)
        operations = all_operations
        return operations
