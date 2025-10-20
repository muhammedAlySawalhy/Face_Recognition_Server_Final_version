#!/usr/bin/env bash
set -euo pipefail

# =========================
# Config
# =========================
ORG="${ORG:-Mirando}"
CN_ROOT="${CN_ROOT:-$ORG Root CA}"
CN_INT="${CN_INT:-$ORG Issuing CA}"

ROOT_BITS="${ROOT_BITS:-4096}"
INT_BITS="${INT_BITS:-4096}"

ROOT_DAYS="${ROOT_DAYS:-3650}"   # ~10 years
INT_DAYS="${INT_DAYS:-1825}"     # ~5 years

OUTDIR="${OUTDIR:-./ca}"         # where to store generated files
mkdir -p "$OUTDIR"

ROOT_KEY="$OUTDIR/rootCA.key"
ROOT_CRT="$OUTDIR/rootCA.crt"

INT_KEY="$OUTDIR/intermediate.key"
INT_CSR="$OUTDIR/intermediate.csr"
INT_CRT="$OUTDIR/intermediate.crt"

CHAIN_CRT="$OUTDIR/ca-chain.crt"

# =========================
# 1) Root CA
# =========================
echo "[+] Generating Root CA private key ($ROOT_BITS bits)"
openssl genrsa -out "$ROOT_KEY" "$ROOT_BITS"
chmod 600 "$ROOT_KEY"

echo "[+] Self-signing Root CA certificate ($ROOT_DAYS days)"
openssl req -x509 -new -key "$ROOT_KEY" -sha256 -days "$ROOT_DAYS" \
  -subj "/C=EG/O=$ORG/CN=$CN_ROOT" \
  -out "$ROOT_CRT"

# =========================
# 2) Intermediate CA
# =========================
echo "[+] Generating Intermediate CA private key ($INT_BITS bits)"
openssl genrsa -out "$INT_KEY" "$INT_BITS"
chmod 600 "$INT_KEY"

echo "[+] Creating Intermediate CA CSR"
openssl req -new -key "$INT_KEY" \
  -subj "/C=EG/O=$ORG/CN=$CN_INT" \
  -out "$INT_CSR"

# Extensions for Intermediate CA
cat > "$OUTDIR/ca_ext.cnf" <<'EOF'
basicConstraints = critical,CA:true,pathlen:0
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
EOF

echo "[+] Signing Intermediate CA certificate ($INT_DAYS days) with Root CA"
openssl x509 -req -in "$INT_CSR" \
  -CA "$ROOT_CRT" -CAkey "$ROOT_KEY" -CAcreateserial \
  -out "$INT_CRT" -days "$INT_DAYS" -sha256 \
  -extfile "$OUTDIR/ca_ext.cnf"

# =========================
# 3) Build chain file
# =========================
cat "$INT_CRT" "$ROOT_CRT" > "$CHAIN_CRT"

# =========================
# 4) Summary
# =========================
echo
echo "[+] Done. Files generated in: $OUTDIR"
ls -l "$OUTDIR"

echo
echo "IMPORTANT:"
echo "  - Keep $ROOT_KEY **offline & secure**"
echo "  - You will use:"
echo "       Intermediate CA cert : $INT_CRT"
echo "       Intermediate CA key  : $INT_KEY"
echo "       Root CA cert         : $ROOT_CRT"
echo "  - Use $CHAIN_CRT (intermediate + root) for verification only"
