# 时光日记

> 安全、私密的个人日记网站，专为树莓派局域网部署优化

## 功能

- **日历视图** - 月历展示日记，点击日期查看当天内容
- **列表视图** - 传统日记列表，支持分页
- **日期选择** - 可自由指定日记日期，支持补写
- **自动保存** - 编辑时 2 秒无操作自动存入，防丢失
- **全文搜索** - 解密后搜索标题和内容
- **移动适配** - 底部导航栏、触控优化、安全区适配

## 安全

| 层面 | 措施 |
|------|------|
| 密码 | PBKDF2+SHA256 哈希，不可逆 |
| 登录 | 5 次失败锁定 10 分钟 |
| 会话 | HTTP-Only Cookie，SameSite，8 小时过期 |
| 数据 | AES-256-GCM 加密存储（标题+内容） |
| 传输 | CSRF 保护，X-Frame-Options，HTTPS 就绪 |
| 密钥 | 持久化存储，进程重启不丢失 |
| 数据库 | SQLite WAL 模式，自动备份 |

## 部署（树莓派）

```bash
# 1. 复制项目到树莓派
scp -r rijiweb pi@树莓派IP:/home/pi/

# 2. 运行部署脚本
ssh pi@树莓派IP
cd /home/pi/rijiweb
bash deploy/setup.sh

# 3. 局域网访问
# http://树莓派IP
```

默认账号：`admin` / `admin123`，请登录后立即修改密码。

### 手动部署

```bash
# 安装依赖
pip install -r requirements.txt

# 配置密钥（首次自动生成到 data/ 目录）

# 开发运行
python app.py

# 生产运行
gunicorn --config gunicorn_config.py wsgi:app
```

## 管理

```bash
# 查看服务状态
sudo systemctl status rijiweb

# 查看日志
sudo journalctl -u rijiweb -f

# 数据库备份（自动，保留在 backups/）
ls -lh backups/

# 重启服务
sudo systemctl restart rijiweb
```

## 项目结构

```
rijiweb/
├── app.py              # 应用入口
├── config.py           # 配置（密钥持久化）
├── wsgi.py             # Gunicorn 入口
├── gunicorn_config.py  # 生产服务器配置
├── models/database.py  # 数据模型 + SQLite 初始化
├── routes/
│   ├── auth.py         # 认证（登录/注册/改密）
│   └── diary.py        # 日记 CRUD + 自动保存 + 日历
├── utils/
│   ├── encryption.py   # AES-256-GCM 加解密
│   └── backup.py       # 自动备份
├── templates/          # Jinja2 模板
├── static/             # CSS / JS
├── deploy/
│   ├── setup.sh        # 一键部署脚本
│   ├── rijiweb.service # systemd 服务
│   └── nginx-riji.conf # Nginx 反向代理
├── data/               # 数据库 + 密钥（自动生成）
└── backups/            # 备份目录
```

## 技术栈

- Python 3 / Flask
- SQLite + SQLAlchemy ORM
- AES-256-GCM（cryptography）
- Gunicorn + Nginx + systemd
- 无 Docker 依赖
