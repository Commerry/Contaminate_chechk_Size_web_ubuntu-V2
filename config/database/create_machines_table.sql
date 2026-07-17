-- ============================================================================
-- PSE Vision - Machine Management Table
-- ============================================================================
-- This script creates the machines table for storing machine information
-- and populates it with initial sample data
-- ============================================================================

-- Create machines table if not exists
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'tbl_machines')
BEGIN
    CREATE TABLE tbl_machines (
        id VARCHAR(50) PRIMARY KEY,           -- Machine ID (e.g., 'MC-01', 'MC-02')
        name NVARCHAR(255) NOT NULL,          -- Machine name
        description NVARCHAR(500),            -- Machine description
        status VARCHAR(20) DEFAULT 'active',  -- Status: active, inactive, maintenance
        location NVARCHAR(255),               -- Physical location
        created_at DATETIME DEFAULT GETDATE(), -- Creation timestamp
        updated_at DATETIME                   -- Last update timestamp
    );
    
    PRINT 'Table tbl_machines created successfully';
END
ELSE
BEGIN
    PRINT 'Table tbl_machines already exists';
END
GO

-- Insert sample machines (only if table is empty)
IF NOT EXISTS (SELECT * FROM tbl_machines)
BEGIN
    INSERT INTO tbl_machines (id, name, description, status, location, created_at)
    VALUES 
        ('MC-01', N'Machine 01', N'กล้องตรวจจับเครื่องที่ 1', 'active', N'สายการผลิต A', GETDATE()),
        ('MC-02', N'Machine 02', N'กล้องตรวจจับเครื่องที่ 2', 'active', N'สายการผลิต B', GETDATE()),
        ('MC-03', N'Machine 03', N'กล้องตรวจจับเครื่องที่ 3', 'active', N'สายการผลิต C', GETDATE());
    
    PRINT 'Sample machines inserted successfully';
END
ELSE
BEGIN
    PRINT 'Machines already exist in table';
END
GO

-- Display all machines
SELECT 
    id AS 'Machine ID',
    name AS 'Machine Name',
    description AS 'Description',
    status AS 'Status',
    location AS 'Location',
    created_at AS 'Created At'
FROM tbl_machines
ORDER BY id;
GO

-- Create index on status for faster queries
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_machines_status')
BEGIN
    CREATE INDEX idx_machines_status ON tbl_machines(status);
    PRINT 'Index idx_machines_status created successfully';
END
GO

PRINT '';
PRINT '============================================================================';
PRINT 'Machine Management Table Setup Complete';
PRINT '============================================================================';
PRINT 'Total machines: ' + CAST((SELECT COUNT(*) FROM tbl_machines) AS VARCHAR);
PRINT 'Active machines: ' + CAST((SELECT COUNT(*) FROM tbl_machines WHERE status = ''active'') AS VARCHAR);
PRINT '============================================================================';
