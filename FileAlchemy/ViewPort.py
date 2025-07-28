from typing import Optional, List, Any, Dict, Callable
import os

class ViewPort:
    def __init__(
        self, 
        parms_value: Optional[Dict[str, Any]] = None, 
        parms_link: Optional[Dict[str, Callable[[], Any]]] = None,
        parms_gl: Optional[Dict[str, str]] = None
    ):
        self.parms_value = parms_value or {}
        self.parms_link = parms_link or {}

        # Initialize global environment variables
        if parms_gl is not None:
            os.environ.clear()
            os.environ.update(parms_gl)

    def set_gl(self, name: str, value: str):
        """Sets a global environment variable."""
        os.environ[name] = value

    def del_gl(self, name: str):
        """Deletes a global environment variable."""
        if name in os.environ:
            del os.environ[name]

    @property
    def parms(self) -> Dict[str, Any]:
        """Returns a combined dictionary of all parameters."""
        return {
            **os.environ,
            **self.parms_value,
            **{k: v() for k, v in self.parms_link.items()}
        }

    def set_(self, name: str, value: Any, link: bool = False):
        """
        Sets a parameter.
        - link=True: saves it as a callable function.
        - link=False: saves it as a static value.
        """
        if link:
            if not callable(value):
                raise TypeError("For linked parameters, the value must be a function")
            self.parms_link[name] = value
        else:
            self.parms_value[name] = value

    def sets(self, parms: Dict[str, Any], link: bool = False):
        """Sets multiple parameters at once."""
        for k, v in parms.items():
            self.set_(k, v, link)

    def del_(self, name: str):
        """Deletes a parameter from local variables."""
        if name in self.parms_value:
            del self.parms_value[name]
        if name in self.parms_link:
            del self.parms_link[name]

    def dels(self, parms: List[str]):
        """Deletes multiple parameters."""
        for k in parms:
            self.del_(k)

    def __getitem__(self, name: str) -> Any:
        """Allows accessing parameters via parms['name']."""
        if name in os.environ:
            return os.environ[name]
        if name in self.parms_value:
            return self.parms_value[name]
        if name in self.parms_link:
            return self.parms_link[name]()
        raise KeyError(f"Parameter '{name}' not found")

    def __setitem__(self, name: str, value: Any):
        """Automatically determines the parameter type when setting."""
        if callable(value):
            self.parms_link[name] = value
        else:
            self.parms_value[name] = value

    def __delitem__(self, name: str):
        self.del_(name)

    def __contains__(self, name: str) -> bool:
        """Checks if a parameter exists."""
        return name in os.environ or name in self.parms_value or name in self.parms_link
