import sqlite3
import os
import hashlib

class DatabaseManager:
    def __init__(self):
        # ফোনের স্টোরেজে ডাটাবেস পাথ
        base = os.path.join(os.path.expanduser("~"), "AnyLoad_Downloads")
        os.makedirs(base, exist_ok=True)
        self.db_path = os.path.join(base, "anyload_data.db")
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS settings 
                            (key TEXT PRIMARY KEY, value TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS vault 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                             original_name TEXT, vault_path TEXT, file_type TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS security_questions 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                             question TEXT, answer TEXT)''')
        self.conn.commit()

    def set_pin(self, pin):
        hashed_pin = hashlib.sha256(pin.encode()).hexdigest()
        self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('vault_pin', ?)", (hashed_pin,))
        self.conn.commit()

    def check_pin(self, pin):
        hashed_pin = hashlib.sha256(pin.encode()).hexdigest()
        self.cursor.execute("SELECT value FROM settings WHERE key='vault_pin'")
        result = self.cursor.fetchone()
        return result and result[0] == hashed_pin

    def is_pin_set(self):
        self.cursor.execute("SELECT value FROM settings WHERE key='vault_pin'")
        return self.cursor.fetchone() is not None

    # নতুন: ভল্টে ফাইল রেকর্ড রাখা
    def add_to_vault(self, original_name, vault_path, file_type):
        self.cursor.execute("INSERT INTO vault (original_name, vault_path, file_type) VALUES (?, ?, ?)",
                            (original_name, vault_path, file_type))
        self.conn.commit()

    # নতুন: ভল্টের ফাইল লিস্ট আনা
    def get_vault_files(self):
        self.cursor.execute("SELECT original_name, vault_path, file_type FROM vault")
        return self.cursor.fetchall()

    # সিকিউরিটি প্রশ্ন সেভ করা
    def save_security_questions(self, qa_list):
        self.cursor.execute("DELETE FROM security_questions")
        for q, a in qa_list:
            hashed_answer = hashlib.sha256(a.lower().strip().encode()).hexdigest()
            self.cursor.execute("INSERT INTO security_questions (question, answer) VALUES (?, ?)", (q, hashed_answer))
        self.conn.commit()

    # সিকিউরিটি প্রশ্ন যাচাই করা
    def verify_security_questions(self, answers):
        self.cursor.execute("SELECT answer FROM security_questions ORDER BY id")
        stored = [row[0] for row in self.cursor.fetchall()]
        if len(stored) != len(answers):
            return False
        for i, ans in enumerate(answers):
            hashed = hashlib.sha256(ans.lower().strip().encode()).hexdigest()
            if hashed != stored[i]:
                return False
        return True

    # সিকিউরিটি প্রশ্ন আছে কিনা চেক
    def has_security_questions(self):
        self.cursor.execute("SELECT COUNT(*) FROM security_questions")
        return self.cursor.fetchone()[0] > 0

    # সিকিউরিটি প্রশ্ন লোড করা
    def get_security_questions(self):
        self.cursor.execute("SELECT question FROM security_questions ORDER BY id")
        return [row[0] for row in self.cursor.fetchall()]

db = DatabaseManager()