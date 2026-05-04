from kivy.utils import platform

class PermissionHandler:
    @staticmethod
    def request_all():
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            permissions = [
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.INTERNET
            ]
            request_permissions(permissions)