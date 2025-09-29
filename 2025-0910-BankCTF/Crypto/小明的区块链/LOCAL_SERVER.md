# 本地验签服务说明（local_server.py）

本地服务用于在没有远程环境的情况下，基于题目附件 `task/challenge_data.json` 离线复现接口与验签逻辑，验证我们恢复出的私钥与签名是否正确。

## 依赖

- Python 3.11+
- `pycryptodome`（用于 Keccak）

## 启动

```
python [BankCTF-2024-09-10]小明的区块链/solution/local_server.py \
  --host 127.0.0.1 \
  --port 59999 \
  --chal "[BankCTF-2024-09-10]小明的区块链/task/challenge_data.json" \
  --result "[BankCTF-2024-09-10]小明的区块链/solution/result.json" \
  --flag-prefix local-
```

或使用环境变量：

- `LOCAL_SERVER_HOST`（默认 `127.0.0.1`）
- `LOCAL_SERVER_PORT`（默认 `59999`）
- `LOCAL_CHAL_JSON`（默认 `../task/challenge_data.json`）
- `LOCAL_RESULT_JSON`（默认 `result.json`）
- `LOCAL_FLAG_PREFIX`（默认 `local-`）
- `LOCAL_FLAG`（若设置则固定返回此 flag 字符串，覆盖前缀模式）
- `LOCAL_CHAL_PRIV`（当找不到 `result.json` 时，用它提供私钥 0x.. 来派生公钥）

## 接口

- `GET /api/new`：返回题目 JSON（附件内容）
- `GET /api/challenge/{token}`：同上
- `POST /api/submit/{token}`：提交签名
  - 请求体：
    - `{"sig_hex":"0x" + r||s||v}`（65 字节 hex），或
    - `{ "r":"0x..", "s":"0x..", "v":0|1|27|28 }`
  - 验证：以太坊风格，`h=Keccak256(verify_hex)`，low‑s
  - 响应：`{"ok":true, "flag":"flag{<prefix><token前8位>}"}` 或（若 `LOCAL_FLAG` 设置）固定返回该 flag

## 示例

查看题面：
```
curl -s http://127.0.0.1:59999/api/new | jq '.token,.verify_hex'
```

提交已求得签名：
```
TOKEN=$(jq -r .token [BankCTF-2024-09-10]小明的区块链/task/challenge_data.json)
SIG=$(jq -r '.signature.sig_hex' [BankCTF-2024-09-10]小明的区块链/solution/result.json)
curl -s -X POST \
  -H 'Content-Type: application/json' \
  -d "{\"sig_hex\":\"$SIG\"}" \
  "http://127.0.0.1:59999/api/submit/$TOKEN"
```

预期：`{"ok":true, "flag":"flag{local-<token前8位>}"}`。

## 验签简述

- 使用 secp256k1；`r` 来自 `kG` 的 x 坐标模 n；
- 以太坊风格哈希：`h=Keccak256(verify_hex)`；
- 验签计算 `w=s^{-1}`，`u1=h·w`，`u2=r·w`，检查 `(u1·G + u2·Q).x ≡ r (mod n)`。
