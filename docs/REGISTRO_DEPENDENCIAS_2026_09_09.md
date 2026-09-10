# Registro da limpeza e atualizacao de dependencias de 2026-09-09

Registro retrospectivo preparado em **2026-09-10**. Versao da aplicacao: **4.50.0**.
Este documento registra a rodada ja executada; sua inclusao altera somente documentacao.

## Escopo, rastreabilidade e limites

A solicitacao foi verificar pip e pacotes sem uso, reduzir ruido, atualizar versoes minor/patch e alinhar requirements ao uso de uv. A execucao abrangeu dependencias diretas e transitivas de runtime, desenvolvimento, web e build. Foram alterados 24 arquivos versionados na rodada tecnica.

| Marco | Commit | Papel |
|---|---|---|
| Antes | `a9160ce98c8a9910093a22092b94cb072deab957` | Estado posterior a remocao do Codeflash |
| Dependencias | `a3e7adb6b71465ada9aae0cc7c77583e0267d4f1` | Limpeza, atualizacoes, requirements e regras Ruff |
| Depois | `36706e7784a44f060761bbfe35d070971ac571fc` | Scripts de ambiente, testes e guias |

A remocao anterior do Codeflash nao integra os deltas abaixo. A rodada nao mudou a versao da aplicacao, schema do banco ou codigo funcional das interfaces/calculos. Os scripts de ambiente e as ferramentas utilizadas pela aplicacao mudaram e podem afetar execucao, instalacao e build.

**Limite do registro:** os inventarios, commits e resultados foram preservados, mas a entrega original nao apresentou este registro consolidado e versionado. Nao foi concluida uma revisao individual de todos os 45 changelogs de pacotes atualizados. As justificativas abaixo distinguem decisoes comprovadas, criterio geral de selecao e lacunas; nao atribuem retrospectivamente uma correcao especifica a cada upgrade.

**Criterio aplicado:** primeiro componente numerico da versao resolvida preservado por pacote/Python/plataforma. Isso nao comprova compatibilidade semantica. Dos 45 nomes atualizados, 12 usam versoes `0.x`; oito mudaram o segundo componente: ast-serialize, cssselect2, httptools, librt, patchelf, ruff, uvicorn e webencodings. Ruff 0.16 de fato mudou comportamento padrao.

O inventario macOS representa um ambiente local Python 3.13.12 que continha ferramentas adicionais. Associar esse inventario a commits nao significa que o estado anterior foi reproduzido por uma instalacao limpa daquele commit: AnyIO era 4.14.2 no ambiente e 4.13.0 no lock. Os inventarios locais nao representam todas as plataformas nem todos os extras.

## Resumo quantitativo

Contagens de nomes incluem `ssa-consulta-rapida` uma unica vez; metadata egg-info/dist-info duplicada do mesmo projeto nao conta como outro pacote. O lock universal inclui todos os extras e variantes de Python/plataforma, mesmo quando nao estao instalados na `.venv`.

| Medida | Antes | Depois | Detalhe |
|---|---:|---:|---|
| Nomes instalados na `.venv` macOS | 63 | 47 | 16 removidos, 22 atualizados, 25 mantidos; nenhum nome novo |
| Nomes distintos no lock | 106 | 97 | 10 removidos, um adicionado, 45 atualizados, 51 mantidos |
| Registros nome/versao no lock | 108 | 100 | NumPy ganhou uma variante adicional |
| Nomes externos no lock | 105 | 96 | Exclui o projeto local |
| Registros externos no lock | 107 | 99 | Inclui variantes pandas/NumPy |
| Referencias a wheels | 1.407 | 1.847 | Arquivos para diferentes interpretes/plataformas; nao sao pacotes instalados |
| Referencias a distribuicoes fonte | 105 | 97 | Arquivos de origem dos pacotes |
| Marcadores globais de resolucao | 13 | 16 | Separacao de Python 3.11 e 3.12 |
| Nomes na `.venv-linux` antiga | 22 | 20 | Somente idna/isort retirados; sem execucao nativa |

## Decisoes de remocao e manutencao

