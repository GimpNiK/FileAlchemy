from typing import Optional, List, Any,Dict,Callable
import os
class ViewPort:
    def __init__(self, 
                 parms_value: Optional[Dict[str, Any]] = None, 
                 parms_link: Optional[Dict[str, Callable[[], Any]]] = None,
                 parms_gl: Optional[Dict[str, str]] = None):
        self.parms_value = parms_value or {}
        self.parms_link = parms_link or {}
        
        # Инициализация глобальных переменных
        if parms_gl is not None:
            os.environ.clear()
            os.environ.update(parms_gl)
    
    def set_gl(self, name: str, value: str):
        """Устанавливает глобальную переменную окружения"""
        os.environ[name] = value
    
    def del_gl(self, name: str):
        """Удаляет глобальную переменную окружения"""
        if name in os.environ:
            del os.environ[name]
    
    @property
    def parms(self) -> Dict[str, Any]:
        """Возвращает объединённый словарь всех параметров"""
        return {
            **os.environ,
            **self.parms_value,
            **{k: v() for k, v in self.parms_link.items()}
        }
    
    def set_(self, name: str, value: Any, link: bool = False):
        """
        Устанавливает параметр
        - link=True: сохраняет как вычисляемую функцию
        - link=False: сохраняет как статическое значение
        """
        if link:
            if not callable(value):
                raise TypeError("Для связанных параметров значение должно быть функцией")
            self.parms_link[name] = value
        else:
            self.parms_value[name] = value
    def sets(self, parms: Dict[str,Any] , link: bool = False):
        for k,v in parms.items():
            self.set_(k,v,link)
    def del_(self, name: str):
        """Удаляет параметр из локальных  переменных"""
        if name in self.parms_value:
            del self.parms_value[name]
        if name in self.parms_link:
            del self.parms_link[name]
    def dels(self, parms: List[str]):
        for k,v in parms:
            self.del_(k)
    def __getitem__(self, name: str) -> Any:
        """Позволяет обращаться к параметрам через parms['name']"""
        if name in os.environ:
            return os.environ[name]
        if name in self.parms_value:
            return self.parms_value[name]
        if name in self.parms_link:
            return self.parms_link[name]()
        raise KeyError(f"Параметр '{name}' не найден")
    
    def __setitem__(self, name: str, value: Any):
        """Автоматически определяет тип параметра при установке"""
        if callable(value):
            self.parms_link[name] = value
        else:
            self.parms_value[name] = value
    
    def __delitem__(self, name: str):
        self.del_(name)
    
    def __contains__(self, name: str) -> bool:
        """Проверяет существование параметра"""
        return name in os.environ or name in self.parms_value or name in self.parms_link