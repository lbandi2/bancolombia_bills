import re
from datetime import datetime

from utils import utc_to_local

class PDFOperation:
    def __init__(self, line: str, exchange_rate=1):
        self.original_line = line
        self.line = line
        self.exchange_rate = exchange_rate
        self.values = {}
        self.get_values()

    def __repr__(self):
        return f'[{"MATCHED" if self.is_matched else "NOT MATCHED"}] [{self.tipo}] {self.fecha.strftime("%Y-%m-%d")} {self.nombre} {self.cargos_y_abonos if self.cargos_y_abonos > 0 else self.valor_original} [{self.cuotas}]'

    def get_values(self) -> None:
        self.autorizacion = self.get_autorizacion()
        self.fecha = self.get_fecha().date()
        self.cuotas = self.get_cuotas()
        self.tipo = self.get_tipo()
        self.saldo_a_diferir = round(self.get_last_value() * self.exchange_rate, 2)
        if self.cuotas == '0':
            self.saldo_a_diferir = 0.0
        self.cargos_y_abonos = round(self.get_last_value() * self.exchange_rate, 2)
        self.tasa_ea_facturada = self.get_tasa_facturada()
        self.tasa_pactada = self.get_tasa_pactada()
        self.valor_original = round(self.get_last_value() * self.exchange_rate, 2)
        self.nombre = self.get_nombre()
        self.is_matched = False
        self.matched_op = None

    def get_tasa_facturada(self) -> float:
        exp = re.compile(r'(\d{2}\,\d{4})')
        for item in self.line.split(' '):
            if exp.match(item):
                self.line = " ".join(self.line.split(' ')[:-1])
                tasa = item.replace(',', '.')
                return float(tasa)
        return 0.0

    def get_tasa_pactada(self) -> float:
        exp = re.compile(r'(\d{1}\,\d{4})')
        for item in self.line.split(' '):
            if exp.match(item):
                self.line = " ".join(self.line.split(' ')[:-1])
                tasa = item.replace(',', '.')
                return float(tasa)
        return 0.0

    def get_autorizacion(self) -> str:
        aut = self.line.split(" ")[0]
        self.line = self.line.replace(f'{aut} ', '')
        return aut

    def get_fecha(self) -> datetime:
        exp = re.compile(r'\d{2}/\d{2}/\d{4}')
        for item in self.line.split(" "):
            if exp.match(item):
                self.line = self.line.replace(f'{item} ', '')
                fecha = utc_to_local(datetime.strptime(item, '%d/%m/%Y'))
                return fecha

    def get_nombre(self) -> str:
        return self.line.title().strip()

    def get_tipo(self) -> str:
        taxes = [
            'INTERESES CORRIENTES',
            'INTERESES MORA',
            'GMF JURIDICO',
            'GMF SALDO A FAVOR',
            'CUOTA DE MANEJO',
            'REVERSION DE ABONO'
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
    
    def get_cuotas(self) -> str:
        exp = re.compile(r"(\d{1,2})/(\d{1,2})$")
        for item in self.line.split(" "):
            if exp.match(item):
                self.line = self.line.replace(f' {item}', '')
                return item
        return '0'
    
    def get_last_value(self, type='float') -> float:
        value = self.line.split(' ')[-1].replace(',', '')
        if '-' in value:
            value = '-' + value[:-1]
        if type == 'float':
            self.line = " ".join(self.line.split(' ')[:-1])
            return float(value)
        elif type == 'percentage':
            self.line = " ".join(self.line.split(' ')[:-1])
            return float(value)
