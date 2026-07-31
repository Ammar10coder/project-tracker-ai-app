import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

import paths
from app import config


def _client_secrets_path() -> str:
    """Prefer a user-supplied client_secrets.json in the config folder, else
    fall back to the one bundled with the app."""
    if os.path.exists(paths.CLIENT_SECRETS_FILE):
        return paths.CLIENT_SECRETS_FILE
    return paths.CLIENT_SECRETS_DEFAULT


class DriveManager:
    """Class wrapper for Google Drive management and folder structure hierarchy."""

    def __init__(self):
        self.drive = self._get_drive_instance()

    def _get_drive_instance(self) -> GoogleDrive:
        """Handles Google Drive authentication smoothly with offline access."""
        gauth = GoogleAuth()
        gauth.settings['get_refresh_token'] = True
        gauth.LoadClientConfigFile(_client_secrets_path())

        creds_file = paths.DRIVE_CREDS_FILE
        if os.path.exists(creds_file):
            gauth.LoadCredentialsFile(creds_file)

        if gauth.credentials is None:
            print("First-time setup: opening browser for Google Drive login...")
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            print("Access token expired. Refreshing silently...")
            try:
                gauth.Refresh()
            except Exception as e:
                print(f"Refresh failed ({e}). Re-authenticating...")
                if os.path.exists(creds_file):
                    os.remove(creds_file)
                gauth.LocalWebserverAuth()
        else:
            gauth.Authorize()

        gauth.SaveCredentialsFile(creds_file)
        return GoogleDrive(gauth)

    def get_or_create_folder(self, folder_name: str, parent_id: str = None) -> str:
        query = f"title = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        else:
            query += " and 'root' in parents"

        folder_list = self.drive.ListFile({'q': query}).GetList()
        if folder_list:
            return folder_list[0]['id']

        folder_metadata = {'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_id:
            folder_metadata['parents'] = [{'id': parent_id}]

        folder = self.drive.CreateFile(folder_metadata)
        folder.Upload()
        return folder['id']

    def upload_file(self, file_path: str, company_name: str = None, person_name: str = "Ammar") -> str:
        """Uploads a file to Google Drive under: [target folder] / [person_name] / [filename]"""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None

        cfg = config.load()
        target_folder_id = cfg.get("DRIVE_TARGET_FOLDER_ID") or None

        employee_folder_id = self.get_or_create_folder(person_name, parent_id=target_folder_id)

        file_name = os.path.basename(file_path)
        gfile = self.drive.CreateFile({
            'title': file_name,
            'parents': [{'id': employee_folder_id}]
        })
        gfile.SetContentFile(file_path)
        gfile.Upload()

        print(f"Uploaded '{file_name}' to Drive folder {target_folder_id or 'root'}/{person_name}/")
        return gfile['id']

    def upload_employee_report(self, file_path: str, employee_name: str = "Ammar", company_name: str = None) -> str:
        return self.upload_file(file_path=file_path, company_name=company_name, person_name=employee_name)


def get_drive_instance() -> GoogleDrive:
    return DriveManager().drive


def is_drive_connected() -> bool:
    return os.path.exists(paths.DRIVE_CREDS_FILE)
