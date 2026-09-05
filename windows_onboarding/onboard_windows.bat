@echo off
REM Windows U 一键入网 - 双击运行（需要管理员权限，右键"以管理员身份运行"）
echo ============================================
echo  Microduck Tailnet 入网脚本
echo ============================================

where winget >nul 2>nul
if %errorlevel%==0 (
  winget install tailscale.tailscale --accept-source-agreements --accept-package-agreements
) else (
  curl -L -o %TEMP%\tailscale-setup.exe https://pkgs.tailscale.com/stable/tailscale-setup-latest-amd64.exe
  %TEMP%\tailscale-setup.exe /quiet
)
timeout /t 8 /nobreak >nul

"C:\Program Files\Tailscale\tailscale.exe" up --authkey tskey-auth-ktDe9zw5qL11CNTRL-bpLoh8yxUrMf5ESuoYt7rMfWHy4pZ5xE --hostname copizza-win
"C:\Program Files\Tailscale\tailscale.exe" ip -4

echo ============================================
echo  完成！本机已加入 Tailnet
echo ============================================
pause
