import gc
from concurrent.futures import ThreadPoolExecutor
from kivy.clock import mainthread

class QueueManager:
    def __init__(self, max_workers=5):
        # সর্বোচ্চ ৫টি প্যারালাল ডাউনলোড স্লট
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = {} # বর্তমানে চলা ডাউনলোডের লিস্ট

    def add_task(self, url, mode, base_path, callback, task_card):
        """নতুন ডাউনলোড কিউতে যোগ করা"""
        # টাস্কটিকে এক্সিকিউটরে পাঠানো
        future = self.executor.submit(
            self._execute_engine, url, mode, base_path, callback, task_card
        )
        self.active_tasks[task_card] = future

    def _execute_engine(self, url, mode, base_path, callback, task_card):
        """ইঞ্জিন কল করা (Lazy Loading সহ)"""
        from core.downloader import DownloaderEngine
        engine = DownloaderEngine(url, mode, base_path, callback, task_card)
        engine.run()
        
        # কাজ শেষে র‍্যাম ক্লিনআপ
        if task_card in self.active_tasks:
            del self.active_tasks[task_card]
        gc.collect()

# গ্লোবাল কিউ ম্যানেজার অবজেক্ট
queue_manager = QueueManager(max_workers=5)