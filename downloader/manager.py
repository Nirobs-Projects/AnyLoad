# -*- coding: utf-8 -*-

from .yt_dlp_engine import YTDLPDownloader
from .pytube_engine import PytubeDownloader


class DownloadManager:
    def __init__(self, url, mode, base_path, callback, task_card):
        self.url = url
        self.mode = mode
        self.base_path = base_path
        self.callback = callback
        self.task_card = task_card
        self.is_cancelled = False
        self.is_paused = False
        self.started = False
        self.active_engine = None

    def cancel(self):
        self.is_cancelled = True
        self.is_paused = False
        if self.active_engine:
            self.active_engine.cancel()

    def pause(self):
        self.is_paused = True
        if self.active_engine:
            self.active_engine.cancel()

    def run(self):
        # ইউজার শুধু "Connecting..." দেখবে, কোনো টেকনিক্যাল লগ নয়
        self.callback("status", "Connecting...", self.task_card)

        # ধাপ ১: yt-dlp দিয়ে ১০ বার চেষ্টা
        for i in range(10):
            if self._is_cancelled():
                return
            print(f"[*] Engine Attempt: {i+1}/20")
            ytdlp = YTDLPDownloader(self.url, self.mode, self.base_path, self._progress_callback)
            self.active_engine = ytdlp
            success, filepath, error = ytdlp.run()
            if success and not self._is_cancelled():
                self.callback("finished", {"message": "Completed ✓", "filepath": filepath}, self.task_card)
                return
            if error and "429" in error and "subtitle" not in error.lower():
                break # রেট লিমিট হলে ব্রেক করবে (কিন্তু সাবটাইটেলের কারণে হলে করবে না)

        # ধাপ ২: pytube দিয়ে ৫ বার চেষ্টা (শুধু ইউটিউব হলে)
        if self._is_youtube_link():
            for i in range(5):
                if self._is_cancelled():
                    return
                print(f"[*] Fallback Attempt: {i+11}/20")
                pytube = PytubeDownloader(self.url, self.mode, self.base_path, self._progress_callback)
                self.active_engine = pytube
                success, filepath, error = pytube.run()
                if success and not self._is_cancelled():
                    self.callback("finished", {"message": "Completed ✓", "filepath": filepath}, self.task_card)
                    return

        # ধাপ ৩: yt-dlp (Safe Mode) দিয়ে ৫ বার চেষ্টা
        for i in range(5):
            if self._is_cancelled():
                return
            print(f"[*] Safe Mode Attempt: {i+16}/20")
            ytdlp_safe = YTDLPDownloader(self.url, self.mode, self.base_path, self._progress_callback)
            self.active_engine = ytdlp_safe
            success, filepath, error = ytdlp_safe.run(safe=True)
            if success and not self._is_cancelled():
                self.callback("finished", {"message": "Completed ✓", "filepath": filepath}, self.task_card)
                return

        # চূড়ান্ত ব্যর্থতা (সব চেষ্টা শেষে)
        if not self._is_cancelled():
            self.callback("failed", "Failed. Please try again.", self.task_card)

    def _progress_callback(self, data):
        if not self.started:
            self.started = True
        self.callback("progress", data, self.task_card)

    def _is_cancelled(self):
        return self.is_cancelled or self.is_paused

    def _is_youtube_link(self):
        return any(tag in self.url.lower() for tag in ["youtube.com", "youtu.be"])
