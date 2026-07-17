# ⚙️ Configuration Files

**PSE Vision CM4 - System Configuration**

---

## 📋 สารบัญ (Table of Contents)

1. [ภาพรวม (Overview)](#-ภาพรวม-overview)
2. [Configuration Files](#-configuration-files)
3. [Database Configuration](#-database-configuration)
4. [ตัวอย่าง Config](#-ตัวอย่าง-config)

---

## 📖 ภาพรวม (Overview)

โฟลเดอร์ `config/` เก็บไฟล์ตั้งค่าต่างๆ สำหรับระบบ PSE Vision CM4:

- 🗄️ **Database Configuration** - ตั้งค่าฐานข้อมูล (PostgreSQL/SQLite)
- 📊 **Schema Files** - SQL scripts สำหรับสร้างตาราง
- 🔧 **System Settings** - ค่าตั้งต้นระบบ

---

## 📂 Configuration Files

```
config/
│
├── database/                      # 🗄️ Database Configuration
│   ├── db_config.json             # Database connection settings
│   ├── create_machines_table.sql  # SQL: Create machines table
│   └── README.md                  # Database documentation
│
└── README.md                      # This file
```

---

## 🗄️ Database Configuration

### `database/db_config.json`

**Purpose:** Database connection settings

```json
{
  "type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "pse_vision",
  "username": "pse_user",
  "password": "your_password_here",
  "pool_size": 10,
  "echo": false
}
```

### `database/create_machines_table.sql`

**Purpose:** SQL script to create machines table

```sql
CREATE TABLE IF NOT EXISTS machines (
    id SERIAL PRIMARY KEY,
    machine_id VARCHAR(50) UNIQUE NOT NULL,
    machine_name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    ip_address VARCHAR(15),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Run script:**
```bash
# PostgreSQL
psql -U pse_user -d pse_vision -f config/database/create_machines_table.sql

# Or from Python
python python_scripts/database/init_db.py
```

---

## 🔧 ตัวอย่าง Config

### Development (SQLite)

```json
{
  "type": "sqlite",
  "database": "system_config.db",
  "echo": true
}
```

**Advantages:**
- ✅ No setup required
- ✅ File-based (portable)
- ✅ Good for development/testing

**Disadvantages:**
- ❌ Limited concurrency
- ❌ No network access

---

### Production (PostgreSQL)

```json
{
  "type": "postgresql",
  "host": "10.2.100.10",
  "port": 5432,
  "database": "pse_vision_prod",
  "username": "pse_prod",
  "password": "strong_password_here",
  "pool_size": 20,
  "echo": false
}
```

**Advantages:**
- ✅ High concurrency
- ✅ Network access
- ✅ Advanced features (replication, etc.)

**Disadvantages:**
- ❌ Requires PostgreSQL server
- ❌ More setup required

---

## 📝 การตั้งค่า Database

### 1. Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Create Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE pse_vision;
CREATE USER pse_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE pse_vision TO pse_user;
\q
```

### 3. Update Config

Edit `config/database/db_config.json`:
```json
{
  "type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "pse_vision",
  "username": "pse_user",
  "password": "your_password"
}
```

### 4. Initialize Tables

```bash
# Run SQL scripts
psql -U pse_user -d pse_vision -f config/database/create_machines_table.sql

# Or use Python
python python_scripts/database/init_db.py
```

---

## 🔒 Security Best Practices

### 1. Protect Credentials

**❌ Don't:**
- Commit `db_config.json` with real passwords to Git
- Use default passwords in production

**✅ Do:**
```bash
# Copy example config
cp config/database/db_config.example.json config/database/db_config.json

# Add to .gitignore
echo "config/database/db_config.json" >> .gitignore

# Set strong password
# Use environment variables for sensitive data
```

### 2. Environment Variables

```bash
# Set environment variables
export DB_HOST=localhost
export DB_USER=pse_user
export DB_PASSWORD=your_password

# Use in Python
import os
db_host = os.getenv('DB_HOST', 'localhost')
db_password = os.getenv('DB_PASSWORD')
```

### 3. File Permissions

```bash
# Restrict access to config files
chmod 600 config/database/db_config.json
```

---

## 🐛 Troubleshooting

### Cannot Connect to Database

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection
psql -U pse_user -d pse_vision -h localhost

# Check firewall
sudo ufw allow 5432/tcp
```

### Permission Denied

```bash
# Grant privileges
sudo -u postgres psql
GRANT ALL PRIVILEGES ON DATABASE pse_vision TO pse_user;
```

### Port Already in Use

```bash
# Check what's using port 5432
sudo lsof -i :5432

# Change port in postgresql.conf
sudo nano /etc/postgresql/*/main/postgresql.conf
# Change: port = 5433

# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

## 📞 Support

- **Documentation:** [../docs/README.md](../docs/README.md)
- **Backend:** [../python_scripts/README.md](../python_scripts/README.md)
- **Issues:** https://github.com/pse/pse-vision-cm4/issues

---

**Made with ❤️ by PSE Vision Team**
