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
    Write-Host "Telecharge Git depuis: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Verifier si remote existe
$remote = git remote -v 2>$null
if ($remote) {
    Write-Host "Remote actuel:" -ForegroundColor Yellow
    Write-Host $remote
    Write-Host ""
    $useExisting = Read-Host "Utiliser ce remote? (O/N)"
    if ($useExisting -eq "O" -or $useExisting -eq "o") {
        $repoUrl = ($remote -split "`t")[1] -replace " \(fetch\)", ""
    } else {
        $repoUrl = Read-Host "Entrez l'URL du repository GitHub"
        git remote set-url origin $repoUrl
    }
} else {
    Write-Host "Aucun remote configure" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "INSTRUCTIONS:" -ForegroundColor Cyan
    Write-Host "1. Va sur: https://github.com/new"
    Write-Host "2. Nom: mia-ia-system-website"
    Write-Host "3. NE COCHE PAS 'Initialize with README'"
    Write-Host "4. Cree le repo"
    Write-Host ""
    $repoUrl = Read-Host "Entrez l'URL complete du repo (ex: https://github.com/jackson97300/mia-ia-system-website.git)"

    if ($repoUrl) {
        git remote add origin $repoUrl
        Write-Host "Remote ajoute!" -ForegroundColor Green
    } else {
        Write-Host "URL vide, annulation..." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Verifier changements
$status = git status --short
if ($status) {
    Write-Host "Changements detectes, ajout au commit..." -ForegroundColor Yellow
    git add .
    Write-Host ""
    $commitMsg = Read-Host "Message du commit (ou Enter pour 'update')"
    if (-not $commitMsg) { $commitMsg = "update" }
    git commit -m $commitMsg
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
    Write-Host "Verifiez que le repo existe sur GitHub et que vous avez les droits" -ForegroundColor Yellow
}

Write-Host ""