| Decisao | Pacotes/versoes | Motivo e alcance |
|---|---|---|
| Remover ferramenta de instalacao local | pip 25.3 | Nao era dependencia declarada; os scripts o semeavam. Removido da `.venv` apos corrigir criacao/instalacao |
| Remover dependencia direta dev | isort 8.0.1 | Nenhum consumidor ativo encontrado no projeto; a referencia restante era comentario |
| Remover dependencia direta build | dmgbuild 1.6.7 | Fluxo DMG identificado utiliza hdiutil |
| Remover cadeia dmgbuild | ds-store 1.3.2; mac-alias 2.2.3 | Perderam consumidor com a remocao de dmgbuild |
| Remover transitivas antigas de Streamlit | blinker 1.9.0; cachetools 7.1.1; GitPython 3.1.58; tenacity 9.1.4 | Metadata do Streamlit 1.63 deixou de exigir essas quatro dependencias |
| Remover cadeia GitPython | gitdb 4.0.12; smmap 5.0.2 | Ficaram sem consumidor no lock atualizado |
| Remover ferramenta extra local e sua cadeia | ddgs e outros 12 pacotes do inventario macOS | Sem uso pela aplicacao; nao pertenciam ao conjunto runtime/dev sincronizado |
| Retirar idna do runtime direto | idna 3.18 -> 3.19 no lock | Permanece transitivo para consumidores web; constraint `>=3.19,<4`; ausente da `.venv` runtime/dev final |
| Retirar virtualenv da declaracao dev direta | virtualenv 21.6.1 -> 21.7.9 | Continua transitivo de pre-commit; constraint `>=21.7.9,<22`; permanece instalado |
| Declarar lxml no runtime | Ausente do lock -> 6.1.3; local 6.1.0 -> 6.1.3 | Backend Excel ja utilizado, preservado para evitar sua remocao pelo sync e perda de desempenho medida |
| Manter ferramentas com consumidor ativo | flake8, black, mypy, pre-commit | Referencias encontradas em scripts de lint, gates e instalacao de hooks |
| Manter dependencia Windows | pywin32 311 | Sem atualizacao de versao; ausencia de validacao nativa suficiente para retirar suporte de build |

A conclusao de ausencia de uso refere-se aos consumidores examinados no repositorio, nao a scripts pessoais externos. As 45 atualizacoes do lock aplicaram o pedido de atualizacao ao grafo completo. Elas nao foram todas necessarias para retirar pip; nao ha evidencias de que cada uma corrija um defeito especifico do SSA.

## Inventario completo do lock

`Direta` significa declarada no projeto, em extras ou no backend de build. `Transitiva` significa resolvida por outro pacote. Essa classificacao nao implica instalacao no ambiente local. Um pacote pode continuar transitivo mesmo depois de sair das dependencias diretas. Versoes separadas por virgula coexistem para faixas distintas de Python.

