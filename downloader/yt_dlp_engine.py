# -*- coding: utf-8 -*-
import os
import time
import re # ANSI ক্লিনিং এর জন্য

from utils.encoding_helper import sanitize_filename
from features.subtitle_handler import SubtitleHandler
from features.thumbnail_embedder import AudioThumbnailEmbedder

def clean_ansi(text):
    """টার্মিনালের কালার কোড রিমুভ করার সেন্ট্রাল ফাংশন"""
    if not isinstance(text, str):
        return text
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text).strip()

class YTDLPDownloader:
    def __init__(self, url, mode, base_path, progress_callback):
        self.url = url
        self.mode = mode
        self.base_path = base_path
        self.progress_callback = progress_callback
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self, safe=False):
        try:
            import yt_dlp
        except ImportError:
            return False, None, "yt-dlp missing"

        save_dir = os.path.join(self.base_path, "Videos" if "Audio" not in self.mode else "Audio")
        os.makedirs(save_dir, exist_ok=True)
        
        if "Playlist" in self.mode:
            os.makedirs(os.path.join(save_dir, "Playlists"), exist_ok=True)
            out_template = os.path.join(save_dir, 'Playlists', '%(playlist_title)s', '%(title)s.%(ext)s')
        else:
            out_template = os.path.join(save_dir, '%(title)s.%(ext)s')

        opts = {
            'logger': self._make_logger(),
            'progress_hooks':[self._ytdlp_hook],
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'outtmpl': out_template,
            'continuedl': True,
            'retries': 5,
            'fragment_retries': 3,
            'sleep_interval_requests': 1,
            'sleep_interval': 1,
            'ignoreerrors': False,
            'restrictfilenames': False,
            'encoding': 'utf-8',
            'prefer_ffmpeg': True,
            'format_sort': ['res', 'ext', 'fps', 'size'],
        }

        opts.update(SubtitleHandler.yt_dlp_options(self.mode))
        if "Audio" in self.mode:
            opts.update(AudioThumbnailEmbedder.yt_dlp_audio_options())
            
        if "Choose Quality" in self.mode:
            q_match = re.search(r'\((.*?)\)', self.mode)
            if q_match:
                q_str = q_match.group(1).upper()
                q_map = {"8K": "4320", "4K": "2160", "1080P": "1080", "720P": "720", "480P": "480", "360P": "360"}
                h = q_map.get(q_str, "1080")
                opts['format'] = f'bestvideo[height<={h}]+bestaudio/best'

        if safe:
            opts['sleep_interval'] = 2
            opts['sleep_interval_requests'] = 2
            opts['retries'] = 10

        retries = 3 if not safe else 5

        for attempt in range(1, retries + 1):
            opts['continuedl'] = True
            if self.is_cancelled:
                return False, None, "Cancelled"
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(self.url, download=True)
                    if self.is_cancelled:
                        return False, None, "Cancelled"
                    filename = ydl.prepare_filename(info)
                    filename = self._normalize_filepath(filename)
                    if "Audio" in self.mode:
                        filename = os.path.splitext(filename)[0] + ".mp3"
                    return True, filename, None
            except Exception as exc:
                if self.is_cancelled:
                    return False, None, "Cancelled"
                
                message = clean_ansi(str(exc))
                print(f"[yt-dlp attempt {attempt}] {message}")
                
                # === Subtitle Crash Fix: সাবটাইটেল এরর দিলে সাবটাইটেল বাদ দিয়ে আবার ট্রাই করবে ===
                if "subtitle" in message.lower():
                    print("[*] Subtitle blocked. Retrying video download without subtitles...")
                    opts.pop('writesubtitles', None)
                    opts.pop('writeautomaticsub', None)
                    opts['postprocessors'] = [pp for pp in opts.get('postprocessors', []) if pp.get('key') != 'FFmpegEmbedSubtitle']
                    continue

                if "416" in message:
                    opts['continuedl'] = False
                    continue
                
                if self._is_fatal_error(message):
                    return False, None, message # হাল ছেড়ে দেবে
                    
                time.sleep(attempt * 2)
                continue

        return False, None, "yt-dlp failed"
    def _make_logger(self):
        class YTDLLogger:
            def debug(self, msg):
                pass
            def warning(self, msg):
                pass
            def error(self, msg):
                print(f"[yt-dlp ERROR] {msg}")
        return YTDLLogger()

    def _ytdlp_hook(self, d):
        if self.is_cancelled:
            raise Exception("PAUSED")
        if d.get('status') != 'downloading':
            return

        title = d.get('info_dict', {}).get('title', 'Downloading...')
        percent = d.get('_percent_str', '0%')
        speed = d.get('_speed_str', '0KiB/s')
        eta = d.get('_eta_str', '00:00')

        total_bytes_approx = d.get('info_dict', {}).get('filesize_approx')
        if total_bytes_approx:
            total_bytes = f"{total_bytes_approx / (1024*1024):.2f}MB"
        else:
            total_bytes = d.get('_total_bytes_str') or d.get('_total_bytes_estimate_str', 'Unknown')

        self.progress_callback({
            'title': clean_ansi(title),
            'percent': clean_ansi(percent),
            'speed': clean_ansi(speed),
            'eta': clean_ansi(eta),
            'total': clean_ansi(total_bytes),
        })

    def _normalize_filepath(self, path):
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        filename = sanitize_filename(filename)
        if directory:
            os.makedirs(directory, exist_ok=True)
            return os.path.join(directory, filename)
        return filename

    def _is_retriable_error(self, message):
        content = message.lower()
        # "429" এবং "rate limit" রিমুভ করা হয়েছে যাতে ইনফিনিট লুপে না পড়ে
        return any(keyword in content for keyword in["temporarily unavailable", "timeout", "connection reset", "connection aborted", "blocked"])
    
    def _is_fatal_error(self, message):
        content = message.lower()
        # এই এররগুলো পেলে ইঞ্জিন আর ট্রাই করবে না
        return any(keyword in content for keyword in["429", "too many requests", "rate limit", "copyright", "private video", "unavailable"])