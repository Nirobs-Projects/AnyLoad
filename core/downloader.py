# -*- coding: utf-8 -*-
# ===================================================================
# downloader.py (Final Merged Version with Pause/Cancel, Retry, Unicode, Fallback)
# Developer: Gemini AI (Guided by Nirob Hasan)
# ===================================================================

import gc
import os
import re
import time
import unicodedata

from utils.encoding_helper import sanitize_filename

# `TagEditor` ক্লাসটি এখানে থাকার কথা (এখন কমেন্ট করা)
# from utils.tag_editor import TagEditor

# ===================================================================
# Logger Class for yt-dlp to prevent crash on Android
# ===================================================================
class YTDLLogger:
    def debug(self, msg):
        pass  # ডিবাগ মেসেজ ইগনোর করা হবে

    def warning(self, msg):
        pass  # ওয়ার্নিং মেসেজ ইগনোর করা হবে

    def error(self, msg):
        # UI তে পাঠানোর জন্য এররটি প্রিন্ট করা যেতে পারে
        print(f"[yt-dlp ERROR] {msg}")

# ===================================================================
# Main Downloader Engine
# ===================================================================
class DownloaderEngine:
    def __init__(self, url, mode, base_path, callback, task_card):
        self.url = url
        self.mode = mode
        self.base_path = base_path
        self.callback = callback
        self.task_card = task_card
        self.is_cancelled = False
        self.is_paused = False

    def stop(self, pause=False):
        """Pause or cancel the current download."""
        self.is_cancelled = True
        self.is_paused = pause
        if pause:
            self.callback("status", "Paused", self.task_card)
        else:
            self.callback("status", "Cancelling download...", self.task_card)

    def run(self):
        """Main entry point for download processing."""
        try:
            self.callback("status", "Preparing download...", self.task_card)
            success, error_message = self.try_ytdlp()

            if not success and not self.is_cancelled:
                if self._is_youtube_link():
                    self.callback("status", "🔄 yt-dlp failed. Trying pytube fallback...", self.task_card)
                    fallback_success = self.try_pytube()
                    if not fallback_success and not self.is_cancelled:
                        self.callback("status", "🔄 Pytube failed. Retrying yt-dlp safe mode...", self.task_card)
                        safe_success, safe_error = self.try_ytdlp(safe=True)
                        if not safe_success and not self.is_cancelled:
                            self.callback("error", "Download failed. Please try again.", self.task_card)
                else:
                    safe_success, safe_error = self.try_ytdlp(safe=True)
                    if not safe_success and not self.is_cancelled:
                        self.callback("error", "Download failed. Please try again.", self.task_card)

        except Exception as e:
            if "PAUSED" not in str(e).upper():
                self.callback("error", str(e), self.task_card)
        finally:
            gc.collect()

    def try_ytdlp(self, safe=False):
        """yt-dlp engine logic with retry and fallback-safe mode."""
        try:
            import yt_dlp
        except ImportError:
            return False, "yt-dlp is not installed"

        save_dir = os.path.join(self.base_path, "Videos" if "Audio" not in self.mode else "Audio")
        os.makedirs(save_dir, exist_ok=True)
        if "Playlist" in self.mode:
            os.makedirs(os.path.join(save_dir, 'Playlists'), exist_ok=True)

        if "Playlist" in self.mode:
            out_template = os.path.join(save_dir, 'Playlists', '%(playlist_title)s', '%(title)s.%(ext)s')
        else:
            out_template = os.path.join(save_dir, '%(title)s.%(ext)s')

        base_opts = {
            'logger': YTDLLogger(),
            'progress_hooks': [self._ytdlp_hook],
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'outtmpl': out_template,
            'continuedl': True,
            'retries': 5,
            'sleep_interval_requests': 1,
            'sleep_interval': 1,
            'ignoreerrors': False,
            'restrictfilenames': False,
            'encoding': 'utf-8',
        }

        if "Audio" in self.mode:
            base_opts['format'] = 'bestaudio/best'
            base_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif "Bangla Sub" in self.mode:
            base_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            base_opts['writesubtitles'] = True
            base_opts['writeautomaticsub'] = True
            base_opts['subtitleslangs'] = ['bn', 'en']
            base_opts['postprocessors'] = [{'key': 'FFmpegEmbedSubtitle'}]
            base_opts['merge_output_format'] = 'mkv'
            
            
        elif "Choose Quality" in self.mode:
                # কোয়ালিটি ফোর্স করার জন্য লজিক
                quality_map = {"8K": "4320", "4K": "2160", "1080p": "1080", "720p": "720", "480p": "480", "360p": "360"}
                selected_q = "1080" # ডিফল্ট
                for q in quality_map:
                    if q in self.mode:
                        selected_q = quality_map[q]
                
                # [height=value] দিলে শুধু ওই কোয়ালিটিই নামবে, কমবেশি হবে না
                opts['format'] = f'bestvideo[height={selected_q}]+bestaudio/best'
        elif "Playlist" in self.mode:
            base_opts['noplaylist'] = False

        if safe:
            base_opts['sleep_interval'] = 2
            base_opts['sleep_interval_requests'] = 2
            base_opts['retries'] = 10
            base_opts['continuedl'] = True

        retries = 3 if not safe else 5
        for attempt in range(1, retries + 1):
            if attempt > 1:
                self.callback("status", f"Retrying yt-dlp ({attempt}/{retries})...", self.task_card)
                time.sleep(attempt)
            try:
                with yt_dlp.YoutubeDL(base_opts) as ydl:
                    info = ydl.extract_info(self.url, download=True)
                    if self.is_cancelled:
                        return False, "Cancelled"

                    filename = ydl.prepare_filename(info)
                    filename = self._normalize_filepath(filename)
                    if "Audio" in self.mode:
                        filename = os.path.splitext(filename)[0] + ".mp3"
                    if os.path.exists(filename):
                        filename = self._normalize_filepath(filename)
                    self.callback("finished", {"message": "✅ Download Complete!", "filepath": filename}, self.task_card)
                    return True, None
            except Exception as e:
                if self._is_pause_exception(e):
                    raise
                error_message = str(e)
                print(f"yt-dlp Error: {error_message}")
                if attempt == retries:
                    return False, error_message
                if self._is_retriable_error(error_message):
                    continue
                return False, error_message

        return False, "Unexpected yt-dlp failure"

    def try_pytube(self):
        """pytube ফলব্যাক লজিক (Pause/Cancel সহ)"""
        try:
            from pytube import YouTube
        except ImportError:
            self.callback("error", "Error: No module named 'pytube'. Run 'pip install pytube'", self.task_card)
            return False

        retries = 3
        for attempt in range(1, retries + 1):
            if attempt > 1:
                self.callback("status", f"Retrying pytube fallback ({attempt}/{retries})...", self.task_card)
                time.sleep(attempt)
            try:
                yt = YouTube(self.url, on_progress_callback=self._pytube_hook)
                if "Audio" in self.mode:
                    stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                    save_path = os.path.join(self.base_path, "Audio")
                else:
                    stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                    if not stream:
                        stream = yt.streams.filter(adaptive=True, file_extension='mp4').order_by('resolution').desc().first()
                    save_path = os.path.join(self.base_path, "Videos")

                if not stream:
                    raise Exception("No compatible pytube stream found")

                os.makedirs(save_path, exist_ok=True)
                out_file = stream.download(output_path=save_path)
                if self.is_cancelled:
                    return False

                out_file = self._normalize_filepath(out_file)
                self.callback("finished", {"message": "✅ Fallback Success!", "filepath": out_file}, self.task_card)
                return True
            except Exception as e:
                if self._is_pause_exception(e):
                    raise
                error_message = str(e)
                print(f"Pytube Error: {error_message}")
                if attempt == retries:
                    return False
                time.sleep(attempt)
                continue

        return False

    def _quality_value(self):
        if "8K" in self.mode:
            return "4320"
        if "4K" in self.mode:
            return "2160"
        if "1080p" in self.mode:
            return "1080"
        if "720p" in self.mode:
            return "720"
        if "480p" in self.mode:
            return "480"
        if "360p" in self.mode:
            return "360"
        return "1080"

    def _is_youtube_link(self):
        return any(tag in self.url.lower() for tag in ["youtube.com", "youtu.be"])

    def _normalize_filepath(self, path):
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        filename = sanitize_filename(filename)
        if directory:
            os.makedirs(directory, exist_ok=True)
            return os.path.join(directory, filename)
        return filename

    def _is_pause_exception(self, exception):
        return "PAUSED" in str(exception).upper()

    def _is_retriable_error(self, error_message):
        msg = str(error_message).lower()
        return any(keyword in msg for keyword in ["429", "416", "rate limit", "temporarily unavailable", "timeout", "connection reset", "connection aborted"])

    def _ytdlp_hook(self, d):
        """yt-dlp এর প্রগ্রেস ডাটা UI-তে পাঠানো (Pause/Cancel লজিক সহ)"""
        if self.is_cancelled:
            raise Exception("PAUSED by user")
            
        if d['status'] == 'downloading':
            title = d.get('info_dict', {}).get('title', 'Downloading Media...')
            percent = d.get('_percent_str', '0%').replace('\x1b[0;94m', '').replace('\x1b[0m', '').strip()
            speed = d.get('_speed_str', '0KiB/s').replace('\x1b[0;32m', '').replace('\x1b[0m', '').strip()
            eta = d.get('_eta_str', '00:00').replace('\x1b[0;33m', '').replace('\x1b[0m', '').strip()
            
            total_bytes = d.get('_total_bytes_str') or d.get('_total_bytes_estimate_str', 'Unknown')
            if isinstance(total_bytes, str):
                total_bytes = total_bytes.replace('\x1b[0;94m', '').replace('\x1b[0m', '').strip()
            
            self.callback("progress", {"title": title, "percent": percent, "speed": speed, "eta": eta, "total": total_bytes}, self.task_card)

    def _pytube_hook(self, stream, chunk, bytes_remaining):
        """pytube এর প্রগ্রেস ডাটা ক্যালকুলেট করা (Pause/Cancel লজিক সহ)"""
        if self.is_cancelled:
            # pytube এর ক্ষেত্রে ডাউনলোড বন্ধ করার জন্য এটিই যথেষ্ট
            # এটি একটি ব্যতিক্রম তৈরি করবে যা আমরা প্রধান ফাংশনে ধরব
            raise Exception("PAUSED by user")
            
        total = stream.filesize
        percent = ((total - bytes_remaining) / total) * 100
        self.callback("progress", {"title": "Pytube Fallback...", "percent": f"{percent:.1f}%", "speed": "N/A", "eta": "N/A", "total": f"{total/(1024*1024):.1f}MB"}, self.task_card)