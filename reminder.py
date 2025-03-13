from sqlalchemy.future import select
from DataBase import User, Access, get_session, get_user_data
import asyncio
import logging
from SendMailSugar import send_email


async def send_reminder():
    from runner import bot
    async with get_session() as session:
        result = await session.execute(select(Access.user_id))
        user_tg_id_set = {user_id[0] for user_id in result.fetchall()} # создаем уникальный set
        user_tg_id_list = list(user_tg_id_set)  # Приводим множество к списку+
        for user_id in user_tg_id_list:
            for attempt in range(3):  # Повторить 3 раза
                try:
                    await bot.send_message(chat_id=user_id, text="Напоминаем вам ввести показания сахара и инсулина! 📝")
                    break  # Выйти из цикла попыток, если успешно
                except Exception as e:
                    logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
                    if attempt == 2:  # Если это последняя попытка
                        logging.error("Не удалось отправить сообщение после 3 попыток.")



async def send_main_email():
    async with get_session() as session:
        user_data_list = await get_user_data()
        if not user_data_list:
            logging.warning("Нет данных для отправки.")
            return
        else:
            for user_data in user_data_list:
                await send_email(user_data)
            logging.info("Все письма отправлены успешно.")



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
