from dotenv import load_dotenv
import os

from mail.gmail_setup import gmail_authenticate
from mail.emails import Email

load_dotenv()

GMAIL_LABEL = os.getenv('GMAIL_LABEL_BILLS')

class Search:
    UNWANTED_ATTACHMENTS = ['comisiones_consolidadas', 'cta_ahorros'] #TODO: add pdf parsing for cta_ahorros

    def __init__(self, query=GMAIL_LABEL, stop_if_unread=False, ignore_subject=[]):
        self.query = query
        self.stop_if_unread = stop_if_unread
        self.ignore_subject = ignore_subject
        self.service = gmail_authenticate()
        self.emails = []
        self.message_ids = self.search_messages(query)
        self.parse_emails()

    def parse_emails(self):
        for index, msg in enumerate(self.message_ids):
            message_content = self.fetch_message(msg)[0]
            message_labels = self.fetch_message(msg)[1]
            message_payload = self.parse_payload(message_content)
            message_headers = message_payload[0]
            has_parts = bool(message_payload[1])
            message_parts = message_payload[2]

            email = Email(message_headers, message_parts, has_parts, message_labels, msg, \
                    self.service, get_attachment=True, unwanted_attachments=self.UNWANTED_ATTACHMENTS)

            if self.stop_if_unread:    # stop processing when the first read mail is found
                if email.is_unread:
                    print(f"Fetched email from {email.date.strftime('%Y-%m-%d')}")
                if not email.is_unread: 
                    if len(self.emails) == 0:
                        print("No new mails to process.")
                    else:
                        print(f"Found read email from {email.date.strftime('%Y-%m-%d')}, aborting email fetch.")
                    break
            if self.ignore_subject != []:
                for item in self.ignore_subject:
                    if item not in email.subject:
                        self.emails.append(email)
                        self.mark_as_read(msg)
            if email.has_attachment:
                email.download_attachment()
            self.emails.append(email)
            self.mark_as_read(msg)
    
    def mark_as_read(self, msg) -> None:
        return self.service.users().messages().modify(
            userId='me', id=msg['id'],
            body={'removeLabelIds': ['UNREAD']}).execute()

    def search_messages(self, query: str) -> list:
        result = self.service.users().messages().list(maxResults=500, userId='me', labelIds=[query]).execute()
        messages = []
        if 'messages' in result:
            messages.extend(result['messages'])
        while 'nextPageToken' in result:
            page_token = result['nextPageToken']
            result = self.service.users().messages().list(maxResults=500, pageToken=page_token, userId='me', labelIds=[query]).execute()
            if 'messages' in result:
                messages.extend(result['messages'])
        return messages

    def fetch_message(self, message):
        msg = self.service.users().messages().get(userId='me', id=message['id'], format='full').execute()
        payload = msg['payload']
        labels = msg['labelIds']
        return payload, labels

    def has_parts(self, payload) -> bool:
        if 'parts' in payload:
            return True
        return False

    def parse_payload(self, payload):
        headers = payload.get('headers')
        if self.has_parts(payload):
            parts = payload.get('parts')
            has_parts = True
        else:
            parts = payload.get('body').get('data')
            has_parts = False
        return headers, has_parts, parts


# class SearchOperations(Search):
#     def __init__(self, query):
#         super().__init__(query, stop_if_unread=True)
#         self.operations = self.get_operations()
#         self.push_to_db()

#     def push_to_db(self):
#         if self.operations != []:
#             for operation in self.operations:
#                 # print(operation)
#                 db = DB(db_table=operation['db_table'])
#                 # try:
#                 db.insert(operation)
#                 # except:
#                     # print(f"Error inserting: {operation}")

#     def get_operations(self):
#         operations = []
#         for item in self.emails:
#             if item.is_unread:
#                 date = item.date.isoformat()
#                 operation = MailOperation(item.body, date)
#                 if operation.is_valid():
#                     operations.append(operation.operation)
#         return operations

