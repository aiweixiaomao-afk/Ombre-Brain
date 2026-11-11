# 裸机 + 主 Caddy（443）部署

这份说明对应在已有 Caddy 上把 Ombre Brain 接到标准 HTTPS，给 ChatGPT
自定义 MCP（OAuth）和其他远程 MCP 客户端使用。进程只监听回环地址，
TLS 由机器上原来的那一个 Caddy 终止。

不要再起第二个 Caddy，也不要把 MCP 放在 443 以外的端口。ChatGPT 添加
自定义连接器时要的是不带非标准端口的 `https://域名/mcp`。单独监听
`127.0.0.1:18443` 时，公网和 ChatGPT 都连不上，页面只会给一个笼统错误。

## 布局

| 用途 | 位置 |
| --- | --- |
| 代码、虚拟环境、记忆 | `/home/admin/ombre-brain`（`buckets/` 是记忆真源） |
| 配置 | `/home/admin/ombre-brain/config.yaml`（模式 600） |
| Dashboard 密码 | `/home/admin/ombre-brain/ob-private.env` 的 `OMBRE_DASHBOARD_PASSWORD` |
| systemd | `ombre-brain.service`（随本目录的单元文件） |
| 对外地址 | `https://ob.aiwei.asia`，MCP 为 `https://ob.aiwei.asia/mcp` |

`config.yaml` 里需要：

```yaml
transport: streamable-http
mcp_require_auth: true
mcp_auth_mode: oauth
deployment:
  public_url: https://ob.aiwei.asia
```

`public_url` 不要带 `:18443` 这类非默认端口，也不要带路径。OAuth 的
issuer、`/.well-known/oauth-authorization-server` 和
`/.well-known/oauth-protected-resource` 都按这个 origin 生成。
动态客户端注册在 `/oauth/register`。

压缩模型和向量的密钥继续放在服务器上的 `config.yaml`（或
`OMBRE_COMPRESS_API_KEY` / `OMBRE_EMBED_API_KEY`）。不要写进 git。
改完密钥或 `public_url` 后只重启本服务：

```bash
systemctl restart ombre-brain
```

## Caddy

先备份 `/etc/caddy/Caddyfile`，把 `Caddyfile.snippet` 整段追加到末尾，
不要改动其他站点。然后：

```bash
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
```

应用侧 `OMBRE_TRUSTED_PROXY_CIDRS=127.0.0.1/32`，因为主 Caddy 从本机
回环连到 `127.0.0.1:18001`。不要填 `0.0.0.0/0`。

## 验收

未带 Bearer 的 `POST https://ob.aiwei.asia/mcp` 应返回 401，并且
`WWW-Authenticate` 含
`resource_metadata="https://ob.aiwei.asia/.well-known/oauth-protected-resource/mcp"`。
授权服务器元数据的 `issuer` 应为 `https://ob.aiwei.asia`。
Dashboard 在 `https://ob.aiwei.asia`，登录和 OAuth 授权页使用同一个密码。
