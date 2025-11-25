# Guia de Distribuicao - SSA Consulta Rapida

**Versao**: 4.11.1
**Data**: 2025-11-19

## Visao Geral

Este guia descreve como criar e distribuir pacotes do SSA Consulta Rapida para usuarios finais.

## Pacotes Disponiveis

O sistema oferece 3 tipos de pacotes, cada um otimizado para um caso de uso diferente:

| Build System | Tamanho ZIP | Executavel | Melhor Para |
|--------------|-------------|-----------|-------------|
| PyOxidizer   | 125 MB      | 3.4 MB    | Distribuicao publica (menor download) |
| PyInstaller  | 169 MB      | 30 MB     | Desenvolvimento e testes rapidos |
| Nuitka       | 187 MB      | 142 MB    | Performance maxima (codigo nativo) |

## Criando Pacotes de Distribuicao

### Opcao 1: Criar todos os pacotes

```bash
python scripts/create_distribution.py --all --skip-installer
```

Cria arquivos ZIP para os 3 build systems.

### Opcao 2: Criar pacote especifico

```bash
# Apenas PyOxidizer (recomendado para distribuicao)
python scripts/create_distribution.py --build-system pyoxidizer --skip-installer

# Apenas PyInstaller
python scripts/create_distribution.py --build-system pyinstaller --skip-installer

# Apenas Nuitka
python scripts/create_distribution.py --build-system nuitka --skip-installer
```

### Opcao 3: Criar instalador Windows (Inno Setup)

Requer Inno Setup instalado: https://jrsoftware.org/isdl.php

```bash
# Com instalador
python scripts/create_distribution.py --build-system pyoxidizer

# Apenas instalador (sem ZIP)
python scripts/create_distribution.py --build-system pyoxidizer --installer-only
```

## Estrutura dos Pacotes

Cada pacote ZIP contem:

```
SSA_Consulta_Rapida_v4.11.1_[build]/
├── SSA_Consulta_Rapida.exe (ou main.exe para Nuitka)
├── _internal/                 # Dependencias (PyInstaller)
├── lib/                       # Bibliotecas (PyOxidizer)
├── config/                    # Arquivos de configuracao
├── data/                      # Diretorio para bancos de dados
│   └── historico_backups/    # Backups automaticos
├── docs_entrada/             # Coloque arquivos Excel aqui
├── docs_saida/               # Exportacoes CSV/Excel
├── logs/                     # Logs de execucao
├── reports/                  # Relatorios gerados
├── exportacao/               # Exportacoes personalizadas
├── docs/                     # Documentacao
│   └── ANTIVIRUS_EXCLUSOES.txt
├── LEIA-ME-USUARIO.txt       # Instrucoes para usuario final
├── LEIA-ME.txt               # README principal
└── VERSION.txt               # Informacoes de versao
```

## Distribuindo para Usuarios Finais

### Recomendacoes por Caso de Uso

#### 1. Distribuicao Publica (Internet)
**Use**: PyOxidizer (125 MB)
- Menor tamanho de download
- Executavel compacto (3.4 MB)
- Python embedado otimizado

#### 2. Distribuicao Interna (Rede Local)
**Use**: PyInstaller (169 MB) ou Nuitka (187 MB)
- PyInstaller: Mais facil debug se houver problemas
- Nuitka: Melhor performance para operacoes intensivas

#### 3. Ambiente Corporativo Seguro
**Use**: Nuitka (187 MB)
- Codigo compilado nativo (mais dificil engenharia reversa)
- Performance maxima
- Melhor para grandes volumes de dados

### Instrucoes para o Usuario Final

Incluir no email/comunicado:

```
SSA Consulta Rapida v4.11.1

INSTALACAO:

1. Baixe o arquivo ZIP
2. Extraia para uma pasta de sua preferencia
   Exemplo: C:\Programas\SSA_Consulta_Rapida
3. Leia o arquivo LEIA-ME-USUARIO.txt para instrucoes completas

IMPORTANTE ANTIVIRUS:

Alguns antivirus podem bloquear o executavel na primeira execucao.
Se isso ocorrer:
- Adicione a pasta do programa nas exclusoes do antivirus
- Consulte: docs/ANTIVIRUS_EXCLUSOES.txt

PRIMEIRO USO:

1. Clique duas vezes em SSA_Consulta_Rapida.exe
2. Coloque arquivos Excel em: docs_entrada/
3. Execute novamente para importar os dados

SUPORTE:

- Documentacao completa na pasta docs/
- Logs em: logs/ssa.log
```

