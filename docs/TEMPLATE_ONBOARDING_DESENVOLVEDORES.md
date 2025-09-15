# TEMPLATE DE ONBOARDING DE DESENVOLVEDORES

Use este template para integrar rapidamente um novo dev ao projeto. Copiar este arquivo e renomear para `ONBOARDING_<NOME>_<DATA>.md` quando for personalizado.

## 1. Contexto Rápido (5 min)
- Objetivo do sistema: consulta rápida e consistente de SSA.
- Principais camadas: Core (lógica), Armazenamento (SQLite), GUI (PyQt6), CLI (interface textual), Config (JSONs), Scripts manutenção.
- Ler primeiro: `docs/ESTRUTURA_PROJETO.md`, `REGRAS_DE_OURO.md`.

## 2. Ambiente (10–15 min)
| Passo | Comando / Ação | Observação |
|-------|-----------------|-----------|
| Python versão | 3.13.x | Confirmar com `python --version` |
| Instalar deps | `pip install -r requirements.txt` | Usar virtualenv / pyenv |
| Verificar instalação | `python verificar_instalacao.py` ou script equivalente | Saída deve ser OK |
| Rodar app CLI | `python main.py --help` | Ver ajuda sem erros |
| Rodar GUI | `python main.py --gui` | Abrir janela principal |

## 3. Arquivos Críticos
| Área | Caminho | Função |
|------|--------|--------|
| Entrada | `main.py` | Orquestra CLI/GUI |
| DB | `armazenamento/database.py` | Operações base SQLite |
| DB otimizado | `armazenamento/database_optimized.py` | Rotinas otimização/carga |
| Lógica | `core/app_logic.py` | Fluxo principal de atualização |
| Config | `config/*.json` | Mapeamentos e preferências |
| Cache | `core/cache_manager.py` | Cache de consultas |
| GUI | `gui/` | Interfaces visuais |

## 4. Fluxo de Trabalho Padrão
1. Criar branch de feature / correção.
2. Ajustar código (evitar tocar em múltiplas áreas sem necessidade).
3. Atualizar docs se mudança estrutural.
4. Rodar testes (quando existirem) + smoke manual.
5. Abrir PR com descrição objetiva (o que / por que / risco).

## 5. Convenções
- Nome de arquivo: snake_case, ASCII, sem acentos.
- Evitar prints permanentes (usar logging se necessário).
- Cada modificação em config deve ser justificada em changelog se impactar comportamento.

## 6. Checklist Inicial Dev
- [ ] Ambiente Python configurado
- [ ] Dependências instaladas sem erro
- [ ] CLI executa `--help`
- [ ] GUI abre
- [ ] Banco acessível (tabelas básicas existem)
- [ ] Leu `ESTRUTURA_PROJETO.md`
- [ ] Leu `REGRAS_DE_OURO.md`
- [ ] Entendeu fluxo atualização SSA

## 7. Erros Comuns
| Sintoma | Causa | Solução |
|---------|-------|---------|
| ImportError mapeamentos | JSON faltando/renomeado | Conferir `config/` |
| GUI não abre | PyQt faltando | Reinstalar dependências |
| Lentidão carga inicial | Modo otimizado não usado | Ver `GUIA_MODO_OPTIMIZED.md` |
| Dados desatualizados | Cache antigo | Limpar `data/file_cache.json` |

## 8. Segurança / Cuidados
- Não apagar `data/ssas.db` sem backup.
- Validar scripts de manutenção antes de rodar em produção.
- Evitar alterar múltiplas tabelas manualmente no SQLite.

## 9. Próximos Passos Após Onboarding
- Acompanhar issues abertas.
- Identificar possíveis refactors pequenos (não quebrar API interna).
- Propor testes de regressão em áreas críticas.

## 10. Registro de Onboarding (preencher)
| Campo | Valor |
|-------|-------|
| Nome Dev |  |
| Data Início |  |
| Mentor |  |
| Primeira Tarefa |  |
| Concluiu Checklist (data) |  |

---
Documento gerado como base; atualizar conforme maturidade do processo.