| Pacote | Antes | Depois | Situacao | Papel antes/depois |
|---|---|---|---|---|
| altair | 6.1.0 | 6.2.2 | atualizado | transitiva |
| altgraph | 0.17.5 | 0.17.5 | mantido | transitiva |
| anyio | 4.13.0 | 4.15.1 | atualizado | transitiva |
| ast-serialize | 0.6.0 | 0.11.1 | atualizado | transitiva |
| attrs | 26.1.0 | 26.1.0 | mantido | transitiva |
| black | 26.5.1 | 26.5.1 | mantido | direta: dev |
| blinker | 1.9.0 | ausente | removido | transitiva -> ausente |
| cachetools | 7.1.1 | ausente | removido | transitiva -> ausente |
| cairocffi | 1.7.1 | 1.7.1 | mantido | transitiva |
| cairosvg | 2.9.0 | 2.9.1 | atualizado | direta: build |
| certifi | 2026.2.25 | 2026.7.22 | atualizado | transitiva |
| cffi | 2.0.0 | 2.1.1 | atualizado | transitiva |
| cfgv | 3.5.0 | 3.5.0 | mantido | transitiva |
| charset-normalizer | 3.4.4 | 3.5.1 | atualizado | transitiva |
| click | 8.4.2 | 8.5.0 | atualizado | transitiva |
| colorama | 0.4.6 | 0.4.6 | mantido | transitiva |
| coverage | 7.13.4 | 7.16.0 | atualizado | transitiva |
| cssselect2 | 0.9.0 | 0.10.1 | atualizado | transitiva |
| defusedxml | 0.7.1 | 0.7.1 | mantido | direta: runtime |
| distlib | 0.4.0 | 0.4.3 | atualizado | transitiva |
| dmgbuild | 1.6.7 | ausente | removido | direta: build -> ausente |
| ds-store | 1.3.2 | ausente | removido | transitiva -> ausente |
| et-xmlfile | 2.0.0 | 2.0.0 | mantido | transitiva |
| exceptiongroup | 1.3.1 | 1.3.1 | mantido | transitiva |
| filelock | 3.29.7 | 3.32.6 | atualizado | direta: runtime |
| flake8 | 7.3.0 | 7.3.0 | mantido | direta: dev |
| gitdb | 4.0.12 | ausente | removido | transitiva -> ausente |
| gitpython | 3.1.58 | ausente | removido | transitiva -> ausente |
| h11 | 0.16.0 | 0.16.0 | mantido | transitiva |
| httptools | 0.7.1 | 0.8.0 | atualizado | transitiva |
| identify | 2.6.19 | 2.6.19 | mantido | transitiva |
| idna | 3.18 | 3.19 | atualizado | direta: runtime -> transitiva |
| iniconfig | 2.3.0 | 2.3.0 | mantido | transitiva |
| isort | 8.0.1 | ausente | removido | direta: dev -> ausente |
| itsdangerous | 2.2.0 | 2.2.0 | mantido | transitiva |
| jinja2 | 3.1.6 | 3.1.6 | mantido | transitiva |
| jsonschema | 4.26.0 | 4.26.0 | mantido | transitiva |
| jsonschema-specifications | 2025.9.1 | 2025.9.1 | mantido | transitiva |
| librt | 0.13.0 | 0.15.0 | atualizado | transitiva |
| lxml | ausente | 6.1.3 | adicionado | ausente -> direta: runtime |
| mac-alias | 2.2.3 | ausente | removido | transitiva -> ausente |
| macholib | 1.16.4 | 1.16.4 | mantido | transitiva |
| markupsafe | 3.0.3 | 3.0.3 | mantido | transitiva |
| mccabe | 0.7.0 | 0.7.0 | mantido | transitiva |
| mypy | 2.3.0 | 2.3.1 | atualizado | direta: dev |
| mypy-extensions | 1.1.0 | 1.1.0 | mantido | transitiva |
| narwhals | 2.21.0 | 2.26.0 | atualizado | transitiva |
| nodeenv | 1.10.0 | 1.10.0 | mantido | transitiva |
| nuitka | 4.1.3 | 4.2.1 | atualizado | direta: build |
| numpy | 2.2.6, 2.4.2 | 2.2.6, 2.4.6, 2.5.3 | atualizado | direta: runtime |
| openpyxl | 3.1.5 | 3.1.5 | mantido | direta: runtime |
| packaging | 26.0 | 26.3 | atualizado | transitiva |
| pandas | 2.3.3, 3.0.3 | 2.3.3, 3.0.5 | atualizado | direta: runtime |
| patchelf | 0.17.2.4 | 0.19.1.0 | atualizado | direta: build |
| pathspec | 1.0.4 | 1.1.1 | atualizado | transitiva |
| pefile | 2024.8.26 | 2024.8.26 | mantido | transitiva |
| pillow | 12.3.0 | 12.3.0 | mantido | direta: build, dev |
| platformdirs | 4.9.2 | 4.11.8 | atualizado | transitiva |
| pluggy | 1.6.0 | 1.6.0 | mantido | transitiva |
| pre-commit | 4.6.0 | 4.6.2 | atualizado | direta: dev |
| protobuf | 7.34.1 | 7.36.1 | atualizado | transitiva |
| pyarrow | 24.0.0 | 24.0.0 | mantido | transitiva |
| pycodestyle | 2.14.0 | 2.14.0 | mantido | transitiva |
| pycparser | 3.0 | 3.0 | mantido | transitiva |
| pydeck | 0.9.2 | 0.9.3 | atualizado | transitiva |
| pyflakes | 3.4.0 | 3.4.0 | mantido | transitiva |
| pygments | 2.20.0 | 2.21.0 | atualizado | transitiva |
| pyinstaller | 6.21.0 | 6.22.2 | atualizado | direta: build |
| pyinstaller-hooks-contrib | 2026.6 | 2026.7 | atualizado | transitiva |
| pyqt6 | 6.11.0 | 6.11.0 | mantido | direta: runtime |
| pyqt6-qt6 | 6.11.1 | 6.11.2 | atualizado | transitiva |
| pyqt6-sip | 13.11.0 | 13.12.0 | atualizado | transitiva |
| pytest | 9.1.1 | 9.1.1 | mantido | direta: dev |
| pytest-cov | 7.1.0 | 7.1.0 | mantido | direta: dev |
| pytest-timeout | 2.4.0 | 2.4.0 | mantido | direta: dev |
| python-dateutil | 2.9.0.post0 | 2.9.0.post0 | mantido | transitiva |
| python-discovery | 1.4.4 | 1.6.0 | atualizado | transitiva |
| python-multipart | 0.0.31 | 0.0.32 | atualizado | transitiva |
| pytokens | 0.4.1 | 0.4.1 | mantido | transitiva |
| pytz | 2025.2 | 2025.2 | mantido | transitiva |
| pywin32 | 311 | 311 | mantido | direta: build |
| pywin32-ctypes | 0.2.3 | 0.2.3 | mantido | transitiva |
| pyyaml | 6.0.3 | 6.0.3 | mantido | transitiva |
| referencing | 0.37.0 | 0.37.0 | mantido | transitiva |
| requests | 2.33.1 | 2.34.2 | atualizado | transitiva |
| rpds-py | 0.30.0 | 0.30.0 | mantido | transitiva |
| ruff | 0.15.21 | 0.16.6 | atualizado | direta: dev |
| setuptools | 83.0.0 | 83.0.0 | mantido | direta: backend |
| six | 1.17.0 | 1.17.0 | mantido | transitiva |
| smmap | 5.0.2 | ausente | removido | transitiva -> ausente |
| ssa-consulta-rapida | 4.50.0 | 4.50.0 | mantido | projeto local |
| starlette | 1.3.1 | 1.6.0 | atualizado | transitiva |
| streamlit | 1.58.0 | 1.63.0 | atualizado | direta: web |
| tabulate | 0.10.0 | 0.10.0 | mantido | direta: runtime |
| tenacity | 9.1.4 | ausente | removido | transitiva -> ausente |
| tinycss2 | 1.5.1 | 1.5.1 | mantido | transitiva |
| toml | 0.10.2 | 0.10.2 | mantido | transitiva |
| tomli | 2.4.0 | 2.4.1 | atualizado | transitiva |
| ty | 0.0.42 | 0.0.79 | atualizado | direta: dev |
| typing-extensions | 4.15.0 | 4.16.0 | atualizado | transitiva |
| tzdata | 2025.3 | 2025.3 | mantido | transitiva |
| urllib3 | 2.7.0 | 2.7.0 | mantido | transitiva |
| uvicorn | 0.46.0 | 0.52.4 | atualizado | transitiva |
| virtualenv | 21.6.1 | 21.7.9 | atualizado | direta: dev -> transitiva |
| watchdog | 6.0.0 | 6.0.0 | mantido | transitiva |
| webencodings | 0.5.1 | 0.6.1 | atualizado | transitiva |
| websockets | 16.0 | 16.1.1 | atualizado | transitiva |

