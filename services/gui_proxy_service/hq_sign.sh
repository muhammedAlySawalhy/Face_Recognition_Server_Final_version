#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# HQ CSR signer (Intermediate CA) -> leaf cert + fullchain
# Usage:
#   ./hq_sign.sh -c server.csr -s san.cnf -o out \
#                -i intermediate.crt -k intermediate.key -r rootCA.crt \
#                [-d 825] [-n server]
#
# Produces:
#   out/server.crt        (leaf)
#   out/fullchain.crt     (leaf + intermediate)
#   out/chain.pem         (intermediate + root)  [for verification]
#   out/server.meta.txt   (quick info: subject/issuer/fingerprints)
# ------------------------------------------------------------

# Defaults (override via flags)
DAYS="825"
NAME="server"

# Parse args
CSR_IN=""
SAN_FILE=""
OUTDIR=""
INT_CRT=""
INT_KEY=""
ROOT_CRT=""

while getopts ":c:s:o:i:k:r:d:n:" opt; do
  case $opt in
    c) CSR_IN="$OPTARG" ;;
    s) SAN_FILE="$OPTARG" ;;
    o) OUTDIR="$OPTARG" ;;
    i) INT_CRT="$OPTARG" ;;
    k) INT_KEY="$OPTARG" ;;
    r) ROOT_CRT="$OPTARG" ;;
    d) DAYS="$OPTARG" ;;
    n) NAME="$OPTARG" ;;
    \?) echo "Invalid option: -$OPTARG" >&2; exit 2 ;;
    :)  echo "Option -$OPTARG requires an argument." >&2; exit 2 ;;
  esac
done

# Validate required args
[[ -z "${CSR_IN}"   ]] && { echo "Missing -c <csr file>"; exit 2; }
[[ -z "${SAN_FILE}" ]] && { echo "Missing -s <san.cnf>"; exit 2; }
[[ -z "${OUTDIR}"   ]] && { echo "Missing -o <outdir>"; exit 2; }
[[ -z "${INT_CRT}"  ]] && { echo "Missing -i <intermediate.crt>"; exit 2; }
[[ -z "${INT_KEY}"  ]] && { echo "Missing -k <intermediate.key>"; exit 2; }
[[ -z "${ROOT_CRT}" ]] && { echo "Missing -r <rootCA.crt>"; exit 2; }

# Friendly checks
for f in "$CSR_IN" "$SAN_FILE" "$INT_CRT" "$INT_KEY" "$ROOT_CRT"; do
  [[ -f "$f" ]] || { echo "File not found: $f"; exit 1; }
done

mkdir -p "$OUTDIR"

LEAF_CRT="$OUTDIR/${NAME}.crt"
FULLCHAIN="$OUTDIR/fullchain.crt"
CHAIN_PEM="$OUTDIR/chain.pem"
META="$OUTDIR/${NAME}.meta.txt"

# Build CA chain used for verification (intermediate + root)
cat "$INT_CRT" "$ROOT_CRT" > "$CHAIN_PEM"

echo "[+] Signing CSR:"
echo "    CSR:       $CSR_IN"
echo "    SAN file:  $SAN_FILE"
echo "    Issuer:    $INT_CRT (key: $INT_KEY)"
echo "    Validity:  $DAYS days"
echo "    Output:    $LEAF_CRT , $FULLCHAIN"

# Sign the CSR with the Intermediate CA
openssl x509 -req \
  -in  "$CSR_IN" \
  -CA  "$INT_CRT" \
  -CAkey "$INT_KEY" \
  -CAcreateserial \
  -out "$LEAF_CRT" \
  -days "$DAYS" \
  -sha256 \
  -extfile "$SAN_FILE"

# Build the full chain presented by servers (leaf + intermediate)
cat "$LEAF_CRT" "$INT_CRT" > "$FULLCHAIN"

# Verify leaf against the chain (intermediate+root)
echo "[*] Verifying signed certificate against chain..."
openssl verify -CAfile "$CHAIN_PEM" "$LEAF_CRT"

# Write handy metadata
{
  echo "=== SUBJECT ==="
  openssl x509 -noout -subject -in "$LEAF_CRT"
  echo
  echo "=== ISSUER ==="
  openssl x509 -noout -issuer  -in "$LEAF_CRT"
  echo
  echo "=== VALIDITY ==="
  openssl x509 -noout -dates   -in "$LEAF_CRT"
  echo
  echo "=== FINGERPRINTS ==="
  echo -n "SHA-256: "; openssl x509 -noout -fingerprint -sha256 -in "$LEAF_CRT" | sed 's/^.*=//'
  echo -n "SHA-1  : "; openssl x509 -noout -fingerprint -sha1   -in "$LEAF_CRT" | sed 's/^.*=//'
  echo
  echo "=== SANs (parsed) ==="
  openssl x509 -noout -text -in "$LEAF_CRT" | awk '/Subject Alternative Name/{flag=1;next}/X509v3/{flag=0}flag'
} > "$META"

echo "[+] Done."
echo "    Leaf cert     : $LEAF_CRT"
echo "    Full chain    : $FULLCHAIN   (leaf + intermediate)"
echo "    Verify chain  : $CHAIN_PEM   (intermediate + root)"
echo "    Info/meta     : $META"
