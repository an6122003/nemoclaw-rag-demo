# SPDX-License-Identifier: Apache-2.0
#
# The RTX Spark (Windows) edition has its own repository now:
#
#     https://github.com/an6122003/rtx-spark-ai-workshop
#
# This file stays so the old command keeps working, for new installs and for
# updates of an existing ~\ai-workshop: it runs the new installer, which is
#
#     irm https://raw.githubusercontent.com/an6122003/rtx-spark-ai-workshop/main/install.ps1 | iex
#
# This file stays ASCII: `irm | iex` runs it as text, in the user's own session,
# so it ends with `return`, never `exit` (which would close their window).

& {
    $ProgressPreference = 'SilentlyContinue'
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    } catch {}
    Write-Host ''
    Write-Host '   The RTX Spark workshop has moved to github.com/an6122003/rtx-spark-ai-workshop' -ForegroundColor Yellow
    Write-Host '   Workshop RTX Spark da chuyen sang kho moi: github.com/an6122003/rtx-spark-ai-workshop' -ForegroundColor DarkGray
    # The old default branch name means nothing in the new repository.
    if ($env:WORKSHOP_BRANCH -eq 'windows') { Remove-Item Env:WORKSHOP_BRANCH }
    try {
        $installer = Invoke-RestMethod 'https://raw.githubusercontent.com/an6122003/rtx-spark-ai-workshop/main/install.ps1'
    } catch {
        Write-Host "   Could not download the installer ($($_.Exception.Message))." -ForegroundColor Red
        Write-Host '   Check the internet connection, then run the command again.' -ForegroundColor Red
        return
    }
    Invoke-Expression $installer
}
