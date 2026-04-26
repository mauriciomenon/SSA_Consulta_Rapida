=============================
SSA Consulta Rapida v4.10.0
=============================

Resumo direto
- Filtros: serie 4.0 tinha divergencias GUI CLI e streamlit em combinacoes OU e negativos; normalizacao tardia gerava estado intermediario incoerente; cache nao invalidava sempre.
- Temas: aplicacao irregular de papeis de cor em quadros resumo indicadores e tags; chaves ausentes geravam fallback silencioso.
- Centralizacao: GUI e CLI usam utils.version; removido fallback hardcoded; adicionada flag --version.
- Documentos: README e CHANGELOG atualizados com registro das falhas anteriores.
- Sem alteracao de schema e sem mudanca de formatos de exportacao.

Contexto historico serie 4.0
1. Conectivo OU exibido de forma ambigua em alguns fluxos.
2. Filtros negativos ignorados quando combinados com OU em pilhas mistas.
3. Cache de filtros reutilizava resultado sem considerar mudanca de conectivo.
4. Temas aplicavam cores diferentes para resumo e tags conforme ambiente.
5. Chaves de tema ausentes sem aviso produziam degradacao visual.

Itens corrigidos nesta versao
- Unificacao do parsing de OU entre CLI GUI e streamlit.
- Invalidacao de cache sempre que entra OU ou negativo.
- Remocao de normalizacao tardia de texto que causava dupla interpretacao.
- Mapeamento unico de papeis de tema para quadros indicadores tags.
- Inclusao das chaves de tema faltantes para evitar fallback silencioso.
- Flag --version adicionada em main.py (saida curta).
- Remocao de strings de versao fixas na GUI.

Impacto esperado
- Resultados de busca iguais nas tres interfaces.
- Negativos preservados em combinacoes com OU.
- Aplicacao de tema consistente entre plataformas.
- Versao consultada de forma unica (python main.py --version).
- Registro explicito das falhas previne reintroducao.

Verificacao rapida pos atualizacao
1. python main.py --version  -> 4.10.0
2. python main.py --gui      -> abrir interface sem erros (ver logs/ssa.log)
3. Teste simples filtro: termo1, !termo2 OU termo3 (validar consistencia CLI vs GUI).
4. Conferir tema ativo: alternar temas e checar contraste de quadros resumo.

Procedimento de atualizacao
1. git pull origin main
2. (Opcional) Limpeza de dados antigos: python main.py --clean-data
3. Conferir versao: python main.py --version
4. Reimportar planilhas se necessario: python main.py --force-rescan

Sem mudancas estruturais
- Banco: nenhuma alteracao de schema.
- Exportacao: formatos CSV XLSX JSON permanecem identicos.
- Scripts de migracao anteriores seguem operacionais; nao requer acao para esta versao.

Riscos residuais monitorados
- Combinacoes de filtros com grande numero de termos podem gerar maior frequencia de invalidacao de cache (monitorar tempo de resposta).
- Temas personalizados externos precisam incluir novas chaves adicionadas (ver utils/themes.py).

Indicadores de sucesso (simples)
- Tempo medio de aplicacao de filtro sem aumento relevante (comparar antes/depois em amostra interna).
- Ausencia de diferencas de contagem entre CLI e GUI para mesma consulta.
- Log sem entradas de fallback de tema.

Comandos uteis (PowerShell)
```pwsh
python main.py --version
python main.py --gui
python main.py --force-rescan
```

Chaves adicionadas ou consolidadas (temas)
- summary_*
- indicator_text_color

Encerramento das falhas serie 4.0
Este release encerra rastreio das anomalias descritas nos pontos de contexto historico. Futuras mudancas em filtros ou temas devem referenciar esta data para auditoria.

Solicitacao de feedback
Relatar divergencias de resultado entre interfaces com: exemplo de termos, captura de saida CLI, captura de tela GUI.

FIM

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

