服务端交互：
- 获取新题：`GET /api/new` → 返回 token、instances、aux、verify_hex、params
- 复取题面：`GET /api/challenge/{token}`
- 提交答案：`POST /api/submit/{token}`
  - 请求体支持两种格式：
    - `{ "sig_hex": "0x" + (r||s||v 的 65 字节 hex) }`
    - `{ "r": "0x...", "s": "0x...", "v": 0|1|27|28 }`
  - 返回：`{ "ok": true, "flag": "flag{...}" }`

数据说明：
- params 全局参数
- instances：若干条样本，每条包含
  - r, s：签名参数（hex）
  - msg_hex：原始消息（hex；非哈希）
  - type：样本类型之一：lin / lsb / msb / mix（不同类型携带的“部分信息”不同）
  - meta：随类型携带的字段（例如某些低/高位窗口或线性相关参数）

- aux：辅助信息对象
  - trunc_bits：整型，比特截断宽度
  - proofs：数组，元素包含 `{ msg_hex, keccak_trunc }`，用于辅助恢复 salt
- verify_hex：需要你最终用恢复出的私钥签名的消息（hex；非哈希）

重要细节：
- 曲线固定为 secp256k1，阶 n 固定；
- 样本中 z 的计算并非直接 Keccak(msg)，而是 `z = Keccak256(msg || salt) mod n`，其中 salt 为未知的 1 字节；你可用 aux 中提供的截断提示（`Keccak256(salt || msg)` 的低若干比特）暴力恢复 salt；
- 提交验签时采用以太坊风格：`h = Keccak256(verify_hex)`，签名格式为 65 字节的 `r||s||v`，`v` 取 0/1（或 27/28）；
- 一个 token 对应一套独立数据；无需也不应访问真实区块链。

样例（缩略）：
```
POST /api/submit/{token} body:

{
  "r": "0xa3abc69bd1a942740f917b2871ba756072a2af58bf90958ab92dc6b70d69680e",
  "s": "0x52cbfe586367a15877394a67424bd96c700906f9f84878a341d30004f9254d8c",
  "v": 0
}
响应 
→ { "ok": true, "flag": "flag{...}" }
```

规则与提示：
- 必要信息均已包含在返回的 JSON 中；不需要外部 API 或链上交互；
- 可以使用任意数学/编程工具（格算法非必需，但可能有帮助）；
- 不要尝试暴力枚举私钥或攻击服务本身；
- 你只需恢复出能够对 `verify_hex` 正确签名的对应私钥即可。
