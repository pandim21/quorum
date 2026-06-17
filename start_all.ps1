# Launch every Quorum committee member, each in its own terminal window.
# Run from the quorum/ folder:  .\start_all.ps1
# Stop an agent: close its window (or Ctrl+C inside it).

$roles = @(
    "portfolio_manager",
    "research_analyst",
    "bull_analyst",
    "bear_analyst",
    "risk_officer",
    "chief_risk_officer",
    "export_controls_analyst",
    "valuation_specialist",
    "forensic_accounting_analyst",
    "independent_auditor"
)

foreach ($role in $roles) {
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "`$host.UI.RawUI.WindowTitle = 'Quorum - $role'; uv run python committee.py $role"
    ) -WorkingDirectory $PSScriptRoot
    Start-Sleep -Milliseconds 600
}

Write-Host "Launched $($roles.Count) committee members. Watch each window for 'Agent started'."
