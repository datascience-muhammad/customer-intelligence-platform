param(
    [string]$Registry = "",
    [string]$ImageName = "shopflow/dbt",
    [string]$Tag = "latest"
)

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker CLI not found. Please install Docker Desktop and ensure the daemon is running."
    exit 1
}

$fullTag = if ($Registry -ne "") { "$Registry/$ImageName:$Tag" } else { "$ImageName:$Tag" }

Write-Host "Building dbt image: $fullTag"
docker build -f .\docker\Dockerfile.dbt -t $fullTag .

if ($LASTEXITCODE -ne 0) { Write-Error "Docker build failed"; exit $LASTEXITCODE }

if ($Registry -ne "") {
    Write-Host "Pushing image to registry: $Registry"
    docker push $fullTag
    if ($LASTEXITCODE -ne 0) { Write-Error "Docker push failed"; exit $LASTEXITCODE }
}

Write-Host "Built image: $fullTag"
Write-Host "Tip: if you built locally without pushing, use this tag in the DockerOperator: $fullTag"
