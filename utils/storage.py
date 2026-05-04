# -*- coding: utf-8 -*-
import os
from kivy.utils import platform

class StorageManager:
    @staticmethod
    def get_base_path():
        if platform == 'android':
            return "/sdcard/Download/AnyLoad"
        else:
            return os.path.join(os.path.expanduser("~"), "Downloads", "AnyLoad")

    @staticmethod
    def setup_folders():
        base_path = StorageManager.get_base_path()
        sub_folders = ["Videos", "Audio", "Vault", "Ringtones", ".temp", ".thumbnails"]
        
        for folder in sub_folders:
            path = os.path.join(base_path, folder)
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
        
        nomedia_path = os.path.join(base_path, "Vault", ".nomedia")
        if not os.path.exists(nomedia_path):
            with open(nomedia_path, 'w') as f:
                pass
        
        return base_path

    @staticmethod
    def get_temp_path():
        return os.path.join(StorageManager.get_base_path(), ".temp")
    
    @staticmethod
    def get_thumbnail_path():
        return os.path.join(StorageManager.get_base_path(), ".thumbnails")