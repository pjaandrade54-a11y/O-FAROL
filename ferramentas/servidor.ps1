param([string]$Raiz, [int]$Porta = 8080)
# Minimal static file server for previewing the site
$tipos = @{ '.html'='text/html; charset=utf-8'; '.css'='text/css; charset=utf-8'; '.js'='text/javascript; charset=utf-8'; '.svg'='image/svg+xml'; '.jpg'='image/jpeg'; '.png'='image/png'; '.pdf'='application/pdf' }
$l = New-Object Net.HttpListener
$l.Prefixes.Add("http://localhost:$Porta/")
$l.Start()
Write-Host "Servindo $Raiz em http://localhost:$Porta/"
while ($l.IsListening) {
  $c = $l.GetContext()
  $rel = [Uri]::UnescapeDataString($c.Request.Url.AbsolutePath.TrimStart('/'))
  if ($rel -eq '') { $rel = 'index.html' }
  $arq = [IO.Path]::GetFullPath((Join-Path $Raiz $rel))
  if ($arq.StartsWith([IO.Path]::GetFullPath($Raiz)) -and (Test-Path $arq -PathType Leaf)) {
    $b = [IO.File]::ReadAllBytes($arq)
    $t = $tipos[[IO.Path]::GetExtension($arq).ToLower()]
    if ($t) { $c.Response.ContentType = $t }
    $c.Response.OutputStream.Write($b, 0, $b.Length)
  } else { $c.Response.StatusCode = 404 }
  $c.Response.Close()
}
