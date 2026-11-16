-- Run ONCE in SSMS against the Safe-Fare database. Safe to re-run.
-- dbo.vehicle_maintenance is NOT changed. Postponements are stored here, one row per postponement.
-- A postponement belongs to one cycle: (tenant_id, vehicle_number, device_id, cycle_previous_date).
-- Once the maintenance is completed, previous_vehicle_maintenance_date moves forward, so older rows stop
-- matching and postponed_date reads as NULL for the new cycle. Rows are kept as history.

IF OBJECT_ID('dbo.vehicle_maintenance_postponements', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.vehicle_maintenance_postponements (
        id                  BIGINT IDENTITY(1,1) PRIMARY KEY,
        tenant_id           BIGINT        NOT NULL,
        vehicle_number      NVARCHAR(50)  NOT NULL,
        device_id           BIGINT        NULL,
        cycle_previous_date DATE          NULL,      -- previous_vehicle_maintenance_date of the cycle it belongs to
        expected_date       DATE          NULL,      -- the expected date at the time (kept for history)
        postponed_date      DATE          NOT NULL,  -- date the driver says it will be completed
        reason              NVARCHAR(1000) NOT NULL,
        postponed_by        NVARCHAR(100) NULL,      -- user who postponed
        created_at          DATETIME2     NOT NULL DEFAULT SYSDATETIME()
    );

    CREATE INDEX IX_vm_postponements_cycle
        ON dbo.vehicle_maintenance_postponements (tenant_id, vehicle_number, device_id, cycle_previous_date, id DESC);
END;

SELECT * FROM dbo.vehicle_maintenance_postponements;
