# ALGORITMO DE GERENCIAMENTO DE LARGURAS NA GUI (CRÍTICO)

Este documento descreve a lógica para cálculo, persistência e ajuste dinâmico das larguras de colunas / controles críticos na interface (PyQt6).

## Objetivos
- Manter legibilidade sem scroll horizontal excessivo.
- Evitar recalcular larguras a cada repintura pesada.
- Preservar preferências do usuário entre sessões.
- Ajustar de forma estável quando colunas aparecem/desaparecem.

## Fontes de Dados para Largura
| Fonte | Papel | Observações |
|-------|------|-------------|
| Medição inicial (QHeaderView) | Base bruta | Primeira fotografia após model set. |
| Heurística mínima | Evita colunas “colapsadas” | Ex.: 48 px textos curtos. |
| Prioridade de coluna (`config/column_priority.json`) | Ordenação de preservação | Colunas de prioridade alta nunca ficam < min_base. |
| Histórico persistido (`gui_main_preferences.json`) | Preferência do usuário | Aplicado após primeira medição. |
| Redução proporcional | Encaixar dentro do viewport | Distribui corte mantendo proporções. |

## Pipeline de Cálculo
1. Carregar prioridades e limites (min, max) de config.
2. Capturar larguras medidas pelo Qt após `model.reset()`.
3. Aplicar overrides do histórico (se existir chave exata de layout).
4. Garantir mínimo absoluto.
5. Calcular soma; se > largura disponível do viewport → entrar em modo compressão.
6. Compressão: iterar colunas em ordem inversa de prioridade aplicando fator de redução.
7. Ajustar última coluna para absorver diferença residual (erro de arredondamento).
8. Persistir resultado final.

## Compressão Proporcional
Pseudo‑código simplificado:
```python
def distribuir(larguras, limite, prioridades):
	total = sum(larguras)
	if total <= limite:
		return larguras
	excesso = total - limite
	ordem = order_by_prioridade_crescente(prioridades)  # menor prioridade primeiro
	for idx in ordem:
		if excesso <= 0:
			break
		margem = larguras[idx] - largura_min_coluna(idx)
		if margem <= 0:
			continue
		corte = min(margem, excesso)
		larguras[idx] -= corte
		excesso -= corte
	if excesso > 0:
		# fallback: distribuir ainda igualmente sobre todas acima do mínimo
		vivos = [i for i,l in enumerate(larguras) if l > largura_min_coluna(i)]
		while excesso > 0 and vivos:
			quota = max(1, excesso // len(vivos))
			for i in list(vivos):
				margem = larguras[i] - largura_min_coluna(i)
				if margem <= 0:
					vivos.remove(i); continue
				corte = min(margem, quota)
				larguras[i] -= corte
				excesso -= corte
				if excesso <= 0:
					break
	return larguras
```

## Persistência
- Chave de layout pode incluir: versão schema, modo (optimized/on-demand), conjunto de colunas ativo.
- Arquivo JSON atual: `config/gui_main_preferences.json` (ou equivalente se renomeado).
- Atualização somente quando diferença > delta mínimo (ex.: 3 px) para reduzir IO.

## Eventos que Disparam Recalculo
| Evento | Ação |
|--------|------|
| Importação completa | Recalcular tudo (modelo novo). |
| Alteração de preferência de usuário (mostrar/ocultar colunas) | Reavaliar + compressão. |
| Resize da janela principal | Ajuste leve (sem re‑medição base). |
| Mudança de fonte (DPI scaling) | Recalcular base + persistir. |

## Métricas Possíveis
- Tempo de cálculo (< 10 ms alvo em dataset médio).
- Número de recompressões por minuto.
- Porcentagem média de corte aplicado vs largura original.

## Riscos / Edge Cases
| Caso | Mitigação |
|------|-----------|
| Todas colunas precisam corte e atingem mínimo | Permitir scroll horizontal residual. |
| Coluna crítica perde legibilidade | Impedir reduzir abaixo `priority_min_override`. |
| Fontes grandes (acessibilidade) explodem layout | Ajustar fator de compressão inicial mais agressivo. |
| Persistência corrompida | Validar JSON; fallback para medição base. |

## Próximos Aperfeiçoamentos
- Introduzir cache de larguras por perfil de uso (ex.: operador vs auditor).
- Benchmarks automáticos de tempo de aplicação do layout.
- Heurística que detecta colunas numéricas vs texto para mínimos diferenciados.

## Status
Documento criado para substituir arquivo vazio e registrar a lógica esperada. Revisar quando implementação for ajustada.

