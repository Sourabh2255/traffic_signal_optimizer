$docxPath = (Resolve-Path "AI_Based_Adaptive_Traffic_Signal_Time_Optimization_System.docx").Path
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open($docxPath)
    $pages = $doc.ComputeStatistics(2)
    Write-Host "Calculated Pages: $pages"
    $doc.Close([ref]0)
} finally {
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    Stop-Process -Name WINWORD -Force -ErrorAction SilentlyContinue
}
