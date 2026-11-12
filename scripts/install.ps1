# install.ps1 —— Windows 入口。
# 找到 Git for Windows 自带的 bash（避开 WindowsApps 里指向 wsl.exe 的占位程序），
# 再把参数原样交给同目录的 install.sh。
#
# 用法与 install.sh 相同。在「目标仓库根」执行（当前目录 = 要装进的项目）：
#   <data-workflow>\scripts\install.ps1
#   <data-workflow>\scripts\install.ps1 --project --with-hooks
#   <data-workflow>\scripts\install.cmd   # 等价入口，不受 ExecutionPolicy 影响
#
# 不要用 bash -l：登录壳会切走当前目录，install.sh 就会把技能装到错误的位置。
# 不要用 PowerShell 去拼 bash -c "echo $HOME"：$HOME 会被 PowerShell 先展开。

$ErrorActionPreference = "Continue"
$InstallSh = Join-Path $PSScriptRoot "install.sh"
if (-not (Test-Path -LiteralPath $InstallSh)) {
    Write-Host "ERROR: 找不到 $InstallSh"
    exit 2
}

function Find-GitBash {
    $candidates = @()
    if ($env:ProgramFiles) {
        $candidates += (Join-Path $env:ProgramFiles "Git\bin\bash.exe")
    }
    $pf86 = ${env:ProgramFiles(x86)}
    if ($pf86) {
        $candidates += (Join-Path $pf86 "Git\bin\bash.exe")
    }
    foreach ($p in $candidates) {
        if ($p -and (Test-Path -LiteralPath $p)) { return $p }
    }
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git -and $git.Source) {
        $root = Split-Path (Split-Path $git.Source -Parent) -Parent
        $sibling = Join-Path $root "bin\bash.exe"
        if (Test-Path -LiteralPath $sibling) { return $sibling }
    }
    return $null
}

$bash = Find-GitBash
if (-not $bash) {
    Write-Host "ERROR: 找不到 Git Bash。"
    Write-Host "       Windows 上不要直接敲 bash：PATH 里的 bash 常常是还没安装发行版的 WSL，"
    Write-Host "       跑起来只会提示安装 Linux，不会执行本脚本。"
    Write-Host "       请先安装 Git for Windows：https://git-scm.com/download/win"
    Write-Host "       装好后再在目标仓库根执行："
    Write-Host ("         " + (Join-Path $PSScriptRoot "install.cmd"))
    exit 2
}

# 当前目录保持为调用时的目录（目标仓库）。参数原样交给 install.sh。
$argList = @($InstallSh) + $args
& $bash @argList
exit $LASTEXITCODE
