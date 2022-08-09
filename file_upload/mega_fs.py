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

    def get_link(self):
        return self.mega.get_upload_link(self.upload_file())

    def upload_file(self):
        return self.mega.upload(self.file, self.find_folder()[0])

    def find_folder(self):
        folder = self.mega.find(self.folder)
        if folder is None:
            raise ValueError(f"[{self.service_name}] Couldn't find folder '{folder}'")
        return folder