## Inventario completo da .venv macOS

Os 63 nomes anteriores estao listados, inclusive os 25 sem mudanca de versao. O sync informou 39 desinstalacoes e 23 instalacoes: essas operacoes incluem substituicoes de versao e reinstalacao do projeto local; nao significam 39 pacotes eliminados do conjunto. O resultado foi 16 nomes removidos e 47 mantidos no ambiente.

A cadeia local de DDGS retirada compreende ddgs, anyio, brotli, certifi, fake-useragent, h11, h2, hpack, httpcore, httpx, hyperframe, primp e socksio. Alguns desses nomes permanecem no lock por consumidores de extras, como web.

| Pacote | Antes | Depois | Situacao |
|---|---|---|---|
| anyio | 4.14.2 | ausente | removido |
| ast-serialize | 0.6.0 | 0.11.1 | atualizado |
| black | 26.5.1 | 26.5.1 | mantido |
| brotli | 1.2.0 | ausente | removido |
| certifi | 2026.2.25 | ausente | removido |
| cfgv | 3.5.0 | 3.5.0 | mantido |
| click | 8.4.2 | 8.5.0 | atualizado |
| coverage | 7.13.4 | 7.16.0 | atualizado |
| ddgs | 9.15.0 | ausente | removido |
| defusedxml | 0.7.1 | 0.7.1 | mantido |
| distlib | 0.4.0 | 0.4.3 | atualizado |
| et-xmlfile | 2.0.0 | 2.0.0 | mantido |
| fake-useragent | 2.2.0 | ausente | removido |
| filelock | 3.29.7 | 3.32.6 | atualizado |
| flake8 | 7.3.0 | 7.3.0 | mantido |
| h11 | 0.16.0 | ausente | removido |
| h2 | 4.4.1 | ausente | removido |
| hpack | 4.2.0 | ausente | removido |
| httpcore | 1.0.9 | ausente | removido |
| httpx | 0.28.1 | ausente | removido |
| hyperframe | 6.1.0 | ausente | removido |
| identify | 2.6.19 | 2.6.19 | mantido |
| idna | 3.18 | ausente | removido |
| iniconfig | 2.3.0 | 2.3.0 | mantido |
| isort | 8.0.1 | ausente | removido |
| librt | 0.13.0 | 0.15.0 | atualizado |
| lxml | 6.1.0 | 6.1.3 | atualizado |
| mccabe | 0.7.0 | 0.7.0 | mantido |
| mypy | 2.3.0 | 2.3.1 | atualizado |
| mypy-extensions | 1.1.0 | 1.1.0 | mantido |
| nodeenv | 1.10.0 | 1.10.0 | mantido |
| numpy | 2.4.2 | 2.5.3 | atualizado |
| openpyxl | 3.1.5 | 3.1.5 | mantido |
| packaging | 26.0 | 26.3 | atualizado |
| pandas | 3.0.3 | 3.0.5 | atualizado |
| pathspec | 1.0.4 | 1.1.1 | atualizado |
| pillow | 12.3.0 | 12.3.0 | mantido |
| pip | 25.3 | ausente | removido |
| platformdirs | 4.9.2 | 4.11.8 | atualizado |
| pluggy | 1.6.0 | 1.6.0 | mantido |
| pre-commit | 4.6.0 | 4.6.2 | atualizado |
| primp | 1.3.1 | ausente | removido |
| pycodestyle | 2.14.0 | 2.14.0 | mantido |
| pyflakes | 3.4.0 | 3.4.0 | mantido |
| pygments | 2.20.0 | 2.21.0 | atualizado |
| pyqt6 | 6.11.0 | 6.11.0 | mantido |
| pyqt6-qt6 | 6.11.1 | 6.11.2 | atualizado |
| pyqt6-sip | 13.11.0 | 13.12.0 | atualizado |
| pytest | 9.1.1 | 9.1.1 | mantido |
| pytest-cov | 7.1.0 | 7.1.0 | mantido |
| pytest-timeout | 2.4.0 | 2.4.0 | mantido |
| python-dateutil | 2.9.0.post0 | 2.9.0.post0 | mantido |
| python-discovery | 1.4.4 | 1.6.0 | atualizado |
| pytokens | 0.4.1 | 0.4.1 | mantido |
| pyyaml | 6.0.3 | 6.0.3 | mantido |
| ruff | 0.15.21 | 0.16.6 | atualizado |
| six | 1.17.0 | 1.17.0 | mantido |
| socksio | 1.0.0 | ausente | removido |
| ssa-consulta-rapida | 4.50.0 | 4.50.0 | mantido |
| tabulate | 0.10.0 | 0.10.0 | mantido |
| ty | 0.0.42 | 0.0.79 | atualizado |
| typing-extensions | 4.15.0 | 4.16.0 | atualizado |
| virtualenv | 21.6.1 | 21.7.9 | atualizado |

