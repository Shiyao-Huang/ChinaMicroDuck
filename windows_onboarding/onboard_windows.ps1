# Windows U 一键入网 Microduck Tailnet
# 以管理员身份运行 PowerShell，粘贴本脚本全部内容
$ErrorActionPreference = "Continue"
Write-Host "== 1. 安装 Tailscale =="
winget install tailscale.tailscale --accept-source-agreements --accept-package-agreements 2>$null
if (-not (Get-Command tailscale -ErrorAction SilentlyContinue)) {
  $msi = "$env:TEMP\tailscale-setup.msi"
  Invoke-WebRequest -Uri "https://pkgs.tailscale.com/stable/tailscale-setup-latest-amd64.msi" -OutFile $msi
  Start-Process msiexec.exe -ArgumentList "/i $msi /qn" -Wait
}
Start-Sleep 3
Write-Host "== 2. 用 authkey 入网（免浏览器）=="
& "C:\Program Files\Tailscale\tailscale.exe" up --authkey "tskey-auth-ktDe9zw5qL11CNTRL-bpLoh8yxUrMf5ESuoYt7rMfWHy4pZ5xE" --hostname "copizza-win"
Write-Host "== 3. 本机 IP =="
& "C:\Program Files\Tailscale\tailscale.exe" ip -4
Write-Host "== 4. 顺便装 egolite（如有包）=="
$ego = "$env:TEMP\egolite-setup.exe"
try {
  Invoke-WebRequest -Uri "https://github.com/Shiyao-Huang/ChinaMicroDuck/releases/download/fleet-v1/egolite-0.5.0.18.dmg" -OutFile $ego -ErrorAction Stop
  Write-Host "egolite dmg 已下载（dmg 为 Mac 格式，Windows 请用官网 exe）"
} catch { Write-Host "egolite: Windows 版请从官网安装" }
Write-Host "== 完成！回到 Microduck 会话告知 =="
