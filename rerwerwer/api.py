# api.py

from requests import request
from bs4 import BeautifulSoup

class Client:

    def get_form_info(self, form_url: str) -> dict:
        result = request("GET", form_url)
        soup = BeautifulSoup(result.text, 'html.parser')

        # Извлекаем информацию о вопросах из HTML-кода Google-формы
        questions = []
        form_title = soup.title.text.strip() if soup.title else "Google Form"
        question_elements = soup.find_all("div", class_="freebirdFormviewerComponentsQuestionBaseRoot")
        for question_elem in question_elements:
            question_text_elem = question_elem.find("div", class_="freebirdFormviewerComponentsQuestionBaseTitle")
            question_text = question_text_elem.text.strip() if question_text_elem else "Question"
            options_elems = question_elem.find_all("div", class_="freebirdFormviewerComponentsQuestionRadioChoice")
            options = [{"value": option.text.strip()} for option in options_elems]
            questions.append({"content": question_text, "options": options})

        return {"questions": questions, "settings": {"name": form_title}}

    def get_session_info(self, form_url: str) -> dict:
        form_info = self.get_form_info(form_url)
        return form_info
