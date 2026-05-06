import os
from google_auth_oauthlib.flow import InstalledAppFlow

# Права на управление календарем и задачами
SCOPES = [
    'https://www.googleapis.com/auth/calendar', 
    'https://www.googleapis.com/auth/tasks'
]

def main():
    if os.path.exists('token.json'):
        print("Файл token.json уже существует!")
        return

    # Читаем credentials.json и запускаем браузер
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    # Сохраняем токен
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    print("Супер! Файл token.json успешно создан.")

if __name__ == '__main__':
    main()