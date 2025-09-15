# STATUS DE BUILD v3.10

Relatório rápido do estado da build / distribuição da versão 3.10 (foco: reprodutibilidade, integridade e gaps restantes).

## 1. Resumo Executivo
Versão 3.10 estabilizada quanto a: estrutura de diretórios, padronização de nomes, preenchimento de documentação crítica e backups automáticos. Próximos focos: validação de configurações JSON, harness mínimo de testes e script de agregação de documentação.

## 2. Artefatos de Build
| Artefato | Local / Comando | Status | Observações |
|----------|-----------------|--------|-------------|
| Wheel / sdist | build/ (ver scripts) | (pendente validar) | Garantir versão em `config/version.json`. |
| Executável GUI (PyInstaller?) | (não configurado) | Pendente | Avaliar necessidade real. |
| Dependências | `requirements.txt` | OK | Revisar limpeza duplicadas futuramente. |
| Scripts auxiliares | `build/build_all.py` | OK | Ajustar para log estruturado. |

## 3. Ambiente de Execução
| Item | Valor / Situação |
|------|------------------|
| Python alvo | 3.13.x |
| SO testado | macOS (local) |
| Suporte Windows | Scripts `.ps1` presentes (não revalidados) |
| Variáveis ambiente críticas | (nenhuma obrigatória) |
| Banco default | `data/ssas.db` |

## 4. Checklist de Reprodutibilidade
- [x] Padronização de nomes aplicada.
- [x] Documentos vazios preenchidos.
- [x] Backup automático antes de reset de banco.
- [ ] Validação automática de JSON de config.
- [ ] Teste smoke CLI documentado.
- [ ] Teste smoke GUI documentado.
- [ ] Script de verificação de docs integrados.

## 5. Testes / Qualidade
| Tipo | Cobertura Atual | Notas |
|------|-----------------|-------|
| Unitários núcleo | Baixa | Definir primeiro conjunto mínimo. |
| Smoke CLI | Manual | Criar script automatizado. |
| Smoke GUI | Manual | Capturar sequência básica (abrir, listar, sair). |
| Validação config JSON | Inexistente | Adicionar schema leve. |
| Verificação docs vazios | Manual | Automação proposta. |

## 6. Riscos Abertos
| Risco | Impacto | Mitigação Planejada |
|-------|---------|---------------------|
| Ausência de testes automatizados | Regressões silenciosas | Introduzir smoke + unit core. |
| JSON sem schema | Erros sutis em produção | Criar validador inicial. |
| Falta de release packaging | Dificulta distribuição externa | Definir meta se necessário. |
| Script build não loga erros padronizados | Debug mais lento | Padronizar logger no build. |

## 7. Próximas Ações Prioritárias
1. Implementar script `scripts/validate_configs.py` para checagem de JSON (estrutura mínima).
2. Criar `tests/smoke_cli_test.py` validando help e uma consulta básica.
3. Adicionar script de verificação de docs vazios (`scripts/check_docs.py`).
4. Registrar versão em `config/version.json` alinhada ao pacote.

## 8. Métricas (Placeholder)
| Métrica | Valor Atual | Alvo |
|---------|-------------|------|
| Tempo setup ambiente limpo | (medir) | < 3 min |
| Tamanho wheel | (se gerar) | < 15 MB |
| Testes smoke falhando | (N/A) | 0 |
| Docs vazios detectados | 0 | 0 |

## 9. Histórico de Alterações deste Arquivo
| Data | Alteração | Autor |
|------|-----------|-------|
| 2025-09-12 | Criação inicial template status build v3.10 | (assistente) |

## 10. Notas Finais
Este arquivo deve ser atualizado apenas quando houver mudança concreta em build, packaging, estrutura de testes ou métricas. Evitar inflar com detalhes replicados de outros documentos; referenciar em vez de duplicar.

