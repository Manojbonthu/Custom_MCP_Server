#!/bin/bash
# Setup script for OpenBao policy and AppRole (All agents/tools)

set -e

echo "Creating read-only policy for ALL MCP tool and agent credentials..."
bao policy write mcp-agent-policy - <<EOF_POLICY
path "secret/data/mcp/*" {
  capabilities = ["read", "list"]
}
path "secret/metadata/mcp/*" {
  capabilities = ["read", "list"]
}
EOF_POLICY

echo "Enabling AppRole auth method (if not already enabled)..."
bao auth enable approle || true

echo "Creating AppRole for MCP with the broadly scoped policy..."
bao write auth/approle/role/mcp-agent \
    secret_id_ttl=0 \
    token_num_uses=0 \
    token_ttl=1h \
    token_max_ttl=24h \
    secret_id_num_uses=0 \
    policies="mcp-agent-policy"

# Check if .env has existing IDs
if [ -f .env ]; then
  EXISTING_ROLE_ID=$(grep "^OPENBAO_ROLE_ID=" .env | cut -d '=' -f2 | tr -d '\r' | tr -d '"' | tr -d "'")
  EXISTING_SECRET_ID=$(grep "^OPENBAO_SECRET_ID=" .env | cut -d '=' -f2 | tr -d '\r' | tr -d '"' | tr -d "'")
fi

if [ -n "$EXISTING_ROLE_ID" ] && [ -n "$EXISTING_SECRET_ID" ]; then
    echo "Reusing existing RoleID and SecretID from .env..."
    ROLE_ID=$EXISTING_ROLE_ID
    SECRET_ID=$EXISTING_SECRET_ID
    
    bao write auth/approle/role/mcp-agent/role-id role_id="$ROLE_ID"
    bao write auth/approle/role/mcp-agent/custom-secret-id secret_id="$SECRET_ID" > /dev/null
else
    echo "Fetching new RoleID and SecretID..."
    ROLE_ID=$(bao read -field=role_id auth/approle/role/mcp-agent/role-id)
    SECRET_ID=$(bao write -f -field=secret_id auth/approle/role/mcp-agent/secret-id)
fi

echo "================================================================"
echo "Setup Complete!"
echo "Credentials have been configured in OpenBao."
echo "================================================================"

# If we generated new IDs, let's output a snippet the user can use
if [ -z "$EXISTING_ROLE_ID" ] || [ -z "$EXISTING_SECRET_ID" ]; then
  cat << EOF > .env.local
CREDENTIAL_PROVIDER=openbao
OPENBAO_URL=http://localhost:8200
OPENBAO_ROLE_ID=$ROLE_ID
OPENBAO_SECRET_ID=$SECRET_ID
EOF
  echo "New credentials have been saved to .env.local."
  echo "Please move or merge these contents into your .env file."
  echo "Do not commit these files to version control."
fi
