-- Read-only checks. Run in SSMS / Azure Data Studio against your database.

-- 1. Columns of vehicle_maintenance (should be the 11 columns from the brief)
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'vehicle_maintenance'
ORDER BY ORDINAL_POSITION;

-- 2. Columns of vehicles (must include tenant_id, vehicle_number, device_id)
SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'vehicles'
ORDER BY ORDINAL_POSITION;

-- 3. A vehicle you can use for testing (one with no maintenance row yet)
SELECT TOP 10 v.tenant_id, v.vehicle_number, v.device_id
FROM vehicles v
WHERE NOT EXISTS (SELECT 1 FROM vehicle_maintenance m
                  WHERE m.tenant_id = v.tenant_id AND m.vehicle_number = v.vehicle_number);

-- 4. Existing duplicates the module would refuse to touch (should return nothing)
SELECT tenant_id, vehicle_number, COUNT(*) AS rows_for_vehicle
FROM vehicle_maintenance
GROUP BY tenant_id, vehicle_number
HAVING COUNT(*) > 1;
