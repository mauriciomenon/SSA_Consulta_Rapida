<#
  Wrapper that keeps backward compatibility with previous activate_env.ps1 usage.
  Usage: . .\activate_env.ps1 [-Variant stable|free-threaded]
#>
[CmdletBinding()]
param(
    [string]$Variant
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir 'activate_repo.ps1') -Variant $Variant