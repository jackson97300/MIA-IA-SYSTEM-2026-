param(
    [Parameter(Mandatory=$true)]
    [string]$RepoUrl
)

Write-Host ""
Write-Host "=== MIA IA SYSTEM - PUSH GITHUB ===" -ForegroundColor Cyan
Write-Host ""

$repoPath = $PSScriptRoot
Set-Location $repoPath

# Verifier Git
try {
    $gitVersion = git --version
    Write-Host "Git detecte: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "ERREUR: Git n'est pas installe!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Configurer remote
$remote = git remote -v 2>$null
if ($remote) {
    Write-Host "Remote existe deja, mise a jour..." -ForegroundColor Yellow
    git remote set-url origin $RepoUrl
} else {
    Write-Host "Ajout du remote..." -ForegroundColor Yellow
    git remote add origin $RepoUrl
}

Write-Host "Remote configure: $RepoUrl" -ForegroundColor Green
Write-Host ""

# Verifier changements
$status = git status --short
if ($status) {
    Write-Host "Changements detectes, ajout au commit..." -ForegroundColor Yellow
    git add .
    git commit -m "update: Site web MIA IA SYSTEM"
    Write-Host ""
}

# Push
Write-Host "Push vers GitHub..." -ForegroundColor Cyan
Write-Host ""

# Essayer master d'abord
git push -u origin master 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    # Si master echoue, essayer main
    Write-Host "'master' echoue, essai avec 'main'..." -ForegroundColor Yellow
    git branch -M main 2>&1 | Out-Null
    git push -u origin main
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "PUSH REUSSI!" -ForegroundColor Green
    Write-Host "Votre code est maintenant sur GitHub" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Erreur lors du push" -ForegroundColor Red
    Write-Host "Verifiez que le repo existe sur GitHub: $RepoUrl" -ForegroundColor Yellow
}

Write-Host ""
