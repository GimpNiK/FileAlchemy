from typing import List,Any,Dict,TypeVar
def change_return_methods_None_on_self_(cls : type) -> type:
    """Декоратор для класса, который заставляет все методы возвращать self, если они ничего не возвращают."""
    
    # Получаем все атрибуты класса
    for attr_name, attr_value in cls.__dict__.items():
        # Проверяем, является ли атрибут методом
        if callable(attr_value):
            # Определяем новый метод
            def wrapper(*args :List[Any], **kwargs :Dict[Any,Any]):
                result = attr_value(*args, **kwargs)
                # Если метод ничего не возвращает, возвращаем self
                return result if result is not None else args[0]
            
            # Заменяем метод на обернутый
            setattr(cls, attr_name, wrapper)
    
    return cls


class Stream:
    """
    Переопределяет операции работы с потоками для классов наследников.
    Для корретной работы необходимо переопределить следующие методы:
    __stream_rewrite__(self,value) < / >  - запрос на перезапись данных
    __stream_append__(self,value) << / >> - запрос на добавление данных
    __stream_getData__(self)              - запрос на данные
    """
    def __lt__(self, other:"subStream") -> None:
        """
        Оператор < : перезаписывает содержимое из другого объекта в текущий.
        """
        if isinstance(other,Stream):
            self.__stream_rewrite__(other.__stream_getData__())
            return None
        elif isinstance(other,str):
            self.__stream_rewrite__(other)
        else:
            raise TypeError(f"Ожидался наследник {__class__.__name__}")
    def __gt__(self, other) -> None:
        """
        Оператор > : перезаписывает содержимое из текущего объекта в другой.
        """
        if isinstance(other,(Stream,str)):
            return other.__lt__(self)
        else:
            raise TypeError(f"Ожидался наследник {__class__.__name__}")
        
    def __lshift__(self,other) -> None:
        """
        Оператор << : добавляет в конец содержимое из другого объекта  в текущий.
        """
        if isinstance(other,Stream):
            self.__stream_append__(other.__stream_getData__())
        elif isinstance(other,str):
            self.__stream_rewrite__(other)
        else:
            raise TypeError(f"Ожидался наследник {__class__.__name__}")
        
    def __rshift__(self,other) -> None:
        """
        Оператор >> : добавляет в конец содержимое из текущего объекта  в другой.
        """
        if isinstance(other,(Stream,str)):
            other.__lshift__(self)
        else:
            raise TypeError(f"Ожидался наследник {__class__.__name__}")
        
    def __stream_rewrite__(self,value:str) -> None:
        raise NotImplementedError(f"Этот метод не разрешен в {__class__.__name__}") 
    def __stream_append__(self,value:str) -> None:
        raise NotImplementedError(f"Этот метод не разрешен в {__class__.__name__}")
    def __stream_getData__(self) -> str:
        raise NotImplementedError(f"Этот метод не разрешен в {__class__.__name__}")

subStream = TypeVar("subStream",bound = Stream)