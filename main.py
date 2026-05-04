# -*- coding: utf-8 -*-
import os
import sys

# Graphics fix for 32-bit devices
os.environ['KIVY_GRAPHICS'] = 'sdl2'

import subprocess
import hashlib
import threading
import re
from kivy.config import Config
from kivy.core.text import LabelBase
from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.card import MDCard
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ObjectProperty
from kivy.core.window import Window
from kivy.clock import mainthread, Clock
from kivy.utils import platform
from kivy.core.clipboard import Clipboard
from kivy.animation import Animation
from db.manager import db
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.label import MDLabel
from kivymd.uix.progressindicator import MDLinearProgressIndicator
from kivymd.uix.fitimage import FitImage
from kivymd.uix.boxlayout import MDBoxLayout
from utils.storage import StorageManager
from utils.permissions import PermissionHandler
from downloader import DownloadManager
from features.audio_trimmer import AudioTrimmer
from features.vault_manager import VaultManager
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivy.uix.modalview import ModalView
from kivymd.uix.scrollview import MDScrollView
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

# ১. Kivy-কে UTF-8 এবং ইউনিকোড হ্যান্ডেল করতে বাধ্য করা
Config.set('kivy', 'text_resource_encoding', 'utf-8')

Window.size = (360, 800)

def register_universal_font():
    # ইউনিকোড সাপোর্ট করে এমন ফন্ট পাথ (আপনার পিসিতে bangla.ttf ই যথেষ্ট)
    font_path = os.path.join(os.path.dirname(__file__), "assets", "bangla.ttf")
    
    if os.path.exists(font_path):
        # Kivy-র ডিফল্ট 'Roboto' ফ্যামিলিকে আমাদের ইউনিকোড ফন্ট দিয়ে ওভাররাইড করা
        # এতে করে অ্যাপের যেখানেই 'Roboto' কল হবে, সেখানে আমাদের ফন্ট কাজ করবে
        LabelBase.register(name='Roboto', 
                           fn_regular=font_path,
                           fn_bold=font_path,
                           fn_italic=font_path,
                           fn_bolditalic=font_path)
        print(f"[*] Unicode Font Registered Successfully: {font_path}")
    else:
        print("[!] Warning: assets/bangla.ttf not found. Bengali might break.")

register_universal_font()

class ThumbnailGenerator:
    @staticmethod
    def generate(video_path):
        # FFmpeg removed - using default thumbnail
        return "assets/default_vedio.png"

    @staticmethod
    def get_audio_thumb(audio_path):
        """অডিও ফাইল থেকে কভার ছবি (APIC) বের করার ফাংশন"""
        thumbnail_dir = StorageManager.get_thumbnail_path()
        os.makedirs(thumbnail_dir, exist_ok=True)
        filename = hashlib.md5(audio_path.encode()).hexdigest() + "_audio.jpg"
        thumbnail_path = os.path.join(thumbnail_dir, filename)

        if not os.path.exists(thumbnail_path):
            try:
                from mutagen.mp3 import MP3
                from mutagen.id3 import ID3
                
                audio = MP3(audio_path, ID3=ID3)
                for tag in audio.tags.values():
                    if tag.FrameID == 'APIC':
                        with open(thumbnail_path, 'wb') as img:
                            img.write(tag.data)
                        return thumbnail_path
            except Exception as e:
                print(f"[!] Audio Thumb Error: {e}")
                pass
            # যদি কভার ছবি না পায় বা এক্সট্র্যাক্ট করতে না পারে, তবে ডিফল্ট ছবি দেখাবে
            return "assets/default_audio.png"
        return thumbnail_path

class ActionCard(MDCard):
    title = StringProperty()
    icon_name = StringProperty()


class TaskCard(MDCard):
    filename = StringProperty("Preparing download...")
    progress_value = NumericProperty(0)
    status_text = StringProperty("Preparing download...")
    total_size = StringProperty("")
    is_paused = BooleanProperty(False)
    url = StringProperty("")
    mode = StringProperty("")
    manager_ref = ObjectProperty(None, allownone=True)
    file_type = StringProperty("video")

    def toggle_pause(self):
        app = MDApp.get_running_app()
        if not self.is_paused:
            if self.manager_ref:
                self.manager_ref.pause()
            self.is_paused = True
            self.status_text = "Paused"
            self.ids.pause_button.icon = "play"
        else:
            self.is_paused = False
            self.status_text = "Downloading..."
            self.ids.pause_button.icon = "pause"
            app._start_engine(self)

    def cancel_task(self):
        if self.manager_ref:
            self.manager_ref.cancel()
        MDApp.get_running_app().remove_task(self)


