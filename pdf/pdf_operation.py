import re
from datetime import datetime

from utils import utc_to_local

class PDFOperation:
    def __init__(self, line):
        self.original_line = line
        self.line = line
        self.values = {}
        # TODO: Compare operation to db operations to set is_matched before proceeding
        self.get_values()

    def get_values(self):
        self.values['autorizacion'] = self.get_autorizacion()
        self.values['fecha'] = self.get_fecha().date()
        self.values['cuotas'] = self.get_cuotas()
        self.values['tipo'] = self.get_tipo()
        self.values['saldo_a_diferir'] = self.get_last_value()
        if self.values['cuotas'] == '0':
            self.values['saldo_a_diferir'] = 0.0
        self.values['cargos_y_abonos'] = self.get_last_value()
        self.values['tasa_ea_facturada'] = self.get_tasa_facturada()
        self.values['tasa_pactada'] = self.get_tasa_pactada()
        self.values['valor_original'] = self.get_last_value()
        self.values['nombre'] = self.get_nombre()
        self.values['is_matched'] = False

    def get_tasa_facturada(self):
        exp = re.compile(r'(\d{2}\,\d{4})')
        for item in self.line.split(' '):
            if exp.match(item):
                self.line = " ".join(self.line.split(' ')[:-1])
                tasa = item.replace(',', '.')
                return float(tasa)
        return 0.0

    def get_tasa_pactada(self):
        exp = re.compile(r'(\d{1}\,\d{4})')
        for item in self.line.split(' '):
            if exp.match(item):
                self.line = " ".join(self.line.split(' ')[:-1])
                tasa = item.replace(',', '.')
                return float(tasa)
        return 0.0

    def get_autorizacion(self):
        aut = self.line.split(" ")[0]
        self.line = self.line.replace(f'{aut} ', '')
        return aut

    def get_fecha(self):
        exp = re.compile(r'\d{2}/\d{2}/\d{4}')
        for item in self.line.split(" "):
            if exp.match(item):
                self.line = self.line.replace(f'{item} ', '')
                fecha = utc_to_local(datetime.strptime(item, '%d/%m/%Y'))
                return fecha

    def get_nombre(self):
        return self.line.title().strip()

    def get_tipo(self):
        taxes = [
            'INTERESES CORRIENTES',
            'INTERESES MORA',
            'GMF JURIDICO',
            'CUOTA DE MANEJO'
        ]
        payments = [
            'ABONO SUCURSAL VIRTUAL',
            'ABONO DEBITO AUTOMATICO',
            'ABONO DEBITO POR MORA'
        ]

        for tax in taxes:
            if tax in self.line:
                return 'tax'

        for payment in payments:
            if payment in self.line:
                if '-' in self.line.split(' ')[-2]:  # this might cause problems
                    return 'payment'

        if '-' in self.line.split(' ')[-2]:
            return 'reimbursement'
        
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
