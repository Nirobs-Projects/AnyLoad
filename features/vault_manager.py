# -*- coding: utf-8 -*-
import hashlib
import os
from db.manager import db


class VaultManager:
    @staticmethod
    def move_to_vault(src_path, filename, base_path):
        vault_dir = os.path.join(base_path, "Vault")
        os.makedirs(vault_dir, exist_ok=True)
        secure_name = hashlib.md5(filename.encode('utf-8')).hexdigest() + ".anyload"
        dest_path = os.path.join(vault_dir, secure_name)
        if os.path.exists(src_path):
            os.rename(src_path, dest_path)
            file_type = "video" if src_path.lower().endswith(('.mp4', '.mkv', '.webm')) else "audio"
            db.add_to_vault(filename, dest_path, file_type)
            return True, dest_path
        return False, None

    @staticmethod
    def load_vault_files():
        return db.get_vault_files()
