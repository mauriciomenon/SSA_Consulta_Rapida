# TEMPLATE DE ONBOARDING DE DESENVOLVEDORES

Use este template para integrar rapidamente um novo dev ao projeto. Copiar este arquivo e renomear para `ONBOARDING_<NOME>_<DATA>.md` quando for personalizado.

## 1. Contexto Rapido (5 min)
- Objetivo do sistema: consulta rapida e consistente de SSA.
- Principais camadas: Core (logica), Armazenamento (SQLite), GUI (PyQt6), CLI (interface textual), Config (JSONs), Scripts manutencao.
- Ler primeiro: `docs/ESTRUTURA_PROJETO.md`, `REGRAS_DE_OURO.md`.

## 2. Ambiente (10–15 min)
| Passo | Comando / Acao | Observacao |
|-------|-----------------|-----------|
| Python versao | 3.13.x | Confirmar com `python --version` |
| Instalar deps | `pip install -r requirements.txt` | Usar virtualenv / pyenv |
| Verificar instalacao | `python verificar_instalacao.py` ou script equivalente | Saida deve ser OK |
| Rodar app CLI | `python main.py --help` | Ver ajuda sem erros |
| Rodar GUI | `python main.py --gui` | Abrir janela principal |

## 3. Arquivos Criticos
| Area | Caminho | Funcao |
|------|--------|--------|
| Entrada | `main.py` | Orquestra CLI/GUI |
| DB | `armazenamento/database.py` | Operacoes base SQLite |
| DB otimizado | `armazenamento/database_optimized.py` | Rotinas otimizacao/carga |
| Logica | `core/app_logic.py` | Fluxo principal de atualizacao |
| Config | `config/*.json` | Mapeamentos e preferencias |
| Cache | `core/cache_manager.py` | Cache de consultas |
| GUI | `gui/` | Interfaces visuais |

## 4. Fluxo de Trabalho Padrao
1. Criar branch de feature / correcao.
2. Ajustar codigo (evitar tocar em multiplas areas sem necessidade).
3. Atualizar docs se mudanca estrutural.
4. Rodar testes (quando existirem) + smoke manual.
5. Abrir PR com descricao objetiva (o que / por que / risco).

## 5. Convencoes
- Nome de arquivo: snake_case, ASCII, sem acentos.
- Evitar prints permanentes (usar logging se necessario).
- Cada modificacao em config deve ser justificada em changelog se impactar comportamento.

## 6. Checklist Inicial Dev
- [ ] Ambiente Python configurado
- [ ] Dependencias instaladas sem erro
- [ ] CLI executa `--help`
- [ ] GUI abre
- [ ] Banco acessivel (tabelas basicas existem)
- [ ] Leu `ESTRUTURA_PROJETO.md`
- [ ] Leu `REGRAS_DE_OURO.md`
- [ ] Entendeu fluxo atualizacao SSA

## 7. Erros Comuns
| Sintoma | Causa | Solucao |
|---------|-------|---------|
| ImportError mapeamentos | JSON faltando/renomeado | Conferir `config/` |
| GUI nao abre | PyQt faltando | Reinstalar dependencias |
| Lentidao carga inicial | Modo otimizado nao usado | Ver `GUIA_MODO_OPTIMIZED.md` |
| Dados desatualizados | Cache antigo | Limpar `data/file_cache.json` |

## 8. Seguranca / Cuidados
- Nao apagar `data/ssas.db` sem backup.
- Validar scripts de manutencao antes de rodar em producao.
- Evitar alterar multiplas tabelas manualmente no SQLite.

## 9. Proximos Passos Apos Onboarding
- Acompanhar issues abertas.
- Identificar possiveis refactors pequenos (nao quebrar API interna).
- Propor testes de regressao em areas criticas.

## 10. Registro de Onboarding (preencher)
| Campo | Valor |
|-------|-------|
| Nome Dev |  |
| Data Inicio |  |
| Mentor |  |
| Primeira Tarefa |  |
| Concluiu Checklist (data) |  |

---
Documento gerado como base; atualizar conforme maturidade do processo.

