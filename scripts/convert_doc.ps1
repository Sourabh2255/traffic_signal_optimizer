$docxPath = (Resolve-Path "AI_Based_Adaptive_Traffic_Signal_Time_Optimization_System.docx").Path
$pdfPath = [System.IO.Path]::ChangeExtension($docxPath, ".pdf")

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $doc = $word.Documents.Open($docxPath)
    $pageCount = $doc.ComputeStatistics(2) # 2 = wdStatisticPages
    Write-Host "Page count: $pageCount"
    # wdFormatPDF = 17
    $doc.SaveAs([ref]$pdfPath, [ref]17)
    $doc.Close([ref]0)
    $word.Quit()
    Write-Host "PDF successfully generated at: $pdfPath"
} catch {
    Write-Host "Error converting to PDF: $_"
}