## Atualizando Versao Existente

Instrucoes para usuarios atualizarem sem perder dados:

1. Baixar nova versao
2. Extrair em pasta temporaria
3. Copiar apenas o executavel principal e pasta _internal/lib
4. MANTER as pastas do usuario:
   - data/ (bancos de dados)
   - config/ (configuracoes personalizadas)
   - docs_entrada/ (arquivos do usuario)
   - docs_saida/ (exportacoes)

## Checklist de Distribuicao

Antes de distribuir, verificar:

- [ ] Versao correta em VERSION.txt
- [ ] README para usuario incluido
- [ ] Documentacao de antivirus incluida
- [ ] Estrutura de diretorios completa
- [ ] Executavel funcional (testar --version e --help)
- [ ] Tamanho do ZIP razoavel
- [ ] Nome do arquivo descritivo (inclui versao e build system)

## Integracao com Build Scripts

Para integrar a criacao de pacotes com os scripts de build existentes:

### build_pyinstaller.bat
Adicionar ao final:
```batch
echo Criando pacote de distribuicao...
python scripts/create_distribution.py --build-system pyinstaller --skip-installer
```

### build_pyoxidizer.bat
Adicionar ao final:
```batch
echo Criando pacote de distribuicao...
python scripts/create_distribution.py --build-system pyoxidizer --skip-installer
```

### build_nuitka.bat
Adicionar ao final:
```batch
echo Criando pacote de distribuicao...
python scripts/create_distribution.py --build-system nuitka --skip-installer
```

## Criando Instalador Windows

### Requisitos

1. Baixar e instalar Inno Setup: https://jrsoftware.org/isdl.php
2. Instalar em: `C:\Program Files (x86)\Inno Setup 6\`

### Criando o Instalador

```bash
python scripts/create_distribution.py --build-system pyoxidizer
```

O instalador sera criado em: `dist_packages/SSA_Consulta_Rapida_v4.11.1_pyoxidizer_Setup.exe`

### Recursos do Instalador

- Instalacao em nivel de usuario (nao requer admin)
- Cria atalho no desktop
- Cria grupo no menu Iniciar
- Cria estrutura de diretorios automaticamente
- Opcao de executar ao final da instalacao
- Desinstalador completo

## Troubleshooting

### Pacote muito grande

Se o pacote ZIP estiver muito grande:

1. Verificar se bancos de dados de teste foram incluidos
2. Remover logs desnecessarios antes de empacotar
3. Considerar usar PyOxidizer (menor)

### Executavel nao funciona no cliente

1. Verificar se todas as DLLs necessarias foram incluidas
2. Testar em maquina limpa (sem Python instalado)
3. Verificar configuracao de antivirus
4. Consultar logs em logs/ssa.log

### Erro ao criar ZIP

1. Verificar espaco em disco suficiente
2. Verificar permissoes de escrita em dist_packages/
3. Fechar programas que possam estar usando os arquivos
4. Verificar se build existe (executar build antes)

## Metricas de Distribuicao

Comparacao dos pacotes criados:

| Metrica | PyOxidizer | PyInstaller | Nuitka |
|---------|------------|-------------|--------|
| Tamanho ZIP | 125 MB | 169 MB | 187 MB |
| Executavel | 3.4 MB | 30 MB | 142 MB |
| Tempo criacao | ~4 min | ~2 min | ~1 min |
| Compressao | Otima | Boa | Regular |

## Proximos Passos

1. **Automatizar no CI/CD**
   - Gerar pacotes automaticamente a cada release
   - Publicar em repositorio interno

2. **Assinatura Digital**
   - Assinar executaveis para evitar avisos do Windows
   - Usar certificado code signing

3. **Atualizacao Automatica**
   - Implementar verificacao de versao
   - Download automatico de atualizacoes

4. **Telemetria (Opcional)**
   - Coletar metricas de uso anonimas
   - Identificar problemas comuns

---

**Autor**: Sistema automatizado de distribuicao
**Ultima atualizacao**: 2025-11-19
