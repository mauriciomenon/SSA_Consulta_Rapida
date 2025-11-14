# SSA Consulta Rapida v4.0.3

Data: 2025-10-09

## Destaques
- Temas 100% parametrizados: bordas de quadros, indicadores e botoes de tags agora sao lidos diretamente de `utils/themes.py`, com novos papeis (`summary_*`, `indicator_text_color`) para todos os temas claros e escuros.
- Consistencia visual: a troca de tema remove CSS residual antes de aplicar o novo, e widgets de filtros/indicadores passam a compartilhar o mesmo palette sem deixar o tema claro “sombreado” ao voltar de um tema escuro.
- UX do filtro global: termos digitados com `||`, `∨` ou `OR` sao exibidos como `OU`, alinhando o comportamento das buscas gerais ao das tags e garantindo rastreabilidade nos testes automatizados.

## Compatibilidade
- Nenhuma alteracao de banco ou schema.
- Os novos papeis de tema tem fallback automatico via `THEME_ROLES_DEFAULT`; temas customizados devem apenas acrescentar as chaves se desejarem valores especificos.

## Notas de Upgrade
- Atualize `config/version.json` para 4.0.3 (ja realizado neste release).
- Caso mantenha temas customizados fora do repositorio, replique as chaves `summary_frame_bg`, `summary_frame_border`, `summary_text_color` e `indicator_text_color` antes de atualizar a GUI.

## Referencias
- Registro de mudancas resumido: `CHANGELOG.md`.
- Implementacao detalhada dos papeis de tema: `utils/themes.py`.

## Agradecimentos
- Obrigado por reforcar a diretriz de theming centralizado e por validar os ajustes de UX tanto no Windows 11 quanto no macOS Tahoe.