class LibraryCard(MDCard):
    filename = StringProperty()
    thumbnail_path = StringProperty()
    filepath = StringProperty()
    file_type = StringProperty("video")

    def on_release(self):
        self.play_media()

    def play_media(self):
        try:
            if platform == 'android':
                from jnius import autoclass, cast
                StrictMode = autoclass('android.os.StrictMode')
                StrictMode.setVmPolicy(autoclass('android.os.StrictMode$VmPolicy$Builder')().build())
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                File = autoclass('java.io.File')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                intent = Intent(Intent.ACTION_VIEW)
                uri = Uri.fromFile(File(self.filepath))
                mime = "video/*" if self.filepath.lower().endswith(('.mp4', '.mkv', '.webm')) else "audio/*"
                intent.setDataAndType(uri, mime)
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                cast('android.app.Activity', PythonActivity.mActivity).startActivity(intent)
            else:
                if sys.platform.startswith('linux'):
                    subprocess.Popen(['xdg-open', self.filepath])
                elif sys.platform == 'win32':
                    os.startfile(self.filepath)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', self.filepath])
        except Exception as e:
            print(f"[!] Play Media Error: {e}")


class AnyLoadApp(MDApp):
    current_pin = ""
    current_action = ""  # "LOGIN" or "MOVING_FILE"
    pending_file_move = {"filepath": "", "filename": ""}  # ফাইল মুভের জন্য পেন্ডিং ডাটা
    security_questions = [
        "What is your favorite color?",
        "What was the name of your first school?",
        "Who is your childhood hero?",
        "What is your mother's maiden name?",
        "What city were you born in?"
    ]

    def build(self):
        self._configure_console_encoding()
        self._register_unicode_font()
        
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.accent_palette = "Teal"
        
        self.base_path = StorageManager.setup_folders()
        os.makedirs("assets", exist_ok=True)
        
        return Builder.load_file("ui.kv")

    def _configure_console_encoding(self):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    def _register_unicode_font(self):
        pass
            
    def on_start(self):
        PermissionHandler.request_all()
        self.refresh_library()
        Clock.schedule_once(self.start_animations, 0.5)
        Clock.schedule_once(self.check_clipboard, 1)

    def on_resume(self):
        Clock.schedule_once(lambda dt: self.check_clipboard(), 0.4)
        return True  # Critical: Prevents Android from killing the app

    def on_pause(self):
        return True  # Critical: Allows app to run in background

    def start_animations(self, dt):
        pass # Optional pulse logic

    def check_clipboard(self, *args):
        try:
            text = Clipboard.paste()
            if text and ("http://" in text or "https://" in text):
                self.show_toast("Link detected in clipboard! Paste it.")
        except Exception as e:
            print(f"[!] Clipboard check error: {e}")

    def paste_from_clipboard(self):
        try:
            text = Clipboard.paste()
            if text:
                self.root.ids.url_input.text = text
                self.show_toast("Link pasted successfully!")
            else:
                self.show_toast("Clipboard is empty")
        except Exception as e:
            print(f"[!] Paste error: {e}")
            self.show_toast("Failed to paste from clipboard")

    def show_toast(self, text):
        print(f"[TOAST] {text}")
        if platform == 'android':
            try:
                from kivymd.toast import toast
                toast(text)
            except Exception:
                pass

    # ── Download flow ─────────────────────────────────────────────────────────

    def process_download(self, mode_title):
        try:
            url = self.root.ids.url_input.text.strip()
        except Exception:
            self.show_toast("Please paste a valid URL first")
            return
        if not url:
            self.show_toast("Please paste a valid URL first")
            return
        if mode_title == "Choose Quality Manually":
            self.root.ids.screen_manager.current = "quality_select"
            return
        self._initiate_download(url, mode_title)

    def start_manual_download(self, quality):
        try:
            url = self.root.ids.url_input.text.strip()
        except Exception:
            self.show_toast("Please paste a valid URL first")
            return
        if not url:
            self.show_toast("Please paste a valid URL first")
            return
        self._initiate_download(url, f"Choose Quality Manually ({quality})")

    def _initiate_download(self, url, mode_title):
        self.root.ids.screen_manager.current = "tasks"
        task_container = self.root.ids.task_container
        try:
            task_container.remove_widget(self.root.ids.empty_task_label)
        except Exception:
            pass
            
        # ইনস্ট্যান্ট UI ফিডব্যাক (Preparing দেখাবে না)
        new_task = TaskCard(
            url=url, mode=mode_title,
            filename="Connecting...",
            status_text="Speed: -- KB/s • ETA: --:--",
            total_size="-- MB",
            progress_value=0
        )
        task_container.add_widget(new_task)
        self._start_engine(new_task)

    def _start_engine(self, task_card):
        """এই ফাংশনটি মুছে গিয়েছিল, এটি আবার যুক্ত করা হলো"""
        manager = DownloadManager(
            url=task_card.url,
            mode=task_card.mode,
            base_path=self.base_path,
            callback=lambda t, d, tc=task_card: self.engine_callback(t, d, tc),
            task_card=task_card
        )
        task_card.manager_ref = manager
        import threading
        threading.Thread(target=manager.run, daemon=True).start()

    @mainthread
    def engine_callback(self, msg_type, data, task_card):
        import re
        # ANSI কালার কোড রিমুভ করার জাদুকরী ফাংশন
        def clean_text(text):
            if not isinstance(text, str): return text
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            return ansi_escape.sub('', text).strip()

        if msg_type == "status":
            task_card.filename = clean_text(data)
            
        elif msg_type == "progress":
            task_card.filename = data.get('title', '')
            task_card.status_text = f"Speed: {data.get('speed','')} • ETA: {data.get('eta','')}"
            task_card.total_size = data.get('total', '')
            
            try:
                new_percent = float(data.get('percent', '0').replace('%', ''))
                # জিরো জাম্প ফিক্স: শুধুমাত্র যখন পজ করা নেই তখনই আপডেট হবে
                if not task_card.is_paused:
                    task_card.progress_value = new_percent
            except Exception:
                pass
                
        elif msg_type == "finished":
            task_card.progress_value = 100
            task_card.status_text = "Completed ✓"
            task_card.md_bg_color = (0, 0.18, 0.1, 1)
            fpath = data.get("filepath")
            if fpath and fpath.lower().endswith(('.mp4', '.mkv', '.webm')):
                ThumbnailGenerator.generate(fpath)
            Clock.schedule_once(lambda dt: self.remove_task(task_card), 2)
            Clock.schedule_once(lambda dt: self.refresh_library(), 2.5)
            
        elif msg_type == "failed":
            task_card.status_text = "Failed. Please try again."
            task_card.md_bg_color = (0.28, 0, 0, 1)
            
            
    def remove_task(self, task_card):
        try:
            self.root.ids.task_container.remove_widget(task_card)
        except Exception:
            pass

    # ── Library ───────────────────────────────────────────────────────────────

    @mainthread
    def refresh_library(self):
        v_dir = os.path.join(self.base_path, "Videos")
        a_dir = os.path.join(self.base_path, "Audio")
        video_data, audio_data = [],[]
        if os.path.exists(v_dir):
            for f in sorted(os.listdir(v_dir), reverse=True):
                if f.lower().endswith(('.mp4', '.mkv', '.webm')):
                    fp = os.path.join(v_dir, f)
                    video_data.append({
                        'filename': f,
                        'thumbnail_path': ThumbnailGenerator.generate(fp),
                        'filepath': fp,
                        'file_type': 'video'
                    })
        if os.path.exists(a_dir):
            for f in sorted(os.listdir(a_dir), reverse=True):
                if f.lower().endswith(('.mp3', '.m4a', '.wav')):
                    fp = os.path.join(a_dir, f)
                    
                    # হার্ডকোড ছবির বদলে এখন আসল ছবি বের করবে
                    tp = ThumbnailGenerator.get_audio_thumb(fp) 
                    
                    audio_data.append({
                        'filename': f,
                        'thumbnail_path': tp,
                        'filepath': fp,
                        'file_type': 'audio'
                    })
        try:
            self.root.ids.video_rv.data = video_data
            self.root.ids.audio_rv.data = audio_data
        except Exception as e:
            print(f"[!] Library sync error: {e}")
