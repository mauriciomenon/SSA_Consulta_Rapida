# ALGORITMO DE GERENCIAMENTO DE LARGURAS NA GUI (CRITICO)

Este documento descreve a logica para calculo, persistencia e ajuste dinamico das larguras de colunas / controles criticos na interface (PyQt6).

## Objetivos
- Manter legibilidade sem scroll horizontal excessivo.
- Evitar recalcular larguras a cada repintura pesada.
- Preservar preferencias do usuario entre sessoes.
- Ajustar de forma estavel quando colunas aparecem/desaparecem.

## Fontes de Dados para Largura
| Fonte | Papel | Observacoes |
|-------|------|-------------|
| Medicao inicial (QHeaderView) | Base bruta | Primeira fotografia apos model set. |
| Heuristica minima | Evita colunas “colapsadas” | Ex.: 48 px textos curtos. |
| Prioridade de coluna (`config/column_priority.json`) | Ordenacao de preservacao | Colunas de prioridade alta nunca ficam < min_base. |
| Historico persistido (`gui_main_preferences.json`) | Preferencia do usuario | Aplicado apos primeira medicao. |
| Reducao proporcional | Encaixar dentro do viewport | Distribui corte mantendo proporcoes. |

## Pipeline de Calculo
1. Carregar prioridades e limites (min, max) de config.
2. Capturar larguras medidas pelo Qt apos `model.reset()`.
3. Aplicar overrides do historico (se existir chave exata de layout).
4. Garantir minimo absoluto.
5. Calcular soma; se > largura disponivel do viewport → entrar em modo compressao.
6. Compressao: iterar colunas em ordem inversa de prioridade aplicando fator de reducao.
7. Ajustar ultima coluna para absorver diferenca residual (erro de arredondamento).
8. Persistir resultado final.

## Compressao Proporcional
Pseudo‐codigo simplificado:
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
		# fallback: distribuir ainda igualmente sobre todas acima do minimo
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

## Persistencia
- Chave de layout pode incluir: versao schema, modo (optimized/on-demand), conjunto de colunas ativo.
- Arquivo JSON atual: `config/gui_main_preferences.json` (ou equivalente se renomeado).
- Atualizacao somente quando diferenca > delta minimo (ex.: 3 px) para reduzir IO.

## Eventos que Disparam Recalculo
| Evento | Acao |
|--------|------|
| Importacao completa | Recalcular tudo (modelo novo). |
| Alteracao de preferencia de usuario (mostrar/ocultar colunas) | Reavaliar + compressao. |
| Resize da janela principal | Ajuste leve (sem re‐medicao base). |
| Mudanca de fonte (DPI scaling) | Recalcular base + persistir. |

## Metricas Possiveis
- Tempo de calculo (< 10 ms alvo em dataset medio).
- Numero de recompressoes por minuto.
- Porcentagem media de corte aplicado vs largura original.

## Riscos / Edge Cases
| Caso | Mitigacao |
|------|-----------|
| Todas colunas precisam corte e atingem minimo | Permitir scroll horizontal residual. |
| Coluna critica perde legibilidade | Impedir reduzir abaixo `priority_min_override`. |
| Fontes grandes (acessibilidade) explodem layout | Ajustar fator de compressao inicial mais agressivo. |
| Persistencia corrompida | Validar JSON; fallback para medicao base. |

## Proximos Aperfeicoamentos
- Introduzir cache de larguras por perfil de uso (ex.: operador vs auditor).
- Benchmarks automaticos de tempo de aplicacao do layout.
- Heuristica que detecta colunas numericas vs texto para minimos diferenciados.

## Status
Documento criado para substituir arquivo vazio e registrar a logica esperada. Revisar quando implementacao for ajustada.

