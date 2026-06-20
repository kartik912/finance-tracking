# scripts/qa_check.ps1
# Canonical QA entrypoint for the Finance Tracking App.
# Exit code 0 = safe to commit. Non-zero = BLOCK.
# Run manually, or wire as a git pre-commit hook (see scripts/git-hooks/pre-commit).

$ErrorActionPreference = "Stop"
$failed = $false

function Step($name, [scriptblock]$body) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    try {
        & $body
        Write-Host "[PASS] $name" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] $name`: $_" -ForegroundColor Red
        $script:failed = $true
    }
}

# --- Step 0: Environment integrity ---
Step "Env check (flet version pin)" {
    $pinned = (Select-String -Path requirements.txt -Pattern "flet==").Line -replace ".*flet==", ""
    $installed = (.\.venv\Scripts\python.exe -m pip show flet | Select-String "Version:").ToString() -replace ".*Version:\s*", ""
    if ($pinned -and ($pinned.Trim() -ne $installed.Trim())) {
        throw "requirements.txt pins flet==$pinned but $installed is installed. flet-api.instructions.md needs re-audit before continuing."
    }
}

# --- Step 1: Clear stale bytecode ---
Get-ChildItem -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force

# --- Step 2: Syntax & import smoke test ---
Step "Syntax check" {
    .\.venv\Scripts\python.exe -c "
import py_compile, glob, sys
errors = []
for f in glob.glob('**/*.py', recursive=True):
    if '.venv' in f or '__pycache__' in f:
        continue
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(str(e))
if errors:
    for e in errors: print('SYNTAX ERROR:', e)
    sys.exit(1)
print('Syntax OK')
"
    if ($LASTEXITCODE -ne 0) { throw "syntax errors found" }
}

# --- Step 3: Layer dependency check ---
Step "Layer dependency check" {
    .\.venv\Scripts\python.exe -c "
import re, glob, sys
violations = []
for f in glob.glob('screens/*.py') + glob.glob('components/*.py'):
    src = open(f, encoding='utf-8').read()
    if re.search(r'from repositories\.|import repositories\.', src):
        violations.append(f)
if violations:
    for v in violations: print('LAYER VIOLATION:', v)
    sys.exit(1)
print('Layer check OK')
"
    if ($LASTEXITCODE -ne 0) { throw "screens/components importing repositories directly" }
}

# --- Step 4: API contract check (Flet forbidden patterns) ---
Step "Flet API contract check" {
    $patterns = @(
        'ft\.border\.all\(', 'page\.go\(', 'page\.open\(', 'page\.show_dialog\(',
        'ft\.ElevatedButton\(', 'ft\.OutlinedButton\(', 'text="', 'name="',
        'prefix_text=', 'suffix_text=', 'ScrollMode\.DISABLED', 'ft\.colors\.', 'ft\.icons\.'
    )
    $targets = Get-ChildItem -Recurse -Include *.py -Path screens, components, main.py -ErrorAction SilentlyContinue
    $hits = @()
    foreach ($p in $patterns) {
        $hits += Select-String -Path $targets -Pattern $p -ErrorAction SilentlyContinue
    }
    if ($hits.Count -gt 0) {
        $hits | ForEach-Object { Write-Host "FORBIDDEN PATTERN: $($_.Path):$($_.LineNumber): $($_.Line.Trim())" }
        throw "$($hits.Count) forbidden Flet API pattern(s) found — see flet-api.instructions.md"
    }
}

# --- Step 5: Pytest suite (includes screen smoke tests) ---
Step "Pytest suite" {
    .\.venv\Scripts\pytest.exe tests/ -v --tb=short
    if ($LASTEXITCODE -ne 0) { throw "pytest failures" }
}

Write-Host "`n=================================" -ForegroundColor Cyan
if ($failed) {
    Write-Host "VERDICT: BLOCK - fix issues above before committing" -ForegroundColor Red
    exit 1
} else {
    Write-Host "VERDICT: READY TO COMMIT" -ForegroundColor Green
    exit 0
}
