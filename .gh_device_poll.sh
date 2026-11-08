#!/bin/bash
# 轮询 GitHub 设备码授权，成功后把 token 写入临时文件
CID=178c6fc778ccc68e1d6a
DEVICE_CODE="$1"
OUT="$2"
DEADLINE=$(( $(date +%s) + 880 ))

while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  RESP=$(curl -sS --max-time 20 -X POST https://github.com/login/oauth/access_token \
    -H "Accept: application/json" \
    -d "client_id=$CID&device_code=$DEVICE_CODE&grant_type=urn:ietf:params:oauth:grant-type:device_code" 2>/dev/null)
  case "$RESP" in
    *access_token*)
      echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" > "$OUT"
      chmod 600 "$OUT"
      echo "AUTH_OK"
      exit 0;;
    *authorization_pending*)
      sleep 5;;
    *slow_down*)
      sleep 8;;
    *expired_token*)
      echo "EXPIRED"; exit 2;;
    *access_denied*)
      echo "DENIED"; exit 3;;
    *)
      echo "RESP: $RESP"; sleep 6;;
  esac
done
echo "TIMEOUT"; exit 4
