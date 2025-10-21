#!/usr/bin/env sh
set -eu

# =========================
# Config via ENV (with sane defaults)
# =========================
# Cert/CSR locations
OUTDIR="${OUTDIR:-/etc/nginx/certs}"
KEY_FILE="${KEY_FILE:-$OUTDIR/server.key}"            # private key (generated here)
CSR_FILE="${CSR_FILE:-$OUTDIR/server.csr}"            # CSR (generated here)
CRT_FILE="${CRT_FILE:-$OUTDIR/server.crt}"            # optional leaf (for reference)
FULLCHAIN_FILE="${FULLCHAIN_FILE:-$OUTDIR/fullchain.crt}"  # REQUIRED: leaf + intermediate(s)
SAN_HINT="${SAN_HINT:-$OUTDIR/san.hq-template.cnf}"

# CSR details (leaf only)
SRV_CN="${SRV_CN:-gui.internal}"                      # label; browsers match SANs, not CN
SAN_DNS="${SAN_DNS:-gui.internal}"                    # comma-separated DNS entries
SAN_IP="${SAN_IP:-}"                                  # comma-separated IP entries (optional)
LEAF_BITS="${LEAF_BITS:-2048}"

# Nginx template variables
LISTEN_PORT="${LISTEN_PORT:-4000}"                    # e.g., 443 or 4000
SERVER_NAME="${SERVER_NAME:-localhost}"               # what clients use to connect
APP_HOST="${APP_HOST:-127.0.0.1}"                     # upstream host
APP_PORT="${APP_PORT:-3000}"                          # upstream port
CLIENT_MAX_BODY_SIZE="${CLIENT_MAX_BODY_SIZE:-50m}"
PROXY_READ_TIMEOUT="${PROXY_READ_TIMEOUT:-300s}"
PROXY_SEND_TIMEOUT="${PROXY_SEND_TIMEOUT:-300s}"

# Template paths
TEMPLATE="${TEMPLATE:-/etc/nginx/templates/site.conf.template}"
TARGET_CONF="${TARGET_CONF:-/etc/nginx/conf.d/site.conf}"

# Nginx launch command
NGINX_CMD="${NGINX_CMD:-nginx -g 'daemon off;'}"

# By default, point Nginx to the files we are managing here
export CERT_FILE="${CERT_FILE:-$FULLCHAIN_FILE}"
export KEY_FILE="${KEY_FILE:-$KEY_FILE}"  # already set

# =========================
# Helper: build SAN file content for HQ
# =========================
write_san_template() {
  echo "subjectAltName = @alt_names" > "$SAN_HINT"
  echo "[alt_names]" >> "$SAN_HINT"
  i=1
  OLDIFS="$IFS"; IFS=,
  for d in $SAN_DNS; do
    d=$(echo "$d" | xargs); [ -n "$d" ] && echo "DNS.$i = $d" >> "$SAN_HINT" && i=$((i+1))
  done
  j=1
  for ip in $SAN_IP; do
    ip=$(echo "$ip" | xargs); [ -n "$ip" ] && echo "IP.$j  = $ip" >> "$SAN_HINT" && j=$((j+1))
  done
  IFS="$OLDIFS"
}

# =========================
# 1) Ensure dirs
# =========================
mkdir -p "$OUTDIR" "$(dirname "$TARGET_CONF")"
chmod 700 "$OUTDIR"

echo "[+] OUTDIR=$OUTDIR"
echo "[+] SRV_CN=$SRV_CN"
echo "[+] SAN_DNS=$SAN_DNS"
echo "[+] SAN_IP=$SAN_IP"
echo "[+] Expecting FULLCHAIN at: $FULLCHAIN_FILE"

# =========================
# 2) Generate leaf private key (once)
# =========================
if [ ! -f "$KEY_FILE" ]; then
  echo "[+] Generating leaf private key ($LEAF_BITS bits) -> $KEY_FILE"
  openssl genrsa -out "$KEY_FILE" "$LEAF_BITS"
  chmod 600 "$KEY_FILE"