## Inventario da .venv-linux antiga

Ambiente estrangeiro cujo interpretador nao executa neste macOS. As remocoes usaram metadata com prefixo explicito; nao foi realizado sync, upgrade ou teste nativo desse ambiente. Pip ja estava ausente. O inventario posterior abaixo corresponde a retirada documentada de idna/isort; as demais versoes foram preservadas.

| Pacote | Antes | Depois | Situacao |
|---|---|---|---|
| defusedxml | 0.7.1 | 0.7.1 | mantido |
| et-xmlfile | 2.0.0 | 2.0.0 | mantido |
| filelock | 3.24.3 | 3.24.3 | mantido |
| idna | 3.11 | ausente | removido |
| iniconfig | 2.3.0 | 2.3.0 | mantido |
| isort | 8.0.0 | ausente | removido |
| lxml | 6.1.0 | 6.1.0 | mantido |
| numpy | 2.4.2 | 2.4.2 | mantido |
| openpyxl | 3.1.5 | 3.1.5 | mantido |
| packaging | 26.0 | 26.0 | mantido |
| pandas | 3.0.0 | 3.0.0 | mantido |
| pluggy | 1.6.0 | 1.6.0 | mantido |
| pygments | 2.20.0 | 2.20.0 | mantido |
| pyqt6 | 6.10.2 | 6.10.2 | mantido |
| pyqt6-qt6 | 6.10.2 | 6.10.2 | mantido |
| pyqt6-sip | 13.11.0 | 13.11.0 | mantido |
| pytest | 9.0.3 | 9.0.3 | mantido |
| pytest-timeout | 2.4.0 | 2.4.0 | mantido |
| python-dateutil | 2.9.0.post0 | 2.9.0.post0 | mantido |
| six | 1.17.0 | 1.17.0 | mantido |
| ssa-consulta-rapida | 4.37.0 | 4.37.0 | mantido |
| tabulate | 0.9.0 | 0.9.0 | mantido |

Este ambiente continua antigo, incluindo SSA 4.37.0 e tabulate 0.9.0. Nao representa a versao 4.50.0 validada no macOS e nao deve ser apresentado como ambiente Linux atualizado ou aprovado.

## Outras mudancas no lock e nos manifestos

### Faixas de Python e limites de versao

| Python | pandas antes -> depois | NumPy antes -> depois |
|---|---|---|
| 3.10 | 2.3.3 -> 2.3.3 | 2.2.6 -> 2.2.6 |
| 3.11 | 3.0.3 -> 3.0.5 | 2.4.2 -> 2.4.6 |
| 3.12 ou superior | 3.0.3 -> 3.0.5 | 2.4.2 -> 2.5.3 |

O corte de NumPy 2.5 exige distinguir Python 3.11 de 3.12+. Isso acrescentou um registro NumPy e tres marcadores globais, mantendo as alternativas de plataforma ja existentes. A verificacao relatada cobriu 126 combinacoes do grafo de Python/plataforma/extras; foi uma conferencia de resolucao, nao 126 execucoes nativas.

Os metadados `requires-dist` e `requires-dev` incorporaram minimos atualizados e limites superiores das dependencias diretas. O criterio de major tomou como base as versoes ja resolvidas, e nao apenas os minimos textuais anteriores. Casos que poderiam ser confundidos com uma troca efetiva de major:

| Declaracao | Antes | Depois | Versao efetivamente resolvida |
|---|---|---|---|
| Backend setuptools | `>=82.0.1` | `>=83.0.0,<84` | 83.0.0 permaneceu igual |
| pandas em Python >=3.11 | `>=2.3.3` | `>=3.0.5,<4` | O lock ja usava 3.0.3 nessa faixa |
| virtualenv | Direta dev `>=20.36.1` | Constraint `>=21.7.9,<22` | O lock ja usava 21.6.1 |

O limite de major foi respeitado na selecao desta rodada. O lock fixa versoes atuais; nao foi criada uma politica permanente de restricao individual para toda dependencia transitiva em futuras resolucoes.

### Artefatos, fontes e estrutura

