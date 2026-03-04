# gui/widgets/filter_help_dialog.py
# Dialog showing filter syntax help

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox

try:
  from utils.version import get_app_version
except ImportError:  # Centralizacao: fallback minimo
  def get_app_version():
    return "0.0.0"


class FilterHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajuda - Filtros (CLI/GUI)")
        self.setModal(True)
        self.resize(560, 480)
        layout = QVBoxLayout()
        help_text = QTextBrowser()
        help_text.setOpenExternalLinks(True)
        # Corrige indentacao incorreta que gerava IndentationError
        app_version = get_app_version() if callable(get_app_version) else "0.0.0"
        help_text.setHtml(
            """
            <h3>Como usar os filtros</h3>
            <h4>Separacao de termos</h4>
            <ul>
              <li><b>Pesquisa Geral</b>: virgulas separam termos (logica E - TODOS os termos obrigatorios)</li>
              <li><b>Filtros de Coluna</b>: virgulas separam alternativas (logica OU - qualquer termo serve)</li>
            </ul>
            <h4>Modos por termo</h4>
            <ul>
              <li><b>contem</b> (padrao): <code>foo</code></li>
              <li><b>comeca com</b>: <code>^foo</code></li>
              <li><b>termina com</b>: <code>foo$</code></li>
              <li><b>igual</b>: <code>=foo</code></li>
              <li><b>regex</b>: <code>~foo.*bar</code></li>
              <li><b>negativo</b>: prefixe <code>!</code> (ex.: <code>!^adm</code>, <code>!$2025</code>)</li>
              <li><b>vazios/nulos</b>: <code>=NULL</code> ou <code>NULL</code> (equivale a campo vazio, nulo ou <code>-</code>)</li>
            </ul>
            <h4>Colunas == e != nos menus de selecao</h4>
            <p>Nos menus de filtro avancado (Setor, Divisao, etc.), cada valor tem duas colunas de checkbox:</p>
            <ul>
              <li><b>== (Incluir)</b>: Marca valores que DEVEM aparecer nos resultados</li>
              <li><b>!= (Excluir)</b>: Marca valores que NAO devem aparecer nos resultados</li>
            </ul>
            <p><i>Nota:</i> Nao e possivel marcar o mesmo valor em ambas as colunas simultaneamente.</p>
            <h4>Exemplos</h4>
            <ul>
              <li><code>mel3</code> - procura por MEL3</li>
              <li><code>pendente, programar</code> - termos combinados</li>
              <li><code>executada, !mel4</code> - exclui MEL4</li>
              <li><code>g076, amp</code> - combina setores</li>
              <li><code>=NULL</code> - somente campos vazios/nulos</li>
            </ul>
            <h4>Filtro por coluna</h4>
            <p>Abra o menu com <b>clique direito</b> no titulo da coluna. O painel a direita mostra os filtros por coluna com botoes <b>Aplicar</b>, <b>Limpar</b> e <b>Ocultar</b>. Regras identicas as do filtro geral.</p>
            <h4>Dicas</h4>
            <ul>
              <li>Nao diferencia maiusculas/minusculas</li>
              <li>Termos parciais funcionam (ex.: <code>exec</code> encontra <i>executada</i>)</li>
              <li>Deixe vazio para ver todas as SSAs</li>
            </ul>
            <hr/>
            <p style='font-size:12px;'>
              <b>Projeto:</b> SSA_Consulta_Rapida • <b>Versao:</b> %s<br/>
              <b>Autor:</b> Mauricio Menon • <b>Repositorio:</b>
              <a href='https://github.com/mauriciomenon/SSA_Consulta_Rapida'>github.com/mauriciomenon/SSA_Consulta_Rapida</a>
            </p>
            """
            % app_version
        )
        layout.addWidget(help_text)
        okb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        okb.accepted.connect(self.accept)
        layout.addWidget(okb)
        self.setLayout(layout)
