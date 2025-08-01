# utils/pagination.py

from typing import List, Any, Generic, TypeVar, Union
import pandas as pd

# T é uma variável de tipo genérico, para que o paginador funcione com qualquer tipo de item.
# Pode ser uma lista de listas ou um DataFrame do Pandas.
T = TypeVar('T')

class Paginator(Generic[T]):
    """
    Gerencia o estado e a lógica da paginação para uma lista de itens ou um DataFrame.
    É uma classe de lógica pura, sem conhecimento da interface (GUI ou CLI).
    """
    def __init__(self, data: Union[pd.DataFrame, List[Any]], page_size: int = 20):
        self.page_size = max(1, page_size)
        self._data: Union[pd.DataFrame, List[Any]] = data
        self.current_page: int = 1
        self.total_items: int = 0
        self.total_pages: int = 1
        self.set_data(data)

    def set_data(self, data: Union[pd.DataFrame, List[Any]]):
        """Define um novo conjunto de dados para paginar e reseta para a página 1."""
        self._data = data
        self.total_items = len(self._data)
        self._calculate_total_pages()
        self.current_page = 1

    def _calculate_total_pages(self):
        """Calcula o número total de páginas."""
        if self.total_items == 0:
            self.total_pages = 1
            return
        self.total_pages = (self.total_items + self.page_size - 1) // self.page_size

    def get_current_page_data(self) -> Union[pd.DataFrame, List[Any]]:
        """Retorna a fatia de dados para a página atual."""
        start_index = (self.current_page - 1) * self.page_size
        end_index = start_index + self.page_size
        
        if isinstance(self._data, pd.DataFrame):
            return self._data.iloc[start_index:end_index]
        else:
            return self._data[start_index:end_index]

    def go_to_page(self, page_number: int) -> bool:
        """Muda para uma página específica. Retorna True se a página for válida."""
        if 1 <= page_number <= self.total_pages:
            self.current_page = page_number
            return True
        return False

    def next_page(self) -> bool:
        """Avança para a próxima página. Retorna True se bem-sucedido."""
        return self.go_to_page(self.current_page + 1)

    def prev_page(self) -> bool:
        """Retorna para a página anterior. Retorna True se bem-sucedido."""
        return self.go_to_page(self.current_page - 1)