- Formato `version = 1`, `revision = 3`, Python minimo `>=3.10` e versao SSA 4.50.0 permaneceram.
- Extras `dev`, `build` e `web` foram preservados. O grupo dev e o extra dev continuam equivalentes; a exportacao `--only-dev` continua sem runtime/projeto local.
- Entrou uma secao `manifest` com as constraints idna e virtualenv. Elas limitam consumidores existentes, sem instalar esses pacotes por si mesmas.
- A metadata transitiva tambem mudou: AnyIO ampliou a dependencia de typing-extensions de Python <3.13 para <3.15; Click deixou de exigir colorama no Windows; python-discovery deixou de exigir platformdirs. Colorama permanece no lock por pytest, e platformdirs por virtualenv. As variantes NumPy foram propagadas para pandas, pydeck, Streamlit e o projeto local.
- Novas versoes e a inclusao de lxml trouxeram listas de wheels, distribuicoes fonte, URLs, hashes, tamanhos e datas dos respectivos artefatos. Isso responde por grande parte do diff de 2.518 linhas do lock.
- Dos 53 registros com versao inalterada, 52 sao externos e preservam fontes, URLs, hashes, tamanhos e datas; o outro e o projeto local, cuja metadata de dependencias mudou.
- Uma resolucao intermediaria utilizou um indice adicional da configuracao global local. Antes do commit, o lock foi regenerado com `uv lock --no-config --default-index https://pypi.org/simple`; todas as origens finais voltaram ao PyPI e as constraints permaneceram presentes. Nenhuma configuracao global foi alterada.

### Requirements e Ruff

Os requirements seguem como compatibilidade; pyproject.toml/uv.lock sao as fontes do fluxo principal. Os arquivos runtime/dev/build/CI e das quatro plataformas foram alinhados. `requirements_clean.txt` passou de 63 linhas de comentarios para duas, continuando sem dependencias. A lista de compatibilidade `requirements_ci.txt` inclui requirements_dev mais PyInstaller.

As listas de plataformas permaneceram planas. Uma tentativa intermediaria de compartilhar runtime com `-r` foi descartada antes do commit porque a assinatura de cache em `launchers/build_multiplatform.py` considera o conteudo do arquivo local, sem percorrer includes. A assinatura existente nao foi alterada. Equivalencia de requirements foi conferida em 18 cenarios Python/plataforma.

