# SSA Consulta Rápida v4.0.3

Data: 2025-10-09

## Destaques
- Temas 100% parametrizados: bordas de quadros, indicadores e botões de tags agora são lidos diretamente de `utils/themes.py`, com novos papéis (`summary_*`, `indicator_text_color`) para todos os temas claros e escuros.
- Consistência visual: a troca de tema remove CSS residual antes de aplicar o novo, e widgets de filtros/indicadores passam a compartilhar o mesmo palette sem deixar o tema claro “sombreado” ao voltar de um tema escuro.
- UX do filtro global: termos digitados com `||`, `∨` ou `OR` são exibidos como `OU`, alinhando o comportamento das buscas gerais ao das tags e garantindo rastreabilidade nos testes automatizados.

## Compatibilidade
- Nenhuma alteração de banco ou schema.
- Os novos papéis de tema têm fallback automático via `THEME_ROLES_DEFAULT`; temas customizados devem apenas acrescentar as chaves se desejarem valores específicos.

## Notas de Upgrade
- Atualize `config/version.json` para 4.0.3 (já realizado neste release).
- Caso mantenha temas customizados fora do repositório, replique as chaves `summary_frame_bg`, `summary_frame_border`, `summary_text_color` e `indicator_text_color` antes de atualizar a GUI.

## Referências
- Registro de mudanças resumido: `CHANGELOG.md`.
- Implementação detalhada dos papéis de tema: `utils/themes.py`.

## Agradecimentos
- Obrigado por reforçar a diretriz de theming centralizado e por validar os ajustes de UX tanto no Windows 11 quanto no macOS Tahoe.
