-- 005 (DEVELOPMENT / TEST DATABASE ONLY - do not run in production).
-- Inserts the five sample BMS stops (Visakhapatnam -> Ongole) for ONE vehicle, only when that vehicle has no
-- stops yet. Existing rows are never changed. EDIT the four values below to match dbo.vehicles first.
-- The coordinates are sample route coordinates: validate them against the real bus stopping points.

DECLARE @tenant_id      BIGINT       = 1;
DECLARE @vehicle_number VARCHAR(30)  = 'AP31Z0044';
DECLARE @device_id      BIGINT       = 1215;
DECLARE @iot_kit        VARCHAR(100) = 'IOT-KIT-001';

IF NOT EXISTS (SELECT 1 FROM dbo.bms_stop_details
               WHERE tenant_id = @tenant_id AND vehicle_number = @vehicle_number AND device_id = @device_id)
BEGIN
    INSERT INTO dbo.bms_stop_details
        (tenant_id, vehicle_number, device_id, iot_kit, stop_sequence, stop_name, lat, [long], bms_in, bms_out, bms_total)
    VALUES
        (@tenant_id, @vehicle_number, @device_id, @iot_kit, 1, 'Anakapalle APSRTC Bus Station',        17.6863300, 83.0023400, 12, 0, 12),
        (@tenant_id, @vehicle_number, @device_id, @iot_kit, 2, 'Tuni APSRTC Bus Station',              17.3685600, 82.5432300,  6, 1, 17),
        (@tenant_id, @vehicle_number, @device_id, @iot_kit, 3, 'Rajamahendravaram APSRTC Bus Station', 17.0012000, 81.7897000,  9, 3, 23),
        (@tenant_id, @vehicle_number, @device_id, @iot_kit, 4, 'Vijayawada Pandit Nehru Bus Station',  16.5088038, 80.6156014,  7, 5, 25),
        (@tenant_id, @vehicle_number, @device_id, @iot_kit, 5, 'Ongole APSRTC Bus Station',            15.5112042, 80.0418439,  4, 6, 23);
END;

SELECT * FROM dbo.bms_stop_details
WHERE tenant_id = @tenant_id AND vehicle_number = @vehicle_number AND device_id = @device_id ORDER BY stop_sequence;
