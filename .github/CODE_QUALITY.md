# Qualidade de codigo e automacao de seguranca

## Contrato vigente

Consulta de 13/09/2026, PR 131 para dev: `gh pr checks --required` nao reportou
checks obrigatorios. Uma falha de job e uma regra de servidor que impede merge
sao mecanismos diferentes. Nao houve alteracao de protecoes, rulesets,
assinaturas, planos ou configuracoes de Apps nesta rodada.

A politica existente trata Snyk e DeepSource como sinais consultivos, salvo
mudanca explicita de politica e configuracao do servidor. Seu status failure
continua visivel; nao deve ser apresentado como aprovacao nem escondido.
As verificacoes locais e jobs proprios retornam falha quando seus contratos
nao sao cumpridos, independentemente da protecao de merge do GitHub.

## Fluxos mantidos no repositorio

- minimal-ci: autoria e grupos de importacao, lint, tipos e testes conforme o
  diff; push/PR main/dev e disparo manual.
- CodeQL: precheck do modo de analise e verificacao de seguranca.
- Secret Scan: workspace e diff da PR bloqueantes; historico consultivo apenas
  em execucoes manuais/agendadas.
- Dependency review: precheck de disponibilidade e analise das dependencias.
- GitLab: MR, branch padrao, web e pushes fix/; autoria, gates, suite completa
  automatica e scanner bloqueantes. JSONL/JUnit preservados por 14 dias.
- Windows: build nativo e verificacao dos artefatos; logs de falha coletados
  depois da verificacao e do envio dos pacotes.
- `.deepsource.toml`: seleciona o analisador; nao configura protecao de merge.

Os comandos locais e detalhes dos artefatos estao em
[TESTING_STRATEGY.md](../docs/TESTING_STRATEGY.md). A validacao nativa de um
build nao pode ser substituida por analise de YAML ou PowerShell.

## Registro historico da PR 131 (13/09/2026)

As anotacoes dos oito jobs GitHub em 7015e6fd confirmam bloqueio de faturamento
antes de iniciar. Isso exige regularizacao da conta, nao mudanca dos gates.
A pipeline GitLab e o estado dos commits estao na secao M de
[AUDIT_FIXES_REPORT.md](../docs/AUDIT_FIXES_REPORT.md).

O reteste local historico e seus limites estao centralizados na
[secao L4 do relatorio](../docs/AUDIT_FIXES_REPORT.md#l4-fechamento-da-rodada-a-e).
Esse registro nao comprova execucao de CI nem aprovacao do HEAD atual.
A entrega de binarios segue [seu procedimento](../docs/BUILD_WINDOWS_ARM64_AMD64.md);
pendencias historicas nao acrescentam gates, e ajustes apenas documentais nao
exigem recompilacao. Os gates existentes permanecem com seus contratos.

CodeFactor passou apos corrigir caminhos temporarios e limpeza dos testes;
quatro avisos de complexidade permanecem nao bloqueantes. GitGuardian reportou
40 commits sem segredos. Resultados de Snyk/Socket sem mudancas de manifests
nao substituem uma auditoria completa de dependencias.

DeepSource reportou failure, 746 ocorrencias introduzidas e 622 resolvidas,
com aviso explicito de possivel imprecisao da base. Duas ocorrencias criticas
verificadas pertencem a funcoes identicas a dev e ja possuem guardas de tipo.
A triagem integral continua pendente; nao foi reduzido limiar nem acrescentada
supressao. Primeiro validar a base, depois reproduzir riscos e corrigir o
que for confirmado. CodeRabbit/Aikido remotos informaram skip por draft;
status verde de uma revisao omitida nao e revisao executada.

## Downloads e dependencias

Nao instalar pacotes Python/npm em gates apenas para gerar metadados
consultivos. O ambiente do projeto usa o lock; bibliotecas Qt do sistema e
Inno Setup no build Windows sao dependencias funcionais dos respectivos jobs.

Automatic Dependency Submission e um fluxo dinamico gerido pelo GitHub,
nao um YAML deste repo. Registro historico de 13/05/2026: a variavel
GH_DEPENDENCY_SUBMISSION_SKIP_CACHE=true estava aplicada; a tentativa de
alterar o workflow dinamico por API retornou HTTP 422. Nao foi feita nova
alteracao desse servico nesta rodada. Se mudar sua configuracao, conferir
Settings > Advanced Security > Dependency graph no GitHub e registrar o efeito.

## Limites e passagem

- Antes de alterar qualquer regra obrigatoria, conferir a politica aprovada e
  os efeitos na branch. Nao transformar um scanner consultivo em obrigatorio
  nem reduzir um gate existente para obter um status verde.
- Limite de quota, autenticacao ou ambiente nao e vulnerabilidade confirmada.
  Registrar o erro original e distinguir de um defeito reproduzivel do codigo.
- `deepsource config validate` depende de sessao CLI autenticada. Os registros
  de autenticacao ausente e erro local Snyk/libsimdutf de 25/04/2026 sao
  historicos e nao descrevem automaticamente o host atual.
- SONAR_TOKEN e SNYK_TOKEN so devem ser configurados quando um fluxo aprovado
  realmente precisar deles; nao foram incluidos segredos nesta entrega.
- Qualquer mudanca futura de regras, Apps ou criterio de aprovacao deve ser
  registrada aqui junto da configuracao correspondente.
