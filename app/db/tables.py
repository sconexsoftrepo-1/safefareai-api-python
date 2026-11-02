"""SQLAlchemy Core table definitions mirroring the EXISTING safefare schema (Flyway V1..V6).

Only the columns this service reads or writes are declared. These definitions only build queries; this
service never creates, alters or drops tables in SQL Server.
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Time,
    UnicodeText,
)

metadata = MetaData(schema="dbo")


def _id() -> Column:
    return Column("id", BigInteger, primary_key=True, autoincrement=True)


def _dt(name: str, nullable: bool = True) -> Column:
    return Column(name, DateTime, nullable=nullable)


tenants = Table("tenants", metadata, _id(), Column("code", String(50)), Column("status", String(20)))

vendor_accounts = Table(
    "vendor_accounts", metadata, _id(),
    Column("tenant_id", BigInteger, nullable=False),
    Column("name", String(100)),
    Column("base_url", String(300)),
    Column("api_version", String(10)),
    Column("secret_ref", String(300)),
    Column("vendor_user_id", BigInteger),
    Column("status", String(20)),
    _dt("last_ok_at"),
)

vendor_users = Table(
    "vendor_users", metadata, _id(),
    Column("tenant_id", BigInteger), Column("vendor_user_id", BigInteger),
    Column("is_key_owner", Boolean), _dt("deleted_at"),
)

users = Table(
    "users", metadata, _id(),
    Column("tenant_id", BigInteger, nullable=False),
    Column("email", String(320)),
    Column("role_id", BigInteger),
    Column("vendor_user_id", BigInteger),
    Column("status", String(20)),
    _dt("deleted_at"),
)

role_permissions = Table(
    "role_permissions", metadata,
    Column("role_id", BigInteger, primary_key=True),
    Column("permission_code", String(60), primary_key=True),
)

user_preferences = Table(
    "user_preferences", metadata,
    Column("tenant_id", BigInteger, primary_key=True),
    Column("user_id", BigInteger, primary_key=True),
    Column("alarm_popup_close_sec", SmallInteger),
    Column("alarm_popup_max", SmallInteger),
    _dt("updated_at"),
)

alarm_types = Table(
    "alarm_types", metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("code", String(40)), Column("label", String(120)), Column("category", SmallInteger),
    Column("default_severity", SmallInteger), Column("is_active", Boolean), _dt("updated_at"),
)

device_groups = Table(
    "device_groups", metadata, _id(),
    Column("tenant_id", BigInteger), Column("vendor_group_id", BigInteger), Column("name", String(150)),
    _dt("deleted_at"),
)

devices = Table(
    "devices", metadata, _id(),
    Column("tenant_id", BigInteger, nullable=False),
    Column("group_id", BigInteger),
    Column("vendor_vehicle_id", BigInteger),
    Column("name", String(100)),
    Column("terminal_no", String(20)),
    Column("camera_count", SmallInteger),
    Column("camera_lines", UnicodeText),
    _dt("deleted_at"),
)

device_latest_state = Table(
    "device_latest_state", metadata,
    Column("device_id", BigInteger, primary_key=True, autoincrement=False),
    Column("tenant_id", BigInteger, nullable=False),
    _dt("device_time"), _dt("received_at"),
    Column("lat", Float), Column("lon", Float), Column("speed_kmh", Float), Column("direction_deg", SmallInteger),
    Column("altitude_m", Float), Column("mileage_km", Numeric(12, 3, asdecimal=False)),
    Column("status_code", SmallInteger), Column("acc_on", Boolean), Column("position_mode", SmallInteger),
    Column("battery_pct", SmallInteger), Column("gsm_signal", SmallInteger), Column("network_type", SmallInteger),
    Column("sensors", UnicodeText), Column("active_alarm", String(200)), Column("video_capable", Boolean),
    _dt("updated_at"),
)

device_positions = Table(
    "device_positions", metadata,
    Column("tenant_id", BigInteger, nullable=False),
    Column("device_id", BigInteger, primary_key=True, autoincrement=False),
    Column("device_time", DateTime, primary_key=True),
    Column("lat", Float), Column("lon", Float), Column("speed_kmh", Float), Column("direction_deg", SmallInteger),
    Column("mileage_km", Numeric(12, 3, asdecimal=False)), Column("acc_on", Boolean),
    Column("run_state", SmallInteger), Column("position_state", SmallInteger), Column("battery_pct", SmallInteger),
    Column("is_backfill", Boolean), Column("extra", UnicodeText),
)

alarms = Table(
    "alarms", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("alarm_time", DateTime, primary_key=True),
    Column("tenant_id", BigInteger, nullable=False),
    Column("device_id", BigInteger, nullable=False),
    Column("alarm_type_id", Integer, nullable=False),
    Column("vendor_alarm_id", String(40), nullable=False),
    _dt("ended_at"),
    Column("severity", SmallInteger), Column("source", SmallInteger), Column("speed_kmh", Float),
    Column("lat", Float), Column("lon", Float), Column("address", String(300)),
    Column("duration_seconds", Integer), Column("media_status", String(15)), Column("handling_status", String(15)),
    Column("handling_outcome", String(20)), Column("handled_by", BigInteger), _dt("handled_at"),
    Column("rule_id", BigInteger), Column("raw_payload", UnicodeText), _dt("ingested_at"),
)

alarm_media = Table(
    "alarm_media", metadata, _id(),
    Column("tenant_id", BigInteger), Column("alarm_id", BigInteger), Column("alarm_time", DateTime),
    Column("media_type", String(10)), Column("channel", SmallInteger), Column("vendor_url", String(1000)),
    Column("status", String(15)),
)

alarm_actions = Table(
    "alarm_actions", metadata, _id(),
    Column("tenant_id", BigInteger), Column("alarm_id", BigInteger), Column("alarm_time", DateTime),
    Column("action_type", String(25)), Column("step_no", SmallInteger), Column("actor_user_id", BigInteger),
    Column("assignee_user_id", BigInteger), Column("note", String(1000)), Column("command_id", BigInteger),
    Column("is_automatic", Boolean), _dt("created_at"),
)

alarm_rules = Table(
    "alarm_rules", metadata, _id(),
    Column("tenant_id", BigInteger), Column("name", String(120)), Column("handling_mode", String(15)),
    Column("process_mode", String(10)), Column("auto_outcome", String(20)), Column("popup_enabled", Boolean),
    Column("notify_enabled", Boolean), Column("sound_enabled", Boolean), Column("group_id", BigInteger),
    Column("priority", SmallInteger), Column("enabled", Boolean), _dt("created_at"), _dt("updated_at"),
)

alarm_rule_types = Table(
    "alarm_rule_types", metadata,
    Column("rule_id", BigInteger, primary_key=True), Column("alarm_type_id", Integer, primary_key=True),
)

commands = Table(
    "commands", metadata, _id(),
    Column("tenant_id", BigInteger), Column("requested_by", BigInteger), Column("command_type", String(40)),
    Column("vendor_endpoint", String(100)), Column("payload", UnicodeText), Column("target_count", Integer),
    Column("status", String(10)), _dt("created_at"), _dt("completed_at"),
)

command_targets = Table(
    "command_targets", metadata, _id(),
    Column("tenant_id", BigInteger), Column("command_id", BigInteger), Column("device_id", BigInteger),
    Column("terminal_no", String(20)), Column("vendor_command_no", String(64)), Column("status", String(10)),
    Column("fail_reason", String(200)), Column("result", UnicodeText), _dt("sent_at"), _dt("finished_at"),
    Column("vendor_cmd_type", Integer), Column("vendor_result", String(20)),
)

video_export_jobs = Table(
    "video_export_jobs", metadata, _id(),
    Column("tenant_id", BigInteger), Column("device_id", BigInteger), Column("requested_by", BigInteger),
    Column("channel", SmallInteger), _dt("start_time"), _dt("end_time"), Column("data_type", SmallInteger),
    Column("stream_type", SmallInteger), Column("vendor_uuid", String(64)), Column("status", String(12)),
    Column("vendor_url", String(1000)), Column("error", String(500)), _dt("created_at"), _dt("ready_at"),
    Column("vendor_status", SmallInteger), _dt("checked_at"),
)

device_video_files = Table(
    "device_video_files", metadata, _id(),
    Column("tenant_id", BigInteger), Column("device_id", BigInteger), Column("channel", SmallInteger),
    _dt("begin_time"), _dt("end_time"), Column("data_type", SmallInteger), Column("stream_type", SmallInteger),
    Column("file_size_mb", Numeric(10, 2, asdecimal=False)), _dt("synced_at"),
)

device_media = Table(
    "device_media", metadata, _id(),
    Column("tenant_id", BigInteger), Column("device_id", BigInteger), Column("channel", SmallInteger),
    Column("media_type", SmallInteger), Column("trigger_type", SmallInteger), Column("operator_user", String(100)),
    _dt("captured_at"), Column("lat", Float), Column("lon", Float), _dt("start_time"), _dt("end_time"),
    Column("file_path", String(500)), Column("preview_url", String(1000)), _dt("synced_at"),
)

device_mileage_reports = Table(
    "device_mileage_reports", metadata, _id(),
    Column("tenant_id", BigInteger), Column("device_id", BigInteger), Column("period_start", Date),
    Column("period_end", Date), Column("distance_km", Numeric(12, 3, asdecimal=False)),
    Column("start_mileage_km", Numeric(14, 3, asdecimal=False)),
    Column("end_mileage_km", Numeric(14, 3, asdecimal=False)),
    Column("plate_color", String(30)), _dt("synced_at"),
)

device_activity_periods = Table(
    "device_activity_periods", metadata, _id(),
    Column("tenant_id", BigInteger), Column("device_id", BigInteger), Column("kind", String(10)),
    _dt("start_time"), _dt("end_time"), Column("duration_seconds", Integer), Column("duration_text", String(40)),
    Column("device_type", String(60)), _dt("synced_at"),
)

device_passthrough_messages = Table(
    "device_passthrough_messages", metadata, _id(),
    Column("tenant_id", BigInteger), Column("device_id", BigInteger), Column("vendor_message_id", String(40)),
    Column("message_type", Integer), Column("content", UnicodeText), _dt("vendor_created_at"),
    _dt("vendor_updated_at"), _dt("synced_at"),
)

custom_voices = Table(
    "custom_voices", metadata, _id(),
    Column("tenant_id", BigInteger), Column("vendor_voice_id", BigInteger), Column("name", String(120)),
    Column("vendor_path", String(500)), Column("file_size_mb", Numeric(8, 2, asdecimal=False)),
    Column("source", String(10)), _dt("created_at"), Column("vendor_user_id", BigInteger),
    Column("import_type", SmallInteger), Column("ftp_base_url", String(300)), _dt("vendor_created_at"),
    _dt("synced_at"), _dt("deleted_at"),
)

geofences = Table(
    "geofences", metadata, _id(),
    Column("tenant_id", BigInteger), Column("vendor_path_id", BigInteger), Column("name", String(150)),
    Column("shape_type", String(10)), Column("color", String(9)), Column("area_type", SmallInteger),
    Column("enabled", Boolean), Column("created_by", BigInteger), _dt("created_at"), _dt("updated_at"),
    _dt("deleted_at"), Column("rule_types", String(30)), Column("rule_param", SmallInteger),
    Column("max_speed", Integer), Column("param_text", String(400)), Column("select_type", SmallInteger),
    Column("select_ids", UnicodeText), Column("threshold", SmallInteger), Column("issued", UnicodeText),
    Column("vendor_user_id", BigInteger), _dt("synced_at"),
)

geofence_points = Table(
    "geofence_points", metadata,
    Column("geofence_id", BigInteger, primary_key=True), Column("seq", SmallInteger, primary_key=True),
    Column("lon", Float), Column("lat", Float),
)

geofence_rules = Table(
    "geofence_rules", metadata, _id(),
    Column("geofence_id", BigInteger), Column("rule_type", SmallInteger), Column("offset_meters", Integer),
    Column("max_speed_kmh", SmallInteger), Column("completion_pct", SmallInteger),
    Column("window_from", Time), Column("window_to", Time),
)

geofence_bindings = Table(
    "geofence_bindings", metadata,
    Column("geofence_id", BigInteger, primary_key=True), Column("target_type", String(10), primary_key=True),
    Column("target_id", BigInteger, primary_key=True),
)

geofence_reminders = Table(
    "geofence_reminders", metadata, _id(),
    Column("geofence_id", BigInteger), Column("rule_type", SmallInteger), Column("display_usage", SmallInteger),
    Column("tts_text", String(300)), Column("play_count", SmallInteger), Column("voice_id", BigInteger),
)

report_jobs = Table(
    "report_jobs", metadata, _id(),
    Column("tenant_id", BigInteger), Column("requested_by", BigInteger), Column("report_type", String(40)),
    Column("params", UnicodeText), Column("format", String(5)), Column("status", String(10)),
    Column("size_bytes", BigInteger), Column("error", String(500)), _dt("created_at"), _dt("started_at"),
    _dt("completed_at"),
)
