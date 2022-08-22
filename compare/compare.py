from datetime import timedelta

from db.db_main import DBCardOp

class Compare:
    def __init__(self, pdf_content):
        self.bill = pdf_content
        self.card_ops = DBCardOp()
        self.date_from = self.bill.desde.replace(tzinfo=None)
        if self.date_from.weekday() in [5, 6]:
            dif = 7 - self.date_from.weekday()      
            self.date_from -= timedelta(days=dif)  # Adjust for weekend charges
        self.date_to = self.bill.hasta.replace(tzinfo=None)
        #TODO: Do the same as date_from for date_to?
        self.db_records = self.card_ops.matching_records(self.date_from, self.date_to, self.bill.card_id)
        self.matched = []
        self.matches = self._compare_vs_card_ops()
        self.unmatched = self.get_no_matches()
        self.matched.extend(self.matches)

    def update_db(self):
        pass

    # def _compare_vs_card_ops(self):
    #     lst_matches = []
    #     for pdf_entry in self.bill.operations:
    #         for item in self.db_records:
    #             if item['entity'] in pdf_entry['nombre']:
    #                 if (pdf_entry['cargos_y_abonos'] - 1500) <= item['amount'] <= (pdf_entry['cargos_y_abonos'] + 1500):
    #                     if item not in lst_matches:
    #                         lst_matches.append(item)
    #     if len(self.db_records) != len(lst_matches):
    #         for item in self.card_ops.all_records():
    #             if item['entity'] in pdf_entry['nombre']:
    #                 if (pdf_entry['valor_original'] - 1500) <= item['amount'] <= (pdf_entry['valor_original'] + 1500):
    #                     if item not in lst_matches:
    #                         lst_matches.append(item)
    #     return lst_matches

    def _compare_vs_card_ops(self):
        lst_matches = []
        for pdf_entry in self.bill.operations:
            if pdf_entry['tipo'] in ['tax', 'payment', 'reimbursement']:
                lst_matches.append(pdf_entry)
            for item in self.db_records:
                if item['entity'] in pdf_entry['nombre']:
                    if pdf_entry['cargos_y_abonos'] == item['amount'] and pdf_entry not in lst_matches:
                        lst_matches.append(pdf_entry)
                    if pdf_entry['valor_original'] == item['amount'] and pdf_entry not in lst_matches:
                        lst_matches.append(pdf_entry)
            if len(self.bill.operations) > len(lst_matches):
                for item in self.card_ops.all_records():
                    if item['entity'] in pdf_entry['nombre']:
                        if (pdf_entry['valor_original'] - 1500) <= item['amount'] <= (pdf_entry['valor_original'] + 1500):
                            if pdf_entry not in lst_matches:
                                lst_matches.append(pdf_entry)
        return lst_matches


    # def get_no_matches(self):
    #     no_matches = []
    #     for pdf_entry in self.bill.operations:
    #         for item in self.db_records:
    #             if pdf_entry['nombre'] == item['entity']:
    #                 if pdf_entry['cargos_y_abonos'] == item['amount']:
    #                     continue
    #         else:
    #             if pdf_entry not in self.matches and pdf_entry not in no_matches:
    #                 if pdf_entry['tipo'] != 'tax' and pdf_entry['tipo'] != 'payment':
    #                     no_matches.append(pdf_entry)
    #     return no_matches

    def get_no_matches(self):
        no_matches = []
        for pdf_entry in self.bill.operations:
            for item in self.db_records:
                if item['entity'] in pdf_entry['nombre']:
                    if (pdf_entry['cargos_y_abonos'] - 1500) <= item['amount'] <= (pdf_entry['cargos_y_abonos'] + 1500):
                        continue
            else:
                if pdf_entry not in no_matches and pdf_entry not in self.matches:
                    if pdf_entry['tipo'] != 'tax' and pdf_entry['tipo'] != 'payment':
                        no_matches.append(pdf_entry)
        return no_matches

    # def get_later_matches(self):
    #     later_matches = []
    #     for bill_entry in self.get_no_matches():
    #         for db_item in self.card_ops.all_records():
    #             if db_item['entity'] in bill_entry['nombre']:
    #                 if (bill_entry['valor_original'] - 1500) <= db_item['amount'] <= (bill_entry['valor_original'] + 1500):
    #                     if bill_entry not in later_matches and bill_entry not in self.matches:
    #                         later_matches.append(bill_entry)
    #                 # else:
    #                 #     print(f"not matching: {bill_entry['nombre']} {bill_entry['valor_original']} {db_item['entity']} {db_item['amount']}")
    #     return later_matches


if __name__ == '__main__':
    from pdf.pdf_main import PDF
    pdf = PDF('./data/Extracto_205358644_202207_TARJETA_MASTERCARD_8814.pdf', '1197309')
    a = Compare(pdf)
    pass
