from datetime import timedelta

from db.db_main import DBCardOp

class Compare:
    def __init__(self, pdf_operation, date_from, date_to, card_id, tolerance=0.5):
        self.pdf_operation = pdf_operation
        self.db = DBCardOp()
        self.date_from = date_from.replace(tzinfo=None)
        self.tolerance = tolerance
        if self.date_from.weekday() in [5, 6]:
            dif = 7 - self.date_from.weekday()      
            self.date_from -= timedelta(days=dif)  # Adjust for weekend charges
        self.date_to = date_to.replace(tzinfo=None)
        #TODO: Do the same as date_from for date_to?
        self.db_records = self.db.matching_records(self.date_from, self.date_to, card_id)
        self.is_matched = self._compare_vs_card_ops()
        #TODO: add match field to cardop to link to bill op?

    def _compare_vs_card_ops(self):
        if self.pdf_operation.tipo in ['tax', 'payment', 'reimbursement']:
            return True
        for item in self.db_records:
            if item['entity'] in self.pdf_operation.nombre:
                if self.pdf_operation.cargos_y_abonos == item['amount']:
                    return True
                if self.pdf_operation.valor_original == item['amount']:
                    return True
        for item in self.db.all_records():
            if item['entity'] in self.pdf_operation.nombre:
                if (self.pdf_operation.valor_original * (1 - self.tolerance)) <= item['amount'] <= (self.pdf_operation.valor_original * (1 + self.tolerance)):
                    return True
        return False
