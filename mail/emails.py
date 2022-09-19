from base64 import urlsafe_b64decode
import os
from utils import convert_date, get_size_format

class Email:
    def __init__(self, headers, parts, has_parts, labels, message, service, get_attachment, unwanted_attachments=[]):
        self.has_parts = has_parts
        self.headers = headers
        self.parts = parts
        self.labels = labels
        self.message = message
        self.service = service
        self.get_attachment = get_attachment
        self.unwanted_attachments = unwanted_attachments

        self.is_unread = self.get_unread_status()
        self.sender = ''
        self.to = ''
        self.subject = ''
        self.date = ''
        self.time = ''
        self.is_html = False
        self.body = ''
        self.has_attachment = False
        # self.attachment = {}
        self.attachment = []
        self.read_payload()

    def is_unwanted_attachment(self, item) -> bool:
        for unwanted in self.unwanted_attachments:
            if unwanted in item['filename'].lower():
                return True
        return False

    def download_attachment(self, folder_name='./data/') -> None:
        for item in self.attachment:
            if self.is_unwanted_attachment(item):
                print(f"Skipping attachment with filename: '{item['filename']}'")
                continue
            else:
                print("Saving file:", item['filename'], "size:", item['file_size'])
                attachment = self.service.users().messages() \
                            .attachments().get(id=item['id'], userId='me', messageId=item['message_id']).execute()
                data = attachment.get("data")
                filepath = os.path.join(folder_name, item['filename'])
                if data:
                    with open(filepath, "wb") as f:
                        f.write(urlsafe_b64decode(data))


    def get_unread_status(self) -> bool:
        if 'UNREAD' in self.labels:
            return True
        return False

    def parse_parts(self, parts, message, folder_name="./data/"):
        """
        Utility function that parses the content of an email partition
        """
        if parts:
            for part in parts:
                filename = part.get("filename")
                mimeType = part.get("mimeType")
                body = part.get("body")
                data = body.get("data")
                file_size = body.get("size")
                part_headers = part.get("headers")
                if part.get("parts"):
                    # recursively call this function when we see that a part
                    # has parts inside
                    self.parse_parts(part.get("parts"), self.message)
                if mimeType == "text/plain":
                    if data:
                        text = urlsafe_b64decode(data).decode()
                        self.body = text
                elif mimeType == "text/html":
                    self.is_html = True
                    self.body = urlsafe_b64decode(data)
                else:
                    for part_header in part_headers:
                        part_header_name = part_header.get("name")
                        part_header_value = part_header.get("value")
                        if part_header_name == "Content-Disposition":
                            if "attachment" in part_header_value:
                                # we get the attachment ID 
                                # and make another request to get the attachment itself
                                self.has_attachment = True
                                attach = {}
                                attach['filename'] = filename
                                attach['file_size'] = get_size_format(file_size)
                                attach['id'] = body.get("attachmentId")
                                attach['message_id'] = message['id']
                                self.attachment.append(attach)

    def read_payload(self) -> None:
        if self.headers:
            for header in self.headers:
                name = header.get("name")
                value = header.get("value")
                if name.lower() == 'from':
                    self.sender = value
                if name.lower() == "to":
                    self.to = value.lower()
                if name.lower() == "subject":
                    self.subject = value
                if name.lower() == "date":
                    date = convert_date(value)
                    self.date = date
                if name.lower() == "content-type":
                    if "text/html" in value:
                        self.is_html = True
        if self.has_parts:
            self.parse_parts(self.parts, self.message)
        else:
            self.body = urlsafe_b64decode(self.parts)
