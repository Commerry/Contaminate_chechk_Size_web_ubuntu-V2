# Database Configuration

This file stores SQL Server database connection and session settings.

## Quick Start

1. **Enable Database:**
   - Open Settings (⚙️) in the application
   - Scroll to "SQL Server Database" section
   - Check "Enable Database Storage"

2. **Configure Connection:**
   ```json
   {
     "enabled": true,
     "host": "10.0.191.15",
     "username": "testchecksize",
     "password": "passw0rd123",
     "database": "OT-test",
     "table": "tbl_testchecksize",
     "port": 1433
   }
   ```

3. **Set Measurement Triggers:**
   - `measurement_triggers`: Number of measurements per session (default: 10)
   - `unlimited_mode`: Set to `true` for unlimited measurements

4. **Test Connection:**
   - Click "Test Connection" button in settings

## Configuration Options

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `enabled` | boolean | Enable/disable database | `false` |
| `host` | string | SQL Server host/IP | `""` |
| `username` | string | Database username | `""` |
| `password` | string | Database password | `""` |
| `database` | string | Database name | `""` |
| `table` | string | Table name | `"tbl_testchecksize"` |
| `port` | number | SQL Server port | `1433` |
| `measurement_triggers` | number | Measurements per session | `10` |
| `unlimited_mode` | boolean | Allow unlimited measurements | `false` |
| `auto_save` | boolean | Auto-save when complete | `false` |
| `lot` | string | Default LOT number | `""` |
| `product_type` | string | Default product type | `""` |

## How It Works

1. **Session Start:** 
   - User starts a session with object name and parameters
   - Session locks to specific object name

2. **Measurement Collection:**
   - System measures N times (e.g., 10 times)
   - Each measurement is stored in memory
   - Object name must match session name

3. **Maximum Selection:**
   - When session completes, system finds MAXIMUM value
   - Only the maximum is saved to database
   - Reduces data by 90% (10 measurements → 1 record)

4. **Database Save:**
   - Saves: datetime, lot, product_type, object_name, size_max
   - Transaction-based (commit/rollback)

## Security

- Password is encrypted in transit (HTTPS recommended)
- Use strong passwords for database accounts
- Restrict database user permissions (INSERT only if possible)
- Firewall: Allow only specific IPs to database

## Troubleshooting

**Connection Failed:**
- Check ODBC Driver 17 for SQL Server is installed
- Verify host/IP and port are correct
- Test SQL Server connectivity: `telnet 10.0.191.15 1433`
- Check SQL Server authentication mode (SQL Server Auth enabled)

**Session Not Saving:**
- Verify measurements reached trigger count
- Check object name matches detected objects
- Review backend logs for errors

## Database Schema

```sql
CREATE TABLE tbl_testchecksize (
    datetime DATETIME NOT NULL,
    lot VARCHAR(50),
    product_type VARCHAR(50),
    obj VARCHAR(50),
    size FLOAT
);
```

## See Also

- **Full Documentation:** `docs/DATABASE_GUIDE.md`
- **API Reference:** Backend API endpoints in `python_scripts/backend_server.py`
- **Code:** `python_scripts/database/` module
