$ErrorActionPreference = "Stop"

function Restart-Service {
    param (
        [string]$ServiceName
    )

    if ([string]::IsNullOrWhiteSpace($ServiceName)) {
        Write-Host "Please specify a service name (e.g., backend, frontend, db, redis) or 'all'." -ForegroundColor Yellow
        return
    }

    if ($ServiceName -eq "all") {
        Write-Host "🔄 Restarting ALL containers..." -ForegroundColor Cyan
        docker-compose restart
    } else {
        Write-Host "🔄 Restarting container: $ServiceName..." -ForegroundColor Cyan
        docker-compose restart $ServiceName
    }

    if ($?) {
        Write-Host "✅ Container '$ServiceName' restarted successfully." -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to restart container '$ServiceName'." -ForegroundColor Red
    }
}

# Check for arguments
if ($args.Count -eq 0) {
    Write-Host "Usage: .\restart-service.ps1 <service_name|all>"
    Write-Host "Examples:"
    Write-Host "  .\restart-service.ps1 backend"
    Write-Host "  .\restart-service.ps1 all"
} else {
    Restart-Service -ServiceName $args[0]
}
