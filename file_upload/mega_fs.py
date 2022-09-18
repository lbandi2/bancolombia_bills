from mega import Mega, errors
from dotenv import load_dotenv
import os

load_dotenv()

MEGA_USER = os.getenv('MEGA_USER')
MEGA_PASS = os.getenv('MEGA_PASS')
MEGA_FOLDER = os.getenv('MEGA_FOLDER')

class MegaFile:
    def __init__(self, file, user=MEGA_USER, password=MEGA_PASS, folder=MEGA_FOLDER):
        self.file = file
        self.user = user
        self.password = password
        self.folder = folder
        self.service_name = 'MEGA'
        try:
            self.mega = Mega().login(self.user, self.password)
            print(f"[{self.service_name}] Successfully logged in..")
        except errors.RequestError:
            raise ValueError(f"[{self.service_name}] Wrong username/password combination")

    # def mega(self):
    #     while True:
    #         try:
    #             try:
    #                 Mega().login(self.user, self.password)
    #             except json.decoder.JSONDecodeError:
    #                 print(f"[MEGA] Error while uploading file, retrying..")
    #         except errors.RequestError:
    #             raise ValueError(f"[{self.service_name}] Wrong username/password combination")
        

    def get_link(self):
        if self.file_exists():
            print(f"[{self.service_name}] File '{self.file.split('/')[-1]}' is already uploaded.")
            return None
        print(f"[{self.service_name}] File uploaded successfully")
        return self.mega.get_upload_link(self.upload_file())

    def find_folder(self):
        folder = self.mega.find(self.folder)
        if folder is None:
            raise ValueError(f"[{self.service_name}] Couldn't find folder '{folder}'")
        return folder

    def file_exists(self):
        if self.file is None:
            raise ValueError("[MEGA] File path is not passed")
        while True:
            try:
                file = self.mega.find(self.file.split('/')[-1])
                break
            except:
                print(f"[MEGA] Error while uploading file, retrying..")
        if file is None:
            return False
        return True

    def upload_file(self):
        return self.mega.upload(self.file, self.find_folder()[0])

if __name__ == '__main__':
    from utils import list_pdfs
    pdfs = list_pdfs()
    for item in pdfs:
        MegaFile(item).upload_file()
