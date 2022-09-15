from datetime import timedelta

from db.db_main import DBCardOp, DBBillOp

class Compare:
    def __init__(self, pdf_operation, date_from, date_to, card_id, tolerance=0.1):
        self.pdf_operation = pdf_operation
        self.db_cardop = DBCardOp()
        self.date_from = date_from.replace(tzinfo=None) - timedelta(days=3)
        self.date_to = date_to.replace(tzinfo=None) + timedelta(days=3)
        self.tolerance = tolerance
        self.db_cardop_records = self.db_cardop.matching_records(self.date_from, self.date_to, card_id)
        self.db_billop_records = DBBillOp().all_records()
        self.is_matched = False if self._compare_vs_card_ops() is None else True
        self.matched_op = self._compare_vs_card_ops()

    def _compare_vs_card_ops(self, tolerance=0.05):
        # for item in self.db_cardop_records:
        #     if item['entity'].lower() in self.pdf_operation.nombre.lower() or self.pdf_operation.nombre.lower() in item['entity'].lower():
        #         if self.pdf_operation.fecha == item['date'].date():
        #             value = self.pdf_operation.valor_original
        #             if value * (1 - tolerance) < item['amount'] < value * (1 + tolerance):
        #                 return item['id']
        #         elif (self.pdf_operation.fecha - timedelta(days=2)) < item['date'].date() < (self.pdf_operation.fecha + timedelta(days=2)):
        #             value = self.pdf_operation.valor_original
        #             if value * (1 - tolerance) < item['amount'] < value * (1 + tolerance):
        #                 return item['id']
        #         elif self.pdf_operation.cuotas not in ['0', '1', '1/1']:
        #             cuotas = self.pdf_operation.cuotas.split('/')[-1]
        #             pdf_value = self.pdf_operation.cargos_y_abonos * int(cuotas)
        #             if (pdf_value * (1 - self.tolerance)) <= item['amount'] <= (pdf_value * (1 + self.tolerance)):
        #                 return item['id']

        for item in self.db_cardop_records:
            if item['entity'].lower() in self.pdf_operation.nombre.lower() or self.pdf_operation.nombre.lower() in item['entity'].lower():
                if self.pdf_operation.fecha == item['date'].date():
                    value = self.pdf_operation.valor_original
                    if value == item['amount']:
                        return item['id']
                elif self.pdf_operation.cuotas not in ['0', '1', '1/1']:
                    cuotas = self.pdf_operation.cuotas.split('/')[-1]
                    pdf_value = self.pdf_operation.cargos_y_abonos * int(cuotas)
                    if (pdf_value * (1 - self.tolerance)) <= item['amount'] <= (pdf_value * (1 + self.tolerance)):
                        return item['id']
        else:
            for item in self.db_cardop_records:
                if item['entity'].lower() in self.pdf_operation.nombre.lower() or self.pdf_operation.nombre.lower() in item['entity'].lower():
                    if (self.pdf_operation.fecha - timedelta(days=2)) < item['date'].date() < (self.pdf_operation.fecha + timedelta(days=2)):
                        value = self.pdf_operation.valor_original
                        if value * (1 - tolerance) < item['amount'] < value * (1 + tolerance):
                            return item['id']


        for item in self.db_billop_records:
            if item['authorization'] != '000000' and \
                item['dues'] not in ['1', '1/1', '0'] and \
                item['authorization'] == self.pdf_operation.autorizacion:
                if (self.pdf_operation.valor_original * (1 - self.tolerance)) <= item['original_value'] <= (self.pdf_operation.valor_original * (1 + self.tolerance)):
                    return item['op_match_id']

        return None

