---
applyTo: '**/gui/**,**/*gui*.py,**/*qt*.py,**/*window*.py,**/*dialog*.py'
description: Instrucoes para desenvolvimento de GUI PyQt6
---

# Desenvolvimento GUI PyQt6

## Padroes deste Projeto

### Estrutura de Classes
```python
class MinhaJanela(QMainWindow):
    """Descricao da janela."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Configura elementos visuais."""
        pass

    def _connect_signals(self) -> None:
        """Conecta sinais e slots."""
        pass
```

### Convencoes
- Prefixo `_` para metodos privados
- Type hints em todos os metodos
- Docstrings em portugues
- Separar setup visual de logica

## Ferramentas MCP Uteis para GUI

### Figma MCP
Quando tiver design no Figma:
```
- generate_code: Gerar codigo do design
- get_node_metadata: Estrutura do design
```

### Para testes de GUI
```
- Playwright pode ajudar com automacao de testes visuais
- browser_screenshot para capturas
```

## Widgets Comuns

### Tabela de Dados
```python
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

def _criar_tabela(self, dados: list[dict]) -> QTableWidget:
    tabela = QTableWidget()
    tabela.setColumnCount(len(dados[0]))
    tabela.setRowCount(len(dados))
    # ... popular dados
    return tabela
```

### Filtros
```python
from PyQt6.QtWidgets import QLineEdit, QComboBox

def _criar_filtros(self) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)

    self.filtro_texto = QLineEdit()
    self.filtro_texto.setPlaceholderText("Buscar...")

    self.filtro_status = QComboBox()
    self.filtro_status.addItems(["Todos", "Ativo", "Inativo"])

    layout.addWidget(self.filtro_texto)
    layout.addWidget(self.filtro_status)
    return container
```

## Apos Editar GUI

1. **Codacy**: Verificar code quality
2. **Testar visualmente**: Executar e verificar layout
3. **Verificar responsividade**: Redimensionar janela