else
  echo "[=] Found existing key -> $KEY_FILE"
fi

# =========================
# 3) If fullchain is already present, render & start
# =========================
if [ -f "$FULLCHAIN_FILE" ]; then
  echo "[=] Found $FULLCHAIN_FILE — rendering Nginx config and starting..."
  envsubst '$LISTEN_PORT $SERVER_NAME $APP_HOST $APP_PORT $CLIENT_MAX_BODY_SIZE $PROXY_READ_TIMEOUT $PROXY_SEND_TIMEOUT' < "$TEMPLATE" > "$TARGET_CONF"
  nginx -t
  exec sh -lc "$NGINX_CMD"
fi

# =========================
# 4) Create CSR if missing (leaf only)
# =========================
if [ ! -f "$CSR_FILE" ]; then
  echo "[+] Creating CSR -> $CSR_FILE"
  openssl req -new -key "$KEY_FILE" -subj "/CN=$SRV_CN" -out "$CSR_FILE"
else
  echo "[=] Found existing CSR -> $CSR_FILE"
fi

# =========================
# 5) Write SAN template for HQ signing
# =========================
echo "[+] Writing SAN template for HQ -> $SAN_HINT"
write_san_template

cat <<EOF

========================= NEXT STEPS (HQ SIGNING) =========================
1) Copy CSR to HQ (secure CA machine):
     $CSR_FILE

2) On HQ, sign CSR with your Intermediate CA using a SAN file (like the one
   we created at: $SAN_HINT). Example HQ commands:

   # Adjust paths to your CA files and SAN file:
   openssl x509 -req -in server.csr \
     -CA intermediate.crt -CAkey intermediate.key -CAcreateserial \
     -out server.crt -days 825 -sha256 -extfile san.cnf

   # Build the chain presented to clients (leaf + intermediate):
   cat server.crt intermediate.crt > fullchain.crt

3) Copy fullchain back here as:
     $FULLCHAIN_FILE
   (Optionally also copy the leaf as: $CRT_FILE)

4) Once $FULLCHAIN_FILE appears, Nginx will start automatically.
==========================================================================
EOF

# =========================
# 6) Wait for fullchain; verify key↔cert; render; start Nginx
# =========================
echo "[*] Waiting for $FULLCHAIN_FILE ..."
while [ ! -f "$FULLCHAIN_FILE" ]; do
  sleep 2
done

# Verify the first cert in the chain matches our key (modulus check)
echo "[*] Verifying certificate matches key..."
TMPLEAF="$(mktemp)"
awk 'BEGIN{p=0} /BEGIN CERTIFICATE/{if(++p==1) print; next} /END CERTIFICATE/{if(p==1){print; exit}} p==1{print}' "$FULLCHAIN_FILE" > "$TMPLEAF"
KEYMOD="$(openssl rsa -noout -modulus -in "$KEY_FILE" | openssl md5)"
CRTMOD="$(openssl x509 -noout -modulus -in "$TMPLEAF" | openssl md5)"
rm -f "$TMPLEAF"
if [ "$KEYMOD" = "$CRTMOD" ]; then
  echo "[+] Key and certificate match."
else
  echo "[!] WARNING: key and certificate DO NOT match. Did you sign the right CSR?"
fi

echo "[+] Rendering Nginx config -> $TARGET_CONF"
envsubst '$LISTEN_PORT $SERVER_NAME $APP_HOST $APP_PORT $CLIENT_MAX_BODY_SIZE $PROXY_READ_TIMEOUT $PROXY_SEND_TIMEOUT' < "$TEMPLATE" > "$TARGET_CONF"
nginx -t
echo "[+] Starting Nginx..."
exec sh -lc "$NGINX_CMD"
# =========================
# End of entrypoint script
# =========================