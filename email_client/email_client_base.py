# email_client/email_client_base.py

# Импортируем класс ABC (Abstract Base Class) и функцию abstractmethod из библиотеки abc.
# ABC нужен для создания базовых (абстрактных) классов, а abstractmethod - для указания методов, которые обязательно должны быть реализованы в дочерних классах.
from abc import ABC, abstractmethod

# Создаём класс EmailClientBase, который наследуется от ABC. Это значит, что EmailClientBase будет абстрактным классом.
# Абстрактный класс - это как шаблон, который нельзя использовать напрямую, но можно создавать на его основе другие классы.
class EmailClientBase(ABC):
    
    # Создаём абстрактный метод connect. Это метод, который должен быть реализован в каждом классе-наследнике.
    # Метод connect будет отвечать за подключение к электронной почте.
    @abstractmethod
    def connect(self):
        # pass - это просто заглушка, которая говорит, что здесь ничего не делается. Классы-наследники должны будут реализовать этот метод сами.
        pass

    # Создаём ещё один абстрактный метод get_messages. Это метод, который также должен быть реализован в каждом классе-наследнике.
    # Метод get_messages будет отвечать за получение сообщений из почтового ящика.
    @abstractmethod
    def get_messages(self):
        # Опять используем pass, так как реализация будет в дочерних классах.
        pass
