from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
import logging
import os
import smtplib
from config import admin_email, email_password

async def send_email(user_data):
    """Отправляет уведомление с данными по сахарному диабету на почту администратора."""
    subject = "Новые данные по сахару и инсулину"
    body = await create_email_body(user_data)
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = admin_email
    msg['To'] = admin_email
    msg.attach(MIMEText(body, 'html'))
    try:
        with smtplib.SMTP('smtp.mail.ru', 587) as server:
            server.starttls()
            server.login(admin_email, email_password)
            server.send_message(msg)
        logging.info("Письмо отправлено успешно.")
    except Exception as e:
        logging.error(f"Не удалось отправить письмо: {e}")


async def create_email_body(user_data):
    """Создает HTML-содержимое письма с новыми данными, сгруппированными по дате."""
    user_id = user_data['user_id']
    type_of_diabetes = user_data['type_of_diabetes']
    
    # Начало HTML содержания письма
    html_content = f"""
    <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 20px;
                    color: #333;
                    background-color: #f9f9f9;
                }}
                h2 {{
                    color: #4CAF50;
                    font-size: 28px;
                    margin-bottom: 20px;
                    text-align: center;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    padding: 15px;
                    text-align: left;
                    border: 1px solid #ddd;
                    font-size: 18px;
                }}
                th {{
                    background-color: #4CAF50;
                    color: white;
                }}
                tr:hover {{
                    background-color: #f1f1f1;
                }}
                .footer {{
                    margin-top: 20px;
                    font-size: 16px;
                    color: #555;
                }}
                .header-row {{
                    background-color: #f0f0f0;
                    font-weight: bold;
                    font-size: 20px;
                }}
                .meal {{
                    background-color: #e8f5e9; /* Светло-зеленый фон для приёмов пищи */
                    padding: 10px;
                    border-radius: 5px; /* Закругленные углы */
                    margin: 5px 0; /* Отступ между записями */
                }}
            </style>
        </head>
        <body>
            <h2>Новые данные по сахарному диабету:</h2>
            <table>
                <tr class="header-row">
                    <td colspan="2" style="text-align: center;">ID пациента: {user_id}</td>
                </tr>
                <tr class="header-row">
                    <td colspan="2" style="text-align: center;">Тип диабета: {type_of_diabetes}</td>
                </tr>
                <tr>
                    <th>Дата</th>
                    <th>Записи</th>
                </tr>
    """

    # Группировка записей по дате
    records_by_date = {}
    for record in user_data['records']:
        record_date = record['record_date']
        if record_date not in records_by_date:
            records_by_date[record_date] = []
        records_by_date[record_date].append(record)

    # Обработка сгруппированных записей
    for date, date_records in records_by_date.items():
        daily_records = "<div>"
        for record in date_records:
            breakfast_glucose = record.get('breakfast_glucose', 'Нет данных')
            breakfast_insulin = record.get('breakfast_insulin', 'Нет данных')
            lunch_glucose = record.get('lunch_glucose', 'Нет данных')
            lunch_insulin = record.get('lunch_insulin', 'Нет данных')
            dinner_glucose = record.get('dinner_glucose', 'Нет данных')
            dinner_insulin = record.get('dinner_insulin', 'Нет данных')
            
            daily_records += f"""
            <div class="meal">
                Завтрак: {breakfast_glucose} (Глюкоза), {breakfast_insulin} (Инсулин) <br>
                Обед: {lunch_glucose} (Глюкоза), {lunch_insulin} (Инсулин) <br>
                Ужин: {dinner_glucose} (Глюкоза), {dinner_insulin} (Инсулин) <br>
            </div>
            """
        
        daily_records += "</div>"
        
        html_content += f"""
            <tr>
                <td>{date}</td>
                <td>{daily_records}</td>
            </tr>
        """

    # Завершение HTML содержания
    html_content += """
            </table>
            <p class="footer">Спасибо за использование нашего сервиса!</p>
        </body>
    </html>
    """

    return html_content