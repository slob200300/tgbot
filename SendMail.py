import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


logging.basicConfig(level=logging.INFO)


async def send_email(admin_email, email_password, fio, phone, med_profile_selected, type_of_reception_selected, additional_info, user_id, attachment_path):
    subject = "Новая запись на прием через телеграм"
    body = create_email_body(fio, phone, med_profile_selected, type_of_reception_selected, additional_info, user_id, attachment_path)
    msg = prepare_email_message(subject, body, attachment_path, admin_email)
    try:
        send_email_message(msg, admin_email, email_password)
        cleanup_attachment(attachment_path)
    except Exception as e:
        logging.error(f"Ошибка при отправке письма: {e}")

def create_email_body(fio, phone, med_profile_selected, type_of_reception_selected, additional_info, user_id, attachment_path):
    return f"""
    <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 20px;
                    color: #333;
                }}
                h2 {{
                    color: #4CAF50;
                    font-size: 24px;
                    margin-bottom: 10px;
                }}
                ul {{
                    list-style-type: none;
                    padding: 0;
                }}
                li {{
                    background: #f4f4f4;
                    margin: 10px 0;
                    padding: 10px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                }}
                strong {{
                    color: #000;
                }}
                .divider {{
                    height: 1px;
                    background: #ddd;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <h2>Новая запись на прием:</h2>
            <ul>
                <li><strong>ФИО:</strong> {fio}</li>
                <li><strong>Телефон:</strong> {phone}</li>
                <li><strong>Медицинская специальность:</strong> {med_profile_selected}</li>
                <li><strong>Тип приема:</strong> {type_of_reception_selected}</li>
                <li><strong>Дополнительная информация:</strong> {additional_info}</li>
                <li><strong>ID пациента:</strong> {user_id}</li>
                <li><strong>Фото направления прикреплено:</strong> {'Да' if os.path.isfile(attachment_path) else 'Нет'}</li>
            </ul>
            <div class="divider"></div>
            <p>Спасибо за использование нашего сервиса!</p>
        </body>
    </html>
    """

def prepare_email_message(subject, body, attachment_path, admin_email):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = admin_email
    msg['To'] = admin_email
    msg.attach(MIMEText(body, 'html'))

    if os.path.isfile(attachment_path):
        try:
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition',f'attachment; filename="{os.path.basename(attachment_path)}"')
                msg.attach(part)
        except Exception as e:
            logging.error(f'Ошибка при добавлении вложения: {e}')
    else:
        logging.warning(f'Файл "{attachment_path}" не найден, вложение не добавлено.')
    return msg

def send_email_message(msg, admin_email, email_password):
    with smtplib.SMTP('smtp.office365.com', 587) as server:
        server.starttls()
        server.login(admin_email, email_password)
        server.send_message(msg)
    logging.info("Письмо отправлено успешно.")

def cleanup_attachment(attachment_path):
    try:
        if os.path.isfile(attachment_path):
            os.remove(attachment_path)
            logging.info(f"{attachment_path} успешно удален.")
        else:
            logging.warning(f"{attachment_path} не найден для удаления.")
    except Exception as e:
        logging.error(f"Ошибка при удалении файла {attachment_path}: {e}")