Ruff 0.16.6 ampliou as regras padrao e inicialmente produziu 175 avisos adicionais nos quatro arquivos Python inalterados examinados. Conforme a [migracao oficial do Ruff 0.16](https://astral.sh/blog/ruff-v0.16.0), `pyproject.toml` passou a declarar `select = ["E4", "E7", "E9", "F"]`. O conjunto habilitado foi comparado com Ruff 0.15.21 e permaneceu identico. Dois trechos novos do teste de shell receberam parenteses em concatenacoes de strings. Essa adaptacao preserva o lint anterior; nao demonstra compatibilidade de todas as outras mudancas upstream.

## Escopo dos scripts e arquivos alterados

| Arquivos | Mudanca registrada |
|---|---|
| `pyproject.toml`, `uv.lock` | Dependencias, constraints, faixas de Python e regras Ruff |
| `requirements.txt`, `requirements_dev.txt`, `requirements_build.txt`, `requirements_ci.txt`, `requirements_clean.txt` | Listas de compatibilidade atualizadas e comentarios simplificados |
| `launchers/platforms/debian_amd64/requirements.txt`, `launchers/platforms/debian_arm64/requirements.txt`, `launchers/platforms/macos_arm64/requirements.txt`, `launchers/platforms/windows_amd64/requirements.txt` | Runtime/build nas listas planas de cada plataforma |
| `scripts/env/direnv_common.sh`, `scripts/env/direnv_common.ps1` | Retirada de seed/ensurepip; criacao sem pip, preservando verificacao de ambiente/Python; selecao da opcao sem pip conforme backend pyenv |
| `dev_env/activate_repo.ps1` | Criacao/validacao do ambiente sem instalacao implicita de pip |
| `dev_env/bootstrap.sh`, `dev_env/bootstrap.ps1` | Instalacao principal por uv sync frozen, ambiente/Python explicitos e propagacao de falha |
| `scripts/env/setup_env.sh`, `scripts/env/setup_env.ps1` | Instalacao dev por uv no ambiente selecionado; erros de instalacao deixam de ser tratados como conclusao |
| `dev_env/activate_env.bat` | Preserva prioridade `.venv_build` sobre `.venv`; cria com uv e instala runtime pelo lock |
| `dev_env/setup_pyox_venv.bat` | Usa uv pip com Python explicito, preservando os pins proprios pandas 2.3.3/openpyxl 3.1.5/PyQt6 6.10.0 |
| `tests/test_shell_ci_contracts.py` | Casos para ambiente sem pip, selecao de backend e destino/falhas do uv |
| `scripts/env/README.md`, `dev_env/ENVIRONMENT_GUIDE.md`, `docs/COMANDOS_RAPIDOS.md` | Instrucoes alinhadas ao uv |

Os instaladores principais usam `--frozen --inexact`; o modo inexact preserva pacotes adicionais ja instalados. Portanto, a correcao de criacao evita semear pip, mas nao remove automaticamente um pip antigo em todos os outros ambientes. A limpeza exata de 63 para 47 foi uma operacao local separada com `uv sync --no-config --frozen`.

O script PyOx manual conserva uma lista independente. A existencia de um extra build no lock nao significa que esse ambiente manual foi atualizado ou validado.

## Evidencias e alcance da validacao tecnica

Resultados da execucao em **2026-09-09**, anteriores a este registro documental. Esta edicao documental nao repete instalacoes, sync ou testes da aplicacao.

| Verificacao | Resultado registrado | Limite |
|---|---|---|
| pytest focado | 134 passaram, um ignorado, 5,87 s | Caso opcional PyArrow ignorado no ambiente principal |
| pytest web em ambiente uv isolado | 55 passaram, 0,61 s | Funcionalidade testada com Streamlit atualizado; nao e teste de navegacao web completo |
| Total das duas execucoes | 189 passaram, um ignorado | Nao soma os 74 testes da execucao preliminar, que se sobrepoem |
| py_compile | Passou nos cinco arquivos Python examinados | Nao equivale a execucao funcional |
| Ruff 0.16.6 | Passou no teste alterado e nos quatro arquivos inalterados, apos preservar as regras anteriores | Novas regras padrao nao foram adotadas integralmente |
| ty 0.0.79 | Passou em `tests/test_shell_ci_contracts.py` | Nao foi uma verificacao global de tipos |
| ShellCheck | Tres scripts shell, nivel warning, passaram | Nao substitui execucao em todos os sistemas |
| PowerShell | Parser e PSScriptAnalyzer, nivel Error, quatro scripts, passaram | Warnings informativos existentes; Windows nativo nao executado |
| Semgrep/Vulture | Sem achados no teste alterado; Vulture com confianca minima 100 | Escopo restrito ao Python alterado |
| Bandit | Sem achados no escopo filtrado de testes | Filtros B101/B603/B607; B404 gerou aviso generico baixo sobre import subprocess e foi documentado/excluido na leitura focada |
| Gitleaks/Detect-secrets/Trufflehog | Sem segredos no diff/arquivos examinados | Trufflehog sem verificacao externa |
| uv pip check | 47 pacotes compativeis | Verifica requisitos declarados, nao compatibilidade semantica |
| Ativacao real POSIX | Duas ativacoes preservaram inode da `.venv` e ausencia de pip | Somente macOS local |
| Sync frozen seco final | Sem alteracoes previstas nos 47 pacotes | Confere o conjunto selecionado naquele ambiente |
| Revisao independente dos scripts | Nenhum bug bloqueante confirmado; dois apontamentos menores foram refutados com verificacoes isoladas | Nao certifica todos os fluxos/plataformas |

Os dez modulos do pytest focado foram: `test_shell_ci_contracts`, `test_dev_env_build_scripts`, `test_exporter`, `test_import_excel_file`, `test_filter_regex_invalid_fallback`, `test_search_filtering_logic`, `test_filter_cache_locking`, `test_contract_filter_worker_cancel_race`, `test_filter_dataframe_exact_identifier_performance` e `test_gui_preferences_atomic_write`. A execucao web usou `test_streamlit_filter_cache` e `test_main_streamlit_launcher`. Ambas usaram timeout de 45 s com metodo thread; timeout nao foi considerado sucesso.

### Auditoria de dependencias

pip-audit **2.10.1**, servico PyPI, em **2026-09-09T19:20:22Z**: **99 pares nome/versao**, **zero vulnerabilidades conhecidas**, **zero pacotes ignorados**. Tres lotes de 96, dois e um pares terminaram com codigo zero, usando `--strict --disable-pip --no-deps`. Incluem os 46 pacotes externos instalados; SSA local e o 47o pacote e nao foi submetido como distribuicao PyPI. A ferramenta rodou isolada, sem reinserir pip no projeto.

O SHA256 do lock auditado coincide com o commit final. A consulta cobre vulnerabilidades conhecidas dessas versoes naquela data, incluindo variantes do lock; nao executa binarios Windows/Linux, nao identifica falhas desconhecidas e nao demonstra ausencia de regressao funcional. Novos avisos publicados depois dessa data nao estao cobertos por esse resultado.

### GUI e desempenho

A GUI Cocoa abriu com o Qt atualizado e renderizou cinco linhas sinteticas em configuracao temporaria. A captura `ssa_uv_atualizado_20260909.png` foi inspecionada. IDs curtos e contador zerado pertencem ao harness utilizado; esse smoke nao comprova um carregamento real completo ou ausencia de problemas com dados de producao.

Comparacao XLSX equivalente, 2.500 linhas x 16 colunas, tres repeticoes por conjunto, mesmo Python e backend lxml/defusedxml:

| Medida | Antes | Depois | Diferenca |
|---|---:|---:|---:|
| Escrita, mediana | 134,981 ms | 135,664 ms | +0,51% |
| Leitura, mediana | 120,453 ms | 121,342 ms | +0,74% |
| RSS maximo | 126,140 MB | 128,565 MB | +1,92% |

Conjunto anterior: NumPy 2.4.2, pandas 3.0.3 e lxml 6.1.0. Atual: NumPy 2.5.3, pandas 3.0.5 e lxml 6.1.3. Ambos usaram openpyxl 3.1.5 e defusedxml 0.7.1. Uma primeira comparacao isolada omitia defusedxml e foi descartada como evidencia comparavel. A amostra final e pequena, nao tem intervalo de confianca e nao substitui medicao de CPU/memoria/latencia da GUI com base representativa.

### Publicacao e CI do SHA tecnico final

Os commits foram enviados a dev nos tres remotos configurados. Nenhum novo binario, tag, branch, PR ou merge fez parte dessa rodada.

| Destino | Resultado para `36706e7784a44f060761bbfe35d070971ac571fc` |
|---|---|
| GitLab | [Pipeline 2834411660](https://gitlab.com/mauricio.menon/ssa_consulta_rapida_pyqt6/-/pipelines/2834411660) aprovado; verify/security, 1m11; conferido na sessao autenticada |
| GitHub principal | [minimal-ci](https://github.com/mauriciomenon/SSA_Consulta_Rapida/actions/runs/34394997425), [Secret Scan](https://github.com/mauriciomenon/SSA_Consulta_Rapida/actions/runs/34394997311) e [CodeQL](https://github.com/mauriciomenon/SSA_Consulta_Rapida/actions/runs/34394997494) encerrados por bloqueio de cobranca da conta; sete jobs sem etapas/runner e dois ignorados; nenhum codigo executado |
| GitHub secundario | Push confirmado; CI sem acesso pela sessao/API disponivel; resultado desconhecido |

Os alertas de vulnerabilidade exibidos pelos pushes referiam-se as branches padrao dos remotos. Eles nao foram usados como resultado da auditoria local do lock desta branch.

## Fontes, preservacao e verificacao do registro

As tabelas completas acima preservam os nomes/versoes no Git e nao dependem de um link temporario para serem lidas. Os locks e manifestos originais podem ser consultados pelo historico dos commits. As evidencias locais listadas abaixo foram fontes deste registro; seus arquivos brutos permanecem em `/tmp`, sujeitos a limpeza, e nao estao integralmente versionados. Hash identifica o arquivo, mas nao substitui sua preservacao.

| Fonte | SHA256 |
|---|---|
| uv.lock antes, commit a9160ce9 | `294c68a5184c0eabd17b0cddb0fce87fe3fcc79809df433e867405ae1dbd69f3` |
| uv.lock depois, commit 36706e77 | `0d87aa5a6c6925235df7a927939849e04f0e03ea0512d40579411b0e44965eac` |
| `ssa_uv_pacotes_antes_depois_20260909.json` | `030aabd8d83304a76703ba91afac783d34a3013b57cd7af08dc5ea4c427a923f` |
| `ssa_uv_linux_before_cleanup_20260909.json` | `c992a67c13e87dc8542f88d8f4965559194253894ab0d3eff92fa5462c317833` |
| `ssa_uv_audit_20260909_161855_summary.json` | `bc925ab325a026bb792e362e5d82175eb4f924fac7e3cd4091080dadf4d43cad` |
| `ssa_uv_xlsx_baseline_complete.json` | `2f9920904aff487eae9760bfd555e1b1ada471132fc0796be00630ab5984762f` |
| `ssa_uv_xlsx_updated_complete.json` | `382a5e109b466f7e89e1ccbc96d0ecfaef4e5f9b3069383a321db6c09eb7db35` |
| `ssa_uv_atualizado_20260909.png` | `9837ab3abd660da23a709c6fc88bfc24c6fe6025e5584fcc727fc8231938e25e` |

Backups dos arquivos alterados foram criados com timestamp e hashes conferidos antes das edicoes. Prefixos locais: `ssa_uv_limpeza_20260909_155702_*`, `ssa_uv_limpeza_20260909_160453_*`, `ssa_uv_scripts_20260909_160405_*`, `ssa_uv_docs_20260909_164700_*` e `ssa_uv_ruff_rules_20260909_162500_*`. Eles nao sao snapshots completos dos ambientes, caches ou dados da aplicacao. Nao foi testada uma recuperacao completa de todos os hosts a partir deles.

Conferencia somente de leitura do historico:

```bash
git show a9160ce9:uv.lock
git show 36706e77:uv.lock
git diff a9160ce9 36706e77 -- pyproject.toml uv.lock
git diff --stat a9160ce9 36706e77
```

## Riscos pendentes e proxima atividade

- Revisao individual de compatibilidade/changelog dos 45 upgrades nao concluida; atencao especial aos pacotes 0.x e ferramentas de build.
- Execucao nativa Windows 11 amd64/arm64 e Linux amd64/arm64 nao realizada nesta rodada; builds completos e executaveis distribuidos nao foram validados.
- O ambiente Linux antigo continua desatualizado. O ambiente PyOx manual tem pins independentes. Scripts inexact podem conservar pacotes extras preexistentes em outros ambientes.
- Testes focados, auditoria de versoes e benchmark pequeno nao cobrem toda a aplicacao, concorrencia, dados de producao ou desempenho por plataforma.
- CI GitHub permanece incompleto por cobranca/acesso; GitLab aprovado tem o escopo do pipeline executado, nao de toda a matriz nativa.
- Parte das evidencias brutas e dos backups continua temporaria; este documento preserva os inventarios/resultados e a identidade das fontes, sem afirmar reproducao integral do estado local anterior.

Entrega documental: inventarios completos, classificacao direta/transitiva, decisoes, resultados, fontes e limites registrados. Proxima atividade tecnica pendente: definir um slice especifico de revisao de compatibilidade e validacao nativa. Esse trabalho nao integra a aprovacao exclusivamente documental deste registro.
