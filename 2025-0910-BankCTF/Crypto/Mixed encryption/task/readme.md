交互信息
nc ip 端口后

GET /pub 响应 {"n":"...","e1":...,"e2":...,"token":"..."}
GET /challenge <token（get /pub获取到的token）> 响应 {"cipher1":"b64...","cipher2a":"b64...","cipher2b":"b64..."}
POST /answer {"token":"...","secret":"..."} 响应 {"ok":true,"flag":"flag{...}"} 或错误

限制说明：
- 每次连接最多执行 CHAL_MAX_CMDS 条命令，超过将断开。
- token 为一次性：/challenge 仅允许使用一次；/answer 仅允许尝试一次。
- nonce = HMAC_SHA256(key, token)[:12]

题面示例如下
nc xx.xxx.xxx.xx 5xxx
Welcome to Mixed-Protocol Trap (Harder)!
Workflow:
1) GET /pub returns RSA modulus n and two exponents e1,e2 plus a one-time token T.
2) GET /challenge <T> .
3) POST /answer with token T and secret S (len:16)(single attempt).
Limits: max 6 commands per connection.
> GET /pub
{"n": "139335977482131574969028391932159210806836326903960716131701451781525804394267272601517818220590276762854390824201618781841488554927386574746572538397056825495831283057299091872410841436505458728292258520264012608746028602383342825373927257129402068577333059660883333544138535478830691506463626739099508248259", "e1": 65537, "e2": 17, "token": "OWpJzmQqOrl2hJsy"}
> GET /challenge OWpJzmQqOrl2hJsy
{"cipher1": "BCYikbjAyznAmiY7Uo+t2A==", "cipher2a": "Pxd/cNe3WoRX6s+YnurriHqU1D5maAQHqLRxu6TZzTWkMCFtn6FcdrALwdRLYFg1D5BqkJhWU2I0Wa83L7KNEarJPtuch7IwVEksBkTV2629xfssmf+AGKxCx/n7Sm9RtXtiu7m8JZop/x2g3dJs7UAwCXKDirEBR1+ODH1zp38=", "cipher2b": "cJc6rL5WD4seztzN/R8OiF6F5Ye3rb5TjEHIEgBQPskVGvRbelLoj+aP03b8/W382cR4i8y8UUPRMJ2yWkMB/lfxvyH5JbnBPdoeinFaGIA2hKW+yJACsOIKsn4ay06fv6IjCjXzKmkaewkS/lmRmjchtRBTcPyAIIHrP+3JX/A="}
>POST /answer {"token":"BQL0XIrcLsVJjXi-","secret":"gZaqucIxXbtVw-0e"} 
{"ok":true,"flag":"flag{...}"}
