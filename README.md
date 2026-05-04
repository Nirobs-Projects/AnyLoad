# 🚀 AnyLoad - Android YouTube/Media Downloader

A powerful Android app built with Python, Kivy, and KivyMD for downloading YouTube videos and audio with advanced features.

## ✨ Features

- 📥 **Multiple Download Modes**
  - Auto Best Quality
  - Manual Quality Selection (8K, 4K, 1080p, 720p, 480p, 360p)
  - Audio Only (MP3)
  - Playlist Download
  - Bangla Subtitle Support

- 📚 **Library Management**
  - Video & Audio Library
  - Thumbnail Generation
  - Play Media Directly
  - File Rename & Delete

- 🔒 **Vault System**
  - PIN Protection
  - Security Questions for Recovery
  - Private File Storage

- 🎵 **Audio Features**
  - Audio Trimmer (Ringtone Maker)
  - ID3 Tag Support
  - Album Art Extraction

## 🛠️ Tech Stack

- **Framework**: Kivy 2.3.1, KivyMD 1.2.0
- **Build Tool**: Buildozer
- **Download Engines**: yt-dlp, pytube
- **Audio Processing**: mutagen
- **Target**: Android API 33 (Min API 21)

## 📋 Requirements

```
python3
kivy==2.3.1
kivymd==1.2.0
yt-dlp
pytube
certifi
mutagen
pillow
pyjnius
sqlite3
libffi
openssl
```

## 🔧 Build Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install buildozer
```

### 2. Build APK
```bash
buildozer android debug
```

### 3. Deploy to Device
```bash
buildozer android deploy run
```

## 🐛 Bug Fixes (v1.1.0)

### Critical Fixes
- ✅ Fixed KivyMD version mismatch (v2.0 → v1.2.0)
- ✅ Removed FFmpeg dependency for Android compatibility
- ✅ Added 32-bit architecture support (armeabi-v7a)
- ✅ Added missing dependencies (sqlite3, libffi, openssl)
- ✅ Fixed graphics context for Unisoc devices
- ✅ Implemented background app persistence

### UI/UX Improvements
- ✅ Fixed layout squashing in ScrollView
- ✅ Added Bengali font support
- ✅ Improved download progress tracking
- ✅ Enhanced error handling

## 📱 Supported Devices

- **Architecture**: ARM64 (64-bit) & ARMv7 (32-bit)
- **Android Version**: 5.0+ (API 21+)
- **Tested On**: Realme Note 50 (Unisoc)

## 📂 Project Structure

```
AnyLoad/
├── main.py              # Main application entry
├── ui.kv                # KivyMD UI layout
├── buildozer.spec       # Build configuration
├── requirements.txt     # Python dependencies
├── assets/              # Images, fonts, icons
├── db/                  # Database manager
├── downloader/          # Download engines
├── features/            # Audio trimmer, vault, etc.
└── utils/               # Storage, permissions, helpers
```

## 🔐 Permissions

- `INTERNET` - Download media
- `READ_EXTERNAL_STORAGE` - Access files
- `WRITE_EXTERNAL_STORAGE` - Save downloads
- `MANAGE_EXTERNAL_STORAGE` - Android 11+ storage

## 📝 License

This project is for educational purposes.

## 👨‍💻 Developer

**Nirob**  
Version: 1.1.0  
Date: May 04, 2026

---

**Note**: This app uses yt-dlp and pytube for downloading. Ensure compliance with YouTube's Terms of Service.
