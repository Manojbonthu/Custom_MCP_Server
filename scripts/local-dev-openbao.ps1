$ErrorActionPreference = 'Stop'
$env:BAO_TOKEN="s.mf3UopevSqMmip4N9lHHXHap"
$env:BAO_ADDR="http://127.0.0.1:8200"

Write-Host "1. Writing Policy for all agents/tools..."
$policy = @"
path `"secret/data/mcp/*`" {
  capabilities = [`"read`", `"list`"]
}
path `"secret/metadata/mcp/*`" {
  capabilities = [`"read`", `"list`"]
}
"@
$policy | bao policy write mcp-agent-policy -

Write-Host "2. Enabling auth approle..."
try { bao auth enable approle } catch { Write-Host "AppRole already enabled or failed" }

Write-Host "3. Creating role..."
bao write auth/approle/role/mcp-agent secret_id_ttl=0 token_num_uses=0 token_ttl=1h token_max_ttl=24h secret_id_num_uses=0 policies="mcp-agent-policy"

Write-Host "4. Extracting IDs..."
$role_id = (bao read -field=role_id auth/approle/role/mcp-agent/role-id)
$secret_id = (bao write -f -field=secret_id auth/approle/role/mcp-agent/secret-id)

Write-Host "`n=== COPY THESE TO YOUR .env ==="
Write-Host "OPENBAO_ROLE_ID=$role_id"
Write-Host "OPENBAO_SECRET_ID=$secret_id"
Write-Host "==============================="
