Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "🚀 Creating Database Tables" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "❌ Virtual environment not activated!" -ForegroundColor Red
    Write-Host "Activate it with: .\gym\Scripts\activate" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Run the Python script
python scripts/create_tables_simple.py

Write-Host ""
Read-Host "Press Enter to exit"