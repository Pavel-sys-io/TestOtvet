from config import cdn, debug, port, host, gpt_model
from pywebio.output import toast, put_html
from pywebio.input import input, TEXT, input_group
from pywebio import start_server
from urllib.parse import quote
from api import Client
from g4f.client import Client as gptClient
import g4f.errors as errors
from time import sleep
from google.auth import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os.path
from googleapiclient.discovery import build

class GmailClient():
    def __init__(self):
        self.credentials = None
        self.service = None
        

    def authenticate(self):
        creds_filename = 'token.pickle'
        SCOPES = ['https://www.googleapis.com/auth/gmail.compose']


        if os.path.exists(creds_filename):
            with open(creds_filename, 'rb') as token:
                self.credentials = pickle.load(token)
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.credentials = flow.run_local_server(port=0)
            with open(creds_filename, 'wb') as token:
                pickle.dump(self.credentials, token)
        self.service = build('gmail', 'v1', credentials=self.credentials)

    def get_emails(self):
        results = self.service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
        emails = results.get('messages', [])
        return emails

class app():
    c = Client()
    gmail = GmailClient()
    gc = gptClient()  # Создание объекта gptClient

    def run(self):
        print("Откройте в браузере ссылку ниже для старта приложения.")
        start_server(self.main, debug=debug, port=port, cdn=cdn, host=host)

    def send_gpt_response(self, message: str):
        while True:
            try:
                response = self.gc.chat.completions.create(
                    model=gpt_model,
                    messages=[
                        {"role": "user", "content": message}
                    ],
                )
                gpt_response = response.choices[0].message.content
                gpt_response=gpt_response.replace("####", "").replace("*", "")
                return gpt_response
            except errors.RetryProviderError:
                sleep(10)
            except Exception as e:
                print(f"Gpt answer error: {e}")
                raise Exception

    def format_question_for_chat(self, question, options, name, question_type_text):
        msg =  f"Помоги с тестом. название:{name}\nВопрос:\n{question}\n\n{question_type_text}\n Варианты ответа: "
        for answer in options:
            msg+=f"\n{answer['value']}"
        return msg

    def show_question(self, num, question, name):
        question_type_text = "Несколько вариантов ответа" if question.get('type') == 'multiquiz' else "Один вариант ответа"
        if question.get("content"):
            try:
                gpt_answer = self.send_gpt_response(self.format_question_for_chat(question['content'], question['options'], name, question_type_text))
            except Exception as e:
                gpt_answer = "Не удалось получить ответ"
        else:
            gpt_answer = "Текст пуст."

        html_content = f"""
        <div style="margin-bottom: 20px; border: 1px solid #ccc; border-radius: 5px; padding: 15px;">
        """
        if question.get("image"):
            html_content += f"""
            <div style="margin-bottom: 10px;">
                <img src="{question['image']}" alt="Изображение вопроса" style="max-width: 100%; height: auto;">
            </div>
        """
        html_content += f"""
            <div>
                <h3 style="color: 'grey';">{num}. {question['content'] if question.get("content") else gpt_answer}</h3>
                <p style="color: grey; margin-bottom: 10px;">{question_type_text}</p>
                <ul style="list-style-type: none; padding-left: 0;">
        """
        for opt in question['options']:
            html_content += "<li style='padding: 10px; background-color: #f4f4f4; border-radius: 5px; margin-bottom: 5px;'>"
            if opt.get("image"):
                html_content += f" <img src='{opt['image']}' alt='Изображение варианта ответа' style='max-width: 100px; height: auto;'>"
            elif opt.get("value"):
                html_content += f"{opt['value']}"
            html_content += "</li>"
        html_content += """
                </ul>
                <p style="margin-top: 10px;"><strong>Ответ чата ГПТ:</strong><br>{}</p>
            </div>
            <div style="margin-top: 10px;">
                <a href="https://www.google.com/search?q={}" target="_blank" style="text-decoration: none;">
                    <button style="background-color: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
                        Поиск в Google
                    </button>
                </a>
            </div>
        </div>
        """.format(gpt_answer, quote(question['content']))
        put_html(html_content)

    def gmail_login_form(self):
        input_group(
            "Вход в почту Gmail",
            [
                input("Электронная почта", name="email", type=TEXT),
                input("Пароль", name="password", type=TEXT),
                input("Пометка о тесте", name="test_mark", type=TEXT, placeholder="Текст пометки о тесте"),
            ]
        )

    def main(self):
        self.gmail_login_form()  # Вызываем форму входа в Gmail

        self.gmail.authenticate()  # Аутентифицируемся в Gmail

        while True:
            link = input("Ссылка на запущенный тест", required=True, type=TEXT)

            try:
                session_info = self.c.get_session_info(link)
            except Exception as e:
                toast(f"Не удалось получить информацию о Google-форме.")
                continue

            break

        put_html("""
           Вопросов: {} | {}
            <div style="margin-bottom: 10px;">
                <p style="font-style: italic; color: #999;">Это может занять некоторое время</p>
            </div>
        """.format(
            len(session_info.get("questions", [])),
            session_info.get("settings", {}).get("name")
        ))
        for num, question in enumerate(session_info.get("questions", []), start=1):
            self.show_question(num, question, session_info.get("settings", {}).get("name"))
        put_html("""
            <div style="margin-bottom: 10px;">
                <p style="font-style: italic; color: #999;">Процесс окончен</p>
            </div>
        """)

if __name__ == "__main__":
    app().run()
