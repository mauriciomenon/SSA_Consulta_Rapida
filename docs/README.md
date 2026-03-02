# Documentacao SSA Consulta Rapida

## Tooling padrao (uv-first)
- Comando principal: `uv run --python 3.13 ...`
- Fallback de runtime: 3.12 -> 3.11 -> 3.10 quando 3.13 nao estiver disponivel.
- `requirements*.txt` sao mantidos para compatibilidade em ambientes sem uv.

## Instalar uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# ou
wget -qO- https://astral.sh/uv/install.sh | sh
```

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Estrutura da Documentacao

### Documentos Principais
- `RELATORIO_COMPLETO.md` - Relatorio tecnico abrangente
- `ESTRUTURA_PROJETO.md` - Arquitetura e organizacao
- `REGRAS_DE_OURO.md` - Diretrizes criticas de desenvolvimento
- `ONBOARDING.md` - Guia para novos desenvolvedores

### Guias de Uso
- `GUIA_MIGRACAO_NOVA_INSTALACAO.md` - Configuracao inicial
- `GUIA_MODO_OPTIMIZED.md` - Funcionalidades otimizadas
- `COMANDOS_RAPIDOS.md` - Referencia rapida
- `LARGURAS_GUI.md` - Sistema de larguras da interface

### Planejamento e Historico
- `CHANGELOG_IMPLEMENTACOES.md` - Historico de mudancas
- `RELATORIO_IMPLEMENTACOES.md` - Implementacoes realizadas
- `RELATORIO_MELHORIAS.md` - Melhorias aplicadas
- `PROBLEMAS_CONHECIDOS.md` - Issues conhecidos e solucoes

### Checklists e Pendencias
- `CHECKLIST_PENDENCIAS_v3.0.7.md` - Pendencias v3.0.7
- `CHECKLIST_PENDENCIAS_v3.10.md` - Pendencias v3.10
- `CHECKLIST_PENDENCIAS_FUTURAS.md` - Roadmap futuro

### Configuracao e Build
- `BUILD_SYSTEM.md` - Sistema de build
- `THEMING_AND_PACKAGING_PLAN.md` - Temas e empacotamento
- `CONFIGURATION_FIXES_2025-09-06.md` - Correcoes de configuracao

## Organizacao por Versao

### v3.0.x (Estavel)
- Funcionalidades core estabelecidas
- CLI e GUI com paridade funcional
- Database SQLite otimizado

### v3.10.x (Atual)
- Sistema de build multiplataforma
- Automacao completa
- Documentacao organizada

### v3.11+ (Futuro)
- Conforme `PLANO_ACAO_v3.11.md`
- Melhorias baseadas em feedback
- Novas funcionalidades

## Como Navegar

1. **Novos desenvolvedores**: Comece com `ONBOARDING.md`
2. **Configuracao**: Veja `GUIA_MIGRACAO_NOVA_INSTALACAO.md`
3. **Problemas**: Consulte `PROBLEMAS_CONHECIDOS.md`
4. **Desenvolvimento**: Leia `REGRAS_DE_OURO.md`

## Arquivos de Saida

Relatorios e resultados ficam em `../docs_saida/`
- Logs de execucao
- Relatorios de testes
- Analises especificas

## Atualizacao 2026-03-01 (ciclo gui-tema-import)
- Corrigido tema dos menus de selecao para herdar cores do tema ativo (sem fallback escuro fixo).
- Reduzido tamanho efetivo dos botoes Aplicar/Limpar dos filtros avancados.
- Corrigido comportamento de largura de popup dos seletores para evitar expansao excessiva.
- Reforcado import otimizado: deduplicacao por numero_ssa e falha explicita em lookup SQL parcial.
- Corrigidos comentarios recentes de review (scripts/tests/docs) e removidos emojis em arquivos versionados.

