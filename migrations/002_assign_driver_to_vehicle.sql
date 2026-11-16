-- Step 1 of 2: run in SSMS to make sure vehicles.driver_id exists.
-- Step 2: assign drivers with the API (PUT /api/vehicle-maintenance/{vehicle}/driver) or the UPDATE lines below.
-- Gives every vehicle ONE driver (users.id) so the maintenance alerts reach that driver.
-- The module reads vehicles.driver_id; it never writes to the vehicles table.

-- 1. Add the column if your vehicles table does not have it yet.
IF COL_LENGTH('dbo.vehicles', 'driver_id') IS NULL
    ALTER TABLE dbo.vehicles ADD driver_id BIGINT NULL;   -- change the type if users.id is not BIGINT
GO

-- 2. Look at the drivers (tenant 1 example; the drivers report to parent_user_id 73).
SELECT id, display_name, email, phone FROM dbo.users WHERE tenant_id = 1 AND parent_user_id = 73;

-- 3. Assign one driver to each vehicle (EDIT the ids / vehicle numbers; one UPDATE per vehicle).
UPDATE dbo.vehicles SET driver_id = 1204 WHERE tenant_id = 1 AND vehicle_number = 'AP31Z0044';
-- UPDATE dbo.vehicles SET driver_id = 1205 WHERE tenant_id = 1 AND vehicle_number = '<next vehicle>';

-- 4. Check: vehicles with no driver get no alerts.
SELECT v.vehicle_number, v.driver_id, u.display_name, u.email
FROM dbo.vehicles v LEFT JOIN dbo.users u ON u.id = v.driver_id AND u.tenant_id = v.tenant_id
WHERE v.tenant_id = 1;
