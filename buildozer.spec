[app]

# -------------------------------
# BASIC INFO
# -------------------------------
title = AnyLoad
package.name = anyload
package.domain = com.nexvexlabs
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,db,mp3,json
version = 1.1.0

# -------------------------------
# REQUIREMENTS (FIXED VERSION MISMATCH)
# -------------------------------
# এখানে শুধু python3 রাখা হয়েছে যাতে আপনার ডকার এনভায়রনমেন্টের সাথে ভার্সন মিলে যায়
requirements = python3,kivy==2.3.1,kivymd==1.2.0,yt-dlp,pytube,certifi,mutagen,pillow,pyjnius,sqlite3,libffi,openssl

# -------------------------------
# UI CONFIG
# -------------------------------
orientation = portrait
fullscreen = 0

# -------------------------------
# ASSETS
# -------------------------------
icon.filename = assets/logo.png
presplash.filename = assets/splash.png

# -------------------------------
# ANDROID CONFIG
# -------------------------------

# ডাউনলোডার অ্যাপের জন্য প্রয়োজনীয় সব পারমিশন
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE, READ_MEDIA_VIDEO, READ_MEDIA_AUDIO, POST_NOTIFICATIONS

# বিল্ড করার সময় অটোমেটিক লাইসেন্স একসেপ্ট করবে (API 33 ফিক্স)
android.accept_sdk_license = True

# Modern Android support
android.api = 33
android.minapi = 21
android.ndk = 25b

# শুধুমাত্র আধুনিক ফোনের জন্য বিল্ড করলে সময় বাঁচবে
android.archs = arm64-v8a,armeabi-v7a

# Performance & Features
android.copy_libs = 1
android.allow_backup = True
android.enable_androidx = True

# -------------------------------
# P4A CONFIG (STABLE)
# -------------------------------
# লিনাক্স কম্পাইলার এরর এড়াতে develop ব্রাঞ্চ ব্যবহার করা হয়েছে
p4a.branch = develop

# -------------------------------
# BUILD SETTINGS
# -------------------------------
[buildozer]
log_level = 2
warn_on_root = 1
