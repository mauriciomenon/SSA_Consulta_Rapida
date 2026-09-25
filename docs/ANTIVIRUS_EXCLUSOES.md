# Configuracao de Antivirus para Builds Python

## Problema Comum

Ferramentas de build Python (PyInstaller, Nuitka, PyOxidizer) geram executaveis que podem ser sinalizados como falso-positivos por antivirus porque:

1. Empacotam Python interpreter completo
2. Criam executaveis auto-extraiveis
3. Modificam comportamento de execucao do sistema
4. Nao tem assinatura digital

## Solucao: Adicionar Exclusoes

### Windows Defender

**Via Interface Grafica:**

1. Abrir Windows Security
2. Virus & threat protection
3. Manage settings
4. Add or remove exclusions
5. Adicionar:
   - `<repo>\build\`
   - `<repo>\dist\`

**Via PowerShell (Admin):**

```powershell
$Repo = "C:\caminho\para\SSA_Consulta_Rapida"
Add-MpPreference -ExclusionPath "$Repo\build"
Add-MpPreference -ExclusionPath "$Repo\dist"
```

Nao use `-ExclusionExtension "*.exe"`: a exclusao por extensao vale para o
sistema inteiro, nao so para o repositorio.

### Outros Antivirus

**Avast/AVG:**
- Settings > General > Exclusions
- Add folders: `<repo>\build\` e `<repo>\dist\`

**Kaspersky:**
- Settings > Additional > Threats and Exclusions > Exclusions > Manage Exclusions
- Add folder

**Norton:**
- Settings > Antivirus > Scans and Risks > Exclusions/Low Risks
- Configure Items to Exclude from Scans

## Alternativa: Assinatura Digital

Para builds de producao, considere assinar digitalmente os executaveis:

1. Comprar certificado de code signing
2. Usar ferramenta signtool.exe do Windows SDK
3. Assinar todos os .exe gerados

```batch
signtool sign /f certificado.pfx /p senha /t http://timestamp.digicert.com SSA_Consulta_Rapida.exe
```

## Verificacao

Apos adicionar exclusoes, verificar se arquivos existem:

```bash
ls -lh build/x86_64-pc-windows-msvc/release/install/*.exe
ls -lh dist/SSA_Consulta_Rapida/*.exe
ls -lh build/nuitka/main.dist/*.exe
```

## Monitoramento

Ver logs do Windows Defender para confirmar que nao esta mais bloqueando:

```powershell
Get-MpThreatDetection | Select-Object -Last 10
```

---

**Importante**: Adicionar exclusoes apenas para diretorio de desenvolvimento.
NAO adicionar exclusoes amplas que possam reduzir seguranca do sistema.

<!-- DOC_SYNC_MAC: 2026-03-29 host-agnostic paths, continue from repo root on macOS -->

