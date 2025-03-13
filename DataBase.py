import aiomysql
import logging
from sqlalchemy import Column, Integer, String, Float, Date, select, insert, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from contextlib import asynccontextmanager
from typing import Union, List, Dict

Base = declarative_base()

class User(Base):
    __tablename__ = 'user_data'
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор записи
    user_id = Column(Integer, unique=True, index=True)   # Уникальный идентификатор пользователя (например, ID чата)
    type_of_diabetes = Column(String)                     # Тип диабета (1, 2 и т.д.)
    breakfast_glucose = Column(Float)
    breakfast_insulin = Column(Integer)
    lunch_glucose = Column(Float)
    lunch_insulin = Column(Integer)
    dinner_glucose = Column(Float)
    dinner_insulin = Column(Integer)
    record_date = Column(Date)

    def __repr__(self):
        return (f"<User(id={self.id}, user_id={self.user_id}, type_of_diabetes={self.type_of_diabetes}, "
                f"breakfast_glucose={self.breakfast_glucose}, breakfast_insulin={self.breakfast_insulin}, "
                f"lunch_glucose={self.lunch_glucose}, lunch_insulin={self.lunch_insulin}, "
                f"dinner_glucose={self.dinner_glucose}, dinner_insulin={self.dinner_insulin}, "
                f"record_date={self.record_date})>")

class Access(Base):
    __tablename__ = 'access_list_id'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)


DATABASE_URL = "mysql+aiomysql://root:1111@172.28.115.198:3306/rtmc_bot"
engine = create_async_engine(DATABASE_URL, echo=True)


async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Метод для получения сессии
@asynccontextmanager
async def get_session():
    session = async_session()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logging.error(f"Ошибка при работе с сессией: {e}")  # Логировать ошибку
        raise
    finally:
        await session.close()


async def test_connection():
    async with get_session() as session:
        result = await session.execute(text('SELECT DATABASE();'))
        database_name = result.scalar()  # Получаем значение первой строки
        logging.info(f'Connected to database: {database_name}')


async def get_user_data(user_id: int = None, current_date: Date = None) -> Union[Dict, List[Dict]]:
    if (user_id is None and current_date is not None) or (user_id is not None and current_date is None):
        raise ValueError("Both user_id and current_date must be provided together or not at all.")

    async with get_session() as session:
        try:
            if user_id is not None and current_date is not None:
                query = select(User).where(User.user_id == user_id, User.record_date == current_date)
                result = await session.execute(query)
                user = result.scalars().first()
                if user:
                    return user_to_dict(user)
                else:
                    return None  # Если пользователь не найден
            else:
            # Если user_id не указан, получаем всех пользователей
                query = select(User)
                result = await session.execute(query)
                users = result.scalars().all()
                users_data = []
                for user in users:
                    user_data = user_to_dict(user)
                    existing_entry = next((item for item in users_data if item['user_id'] == user_data['user_id']), None)
                    if existing_entry:
                        # Добавляем текущую запись к существующей записи по пользователю
                        existing_entry['records'].append(user_data)
                    else:
                        # Создаём новую запись для пользователя
                        users_data.append({
                            'user_id': user_data['user_id'],
                            'type_of_diabetes': user_data['type_of_diabetes'],
                            'records': [user_data]
                        })
                return users_data

        except Exception as e:
            logging.error(f"Error occurred while fetching user data: {e}")
            return []  # Возвращает пустой список в случае ошибки


def user_to_dict(user) -> dict:
    return {
        'user_id': user.user_id,
        'type_of_diabetes': user.type_of_diabetes,
        'breakfast_glucose': user.breakfast_glucose,
        'breakfast_insulin': user.breakfast_insulin,
        'lunch_glucose': user.lunch_glucose,
        'lunch_insulin': user.lunch_insulin,
        'dinner_glucose': user.dinner_glucose,
        'dinner_insulin': user.dinner_insulin,
        'record_date': user.record_date
    }



async def add_multiple_records(user_id: int, records):
    async with get_session() as session:
        insert_query = insert(User).values(records)
        await session.execute(insert_query)
        await session.commit()  # Закоммитить изменения



async def update_multiple_records(user_id: int, records):
    async with get_session() as session:
        for record in records:
            # Формируем запрос для обновления
            update_query = update(User).where(User.user_id == user_id).values(**record)
            # Выполняем запрос
            await session.execute(update_query)
        await session.commit()  # Закоммитить изменения