# ── Safe Library Menu & Dialogs ──────────────────────────────────────────

    def open_library_menu(self, lib_card):
        from kivy.uix.modalview import ModalView
        self.menu_view = ModalView(size_hint=(0.8, None), height="280dp", background_color=(0,0,0,0))
        card = MDCard(orientation="vertical", padding="15dp", spacing="10dp", radius=20, md_bg_color=(0.12, 0.12, 0.12, 1))
        
        # এখানে 'font_name' হিসেবে আপনার বাংলা ফন্টের নামটি ব্যবহার করুন (যেমন 'Bangla' অথবা 'Roboto')
        title = MDLabel(text="Options", font_name="Roboto", style="TitleMedium", theme_text_color="Custom", text_color=(0, 0.8, 0.7, 1), size_hint_y=None, height="30dp", halign="center")
        card.add_widget(title)

        def make_btn(text, action):
            btn = MDButton(style="text", on_release=lambda x: self._menu_action(lib_card, action), size_hint_x=1)
            # এখানেও font_name যোগ করুন
            btn.add_widget(MDButtonText(text=text, font_name="Roboto", theme_text_color="Custom", text_color=(1,1,1,1)))
            return btn
        
        # ... (বাকি বাটনগুলো আগের মতোই থাকবে) ...
        btn_box = MDBoxLayout(orientation="vertical", spacing="2dp", adaptive_height=True)
        btn_box.add_widget(make_btn("▶ Play Media", 'play'))
        if lib_card.file_type == 'audio':
            btn_box.add_widget(make_btn("✂ Trim Audio", 'trim'))
        btn_box.add_widget(make_btn("✏️ Rename", 'rename')) # নতুন ফিচার
        btn_box.add_widget(make_btn("🛡️ Move to Vault", 'vault'))
        btn_box.add_widget(make_btn("🗑️ Delete File", 'delete'))
        
        card.add_widget(btn_box)
        self.menu_view.add_widget(card)
        self.menu_view.open()

    def _menu_action(self, lib_card, action):
        if hasattr(self, 'menu_view'): self.menu_view.dismiss()
        if action == 'play': lib_card.play_media()
        elif action == 'trim': self.show_trim_dialog(lib_card.filepath)
        elif action == 'vault': self.confirm_vault_move(lib_card.filepath, lib_card.filename)
        elif action == 'delete': self.delete_library_file(lib_card)
        elif action == 'rename': self.show_rename_dialog(lib_card)

    def show_rename_dialog(self, lib_card):
        """ফাইল রিনেম করার ডায়ালগ"""
        view = ModalView(size_hint=(0.85, None), height="200dp", background_color=(0,0,0,0))
        card = MDCard(orientation="vertical", padding="20dp", spacing="15dp", radius=20, md_bg_color=(0.12, 0.12, 0.12, 1))
        
        name_field = MDTextField(hint_text="New Name", text=os.path.splitext(lib_card.filename)[0])
        card.add_widget(MDLabel(text="Rename File", style="TitleMedium", theme_text_color="Custom", text_color=(0, 0.8, 0.7, 1), size_hint_y=None, height="30dp"))
        card.add_widget(name_field)
        
        btn = MDButton(style="filled", on_release=lambda x: self._execute_rename(lib_card, name_field.text, view), pos_hint={"center_x": .5})
        btn.add_widget(MDButtonText(text="Rename"))
        card.add_widget(btn)
        
        view.add_widget(card)
        view.open()

    def _execute_rename(self, lib_card, new_name, view):
        try:
            ext = os.path.splitext(lib_card.filepath)[1]
            new_path = os.path.join(os.path.dirname(lib_card.filepath), new_name + ext)
            os.rename(lib_card.filepath, new_path)
            self.refresh_library()
            self.show_toast("Renamed successfully")
            view.dismiss()
        except Exception as e:
            self.show_toast("Rename failed")
            print(f"[!] Rename error: {e}")

    def _menu_action(self, lib_card, action):
        if hasattr(self, 'menu_view'):
            self.menu_view.dismiss()
            
        if action == 'play': lib_card.play_media()
        elif action == 'trim': self.show_trim_dialog(lib_card.filepath)
        elif action == 'vault': self.verify_before_move(lib_card.filepath, lib_card.filename)
        elif action == 'details': self.show_file_details(lib_card)
        elif action == 'delete': self.delete_library_file(lib_card)

    def show_file_details(self, lib_card):
        self.details_view = ModalView(size_hint=(0.85, None), height="200dp", background_color=(0,0,0,0))
        card = MDCard(orientation="vertical", padding="20dp", spacing="15dp", radius=20, md_bg_color=(0.1, 0.1, 0.1, 1))
        
        card.add_widget(MDLabel(text="File Details", style="TitleMedium", theme_text_color="Custom", text_color=(0, 0.8, 0.7, 1), size_hint_y=None, height="30dp"))
        card.add_widget(MDLabel(text=f"Name: {lib_card.filename}\nPath: {lib_card.filepath}", style="BodyMedium", theme_text_color="Custom", text_color=(1, 1, 1, 1)))
        
        btn = MDButton(style="filled", on_release=lambda x: self.details_view.dismiss(), pos_hint={"center_x": .5})
        btn.add_widget(MDButtonText(text="Close"))
        card.add_widget(btn)
        
        self.details_view.add_widget(card)
        self.details_view.open()

    def show_trim_dialog(self, filepath):
        if not filepath.lower().endswith(('.mp3', '.m4a', '.wav')):
            self.show_toast("Trim available only for audio files")
            return
            
        self.trim_view = ModalView(size_hint=(0.85, None), height="250dp", background_color=(0,0,0,0))
        card = MDCard(orientation="vertical", padding="20dp", spacing="15dp", radius=20, md_bg_color=(0.1, 0.1, 0.1, 1))
        
        card.add_widget(MDLabel(text="Trim Audio (Ringtone)", style="TitleMedium", theme_text_color="Custom", text_color=(0, 0.8, 0.7, 1), size_hint_y=None, height="30dp"))
        
        self.trim_start_field = MDTextField(hint_text="Start (seconds)", text="0")
        self.trim_end_field = MDTextField(hint_text="End (seconds)", text="30")
        card.add_widget(self.trim_start_field)
        card.add_widget(self.trim_end_field)
        
        btn_box = MDBoxLayout(orientation="horizontal", spacing="10dp", size_hint_y=None, height="40dp")
        
        btn_cancel = MDButton(style="outlined", on_release=lambda x: self.trim_view.dismiss())
        btn_cancel.add_widget(MDButtonText(text="Cancel"))
        
        btn_trim = MDButton(style="filled", on_release=lambda x: self._confirm_trim(filepath))
        btn_trim.add_widget(MDButtonText(text="Trim"))
        
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_trim)
        card.add_widget(btn_box)
        
        self.trim_view.add_widget(card)
        self.trim_view.open()

    def _confirm_trim(self, filepath):
        try:
            start = float(self.trim_start_field.text or 0)
            end = float(self.trim_end_field.text or 0)
        except ValueError:
            self.show_toast("Enter valid start and end times")
            return
            
        if end <= start:
            self.show_toast("End time must be greater than start time")
            return
            
        self.trim_view.dismiss()
        
        output_dir = os.path.join(self.base_path, 'Ringtones')
        os.makedirs(output_dir, exist_ok=True)
        
        from features.audio_trimmer import AudioTrimmer
        result = AudioTrimmer.trim(filepath, start, end, output_dir)
        
        self.show_toast("Trimmed audio saved" if result else "Trim failed")
        if result:
            self.refresh_library()
    # ── Vault ─────────────────────────────────────────────────────────────────

    def load_vault_contents(self):
        try:
            files = db.get_vault_files()
            vault_data = []
            for name, path, ftype in files:
                if os.path.exists(path):
                    # থাম্বনেইল জেনারেট করা
                    tp = ThumbnailGenerator.generate(path) if ftype == 'video' else "assets/default_audio.png"
                    vault_data.append({
                        'filename': name,
                        'thumbnail_path': tp,
                        'filepath': path,
                        'file_type': ftype
                    })
            
            # ভল্ট স্ক্রিন আপডেট
            self.root.ids.vault_rv.data = vault_data
            
            # পিন প্যাড হাইড করে লিস্ট দেখানো
            self.root.ids.pin_pad_box.opacity = 0
            self.root.ids.pin_pad_box.disabled = True
            self.root.ids.vault_rv.opacity = 1
            self.root.ids.vault_rv.disabled = False
            
            print(f"[*] Found {len(vault_data)} files in Vault.")
        except Exception as e:
            print(f"[!] Vault load error: {e}")

    def vault_pin_input(self, digit):
        if digit == 'C':
            self.current_pin = ""
        elif len(self.current_pin) < 4:
            self.current_pin += digit
        try:
            self.root.ids.pin_display.text = "*" * len(self.current_pin)
        except Exception:
            pass

    def vault_authorize(self):
        if len(self.current_pin) < 4:
            self.root.ids.vault_msg.text = "PIN must be 4 digits!"
            return
        try:
            if not db.is_pin_set():
                # প্রথমবার PIN সেট করার সময় সিকিউরিটি প্রশ্ন দেখাও
                self.show_security_questions_setup()
            elif db.check_pin(self.current_pin):
                if self.current_action == "MOVING_FILE":
                    # ফাইল মুভ করার জন্য PIN চেক হয়েছে
                    self._execute_vault_move()
                else:
                    # নর্মাল লগইন
                    self.root.ids.vault_msg.text = "Access Granted!"
                    self.root.ids.vault_status_icon.icon = "shield-check"
                    self.root.ids.vault_status_icon.text_color = (0, 0.85, 0.77, 1)
                    self.root.ids.pin_pad_box.opacity = 0
                    self.root.ids.pin_pad_box.disabled = True
                    self.root.ids.vault_rv.opacity = 1
                    self.root.ids.vault_rv.disabled = False
                    self.load_vault_contents()
                self.current_pin = ""
                self.root.ids.pin_display.text = ""
            else:
                self.root.ids.vault_msg.text = "Wrong PIN! Try again."
                self.current_pin = ""
                self.root.ids.pin_display.text = ""
        except Exception as e:
            print(f"[!] Vault auth error: {e}")
            
    # main.py এর একদম শেষে এই ফাংশনটি অবশ্যই থাকতে হবে
    def delete_library_file(self, lib_card):
        try:
            if os.path.exists(lib_card.filepath):
                os.remove(lib_card.filepath)
                self.show_toast("Deleted successfully")
                self.refresh_library()
        except Exception as e:
            print(f"[!] Delete error: {e}")

    # সিকিউরিটি প্রশ্ন সেটআপ (প্রথমবার PIN সেট করার সময়)
    def show_security_questions_setup(self):
        self.sq_view = ModalView(size_hint=(0.9, None), height="500dp", background_color=(0,0,0,0.8))
        card = MDCard(orientation="vertical", padding="20dp", spacing="15dp", radius=20, md_bg_color=(0.1, 0.1, 0.1, 1))
        
        card.add_widget(MDLabel(text="Setup Security Questions", style="TitleMedium", theme_text_color="Custom", text_color=(0, 0.8, 0.7, 1), size_hint_y=None, height="30dp"))
        card.add_widget(MDLabel(text="Select 3 questions and provide answers for PIN recovery", style="BodySmall", theme_text_color="Secondary", size_hint_y=None, height="40dp"))
        
        scroll = MDScrollView(size_hint_y=0.7)
        content = MDBoxLayout(orientation="vertical", spacing="10dp", adaptive_height=True, padding="5dp")
        
        self.sq_fields = []
        for i in range(3):
            content.add_widget(MDLabel(text=f"Question {i+1}: {self.security_questions[i]}", style="BodySmall", size_hint_y=None, height="25dp"))
            field = MDTextField(hint_text=f"Answer {i+1}", mode="outlined")
            content.add_widget(field)
            self.sq_fields.append((self.security_questions[i], field))
        
        scroll.add_widget(content)
        card.add_widget(scroll)
        
        btn = MDButton(style="filled", on_release=lambda x: self._save_security_setup(), pos_hint={"center_x": .5})
        btn.add_widget(MDButtonText(text="Save & Continue"))
        card.add_widget(btn)
        
        self.sq_view.add_widget(card)
        self.sq_view.open()

    def _save_security_setup(self):
        qa_list = [(q, f.text) for q, f in self.sq_fields]
        if any(not a.strip() for _, a in qa_list):
            self.show_toast("Please answer all questions")
            return
        
        db.save_security_questions(qa_list)
        db.set_pin(self.current_pin)
        self.sq_view.dismiss()
        self.root.ids.vault_msg.text = "PIN & Security Setup Complete!"
        self.current_pin = ""
        self.root.ids.pin_display.text = ""
        self.show_toast("Security setup successful!")

    # Forgot PIN - সিকিউরিটি প্রশ্ন যাচাই
    def show_forgot_pin_dialog(self):
        if not db.has_security_questions():
            self.show_toast("No recovery questions set")
            return
        
        questions = db.get_security_questions()
        self.recovery_view = ModalView(size_hint=(0.9, None), height="450dp", background_color=(0,0,0,0.8))
        card = MDCard(orientation="vertical", padding="20dp", spacing="15dp", radius=20, md_bg_color=(0.1, 0.1, 0.1, 1))
        
        card.add_widget(MDLabel(text="PIN Recovery", style="TitleMedium", theme_text_color="Custom", text_color=(0, 0.8, 0.7, 1), size_hint_y=None, height="30dp"))
        card.add_widget(MDLabel(text="Answer your security questions", style="BodySmall", theme_text_color="Secondary", size_hint_y=None, height="30dp"))
        
        scroll = MDScrollView(size_hint_y=0.65)
        content = MDBoxLayout(orientation="vertical", spacing="10dp", adaptive_height=True, padding="5dp")
        
        self.recovery_fields = []
        for i, q in enumerate(questions):
            content.add_widget(MDLabel(text=f"Q{i+1}: {q}", style="BodySmall", size_hint_y=None, height="30dp"))
            field = MDTextField(hint_text=f"Answer {i+1}", mode="outlined")
            content.add_widget(field)
            self.recovery_fields.append(field)
        
        scroll.add_widget(content)
        card.add_widget(scroll)
        
        btn_box = MDBoxLayout(orientation="horizontal", spacing="10dp", size_hint_y=None, height="40dp")
        btn_cancel = MDButton(style="outlined", on_release=lambda x: self.recovery_view.dismiss())
        btn_cancel.add_widget(MDButtonText(text="Cancel"))
        btn_verify = MDButton(style="filled", on_release=lambda x: self._verify_recovery())
        btn_verify.add_widget(MDButtonText(text="Verify"))
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_verify)
        card.add_widget(btn_box)
        
        self.recovery_view.add_widget(card)
        self.recovery_view.open()

    def _verify_recovery(self):
        answers = [f.text for f in self.recovery_fields]
        if db.verify_security_questions(answers):
            self.recovery_view.dismiss()
            self.show_toast("Verification successful! Set new PIN")
            self.root.ids.vault_msg.text = "Enter New PIN"
            self.current_pin = ""
            self.root.ids.pin_display.text = ""
            # PIN রিসেট করার জন্য ডাটাবেস থেকে পুরনো PIN মুছে দাও
            db.cursor.execute("DELETE FROM settings WHERE key='vault_pin'")
            db.conn.commit()
        else:
            self.show_toast("Wrong answers! Try again")

    # ফাইল মুভ করার আগে PIN যাচাই
    def verify_before_move(self, filepath, filename):
        if not db.is_pin_set():
            self.show_toast("Please set a PIN first in Vault")
            return
        
        self.current_action = "MOVING_FILE"
        self.pending_file_move = {"filepath": filepath, "filename": filename}
        self.root.ids.screen_manager.current = "vault"
        self.root.ids.vault_msg.text = "Enter PIN to move file"

    def _execute_vault_move(self):
        filepath = self.pending_file_move["filepath"]
        filename = self.pending_file_move["filename"]
        
        try:
            vault_dir = os.path.join(self.base_path, "Vault")
            os.makedirs(vault_dir, exist_ok=True)
            new_path = os.path.join(vault_dir, filename)
            
            # ফাইল মুভ করো (ডিলিট নয়, মুভ)
            os.rename(filepath, new_path)
            
            # ডাটাবেসে রেকর্ড রাখো
            file_type = "video" if filepath.lower().endswith(('.mp4', '.mkv', '.webm')) else "audio"
            db.add_to_vault(filename, new_path, file_type)
            
            self.show_toast("File moved to Vault successfully")
            self.refresh_library()
            self.current_action = ""
            self.pending_file_move = {"filepath": "", "filename": ""}
        except Exception as e:
            self.show_toast("Failed to move file")
            print(f"[!] Vault move error: {e}")
            
    def update_pin(self, new_pin):
        """ভল্ট আনলক থাকা অবস্থায় পিন আপডেট করার ফিচার"""
        db.set_pin(new_pin)
        self.show_toast("PIN Updated Successfully!")

    def show_forgot_pin_dialog(self):
        """Forgot PIN ক্লিক করলে কি করতে হবে তা এখানে লিখুন"""
        self.show_toast("Contact Admin to reset PIN!")


if __name__ == "__main__":
    AnyLoadApp().run()