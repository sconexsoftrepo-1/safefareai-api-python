"""Typed wrappers for the GPS TrackTech endpoints used by the Python-assigned features.

Section numbers refer to API_EN.pdf. Only documented paths, methods and fields are used.
`retry=True` marks read-only calls; command / write calls are never retried automatically.
"""
from datetime import datetime

from app.core.timeutil import fmt_vendor
from app.vendor.client import VendorAccount, VendorClient, VendorResponse

QUERY_BY_DEVICE_ID = 1  # vendor queryType: 0 = device name, 1 = device ID (terminal number)


class GpsTrackTechApi:
    def __init__(self, client: VendorClient, account: VendorAccount):
        self.client = client
        self.account = account

    def _get(self, path: str, params: dict | None = None, *, retry: bool) -> VendorResponse:
        return self.client.request(self.account, "GET", path, params=params, retry=retry)

    def _post(self, path: str, body: dict, *, retry: bool) -> VendorResponse:
        return self.client.request(self.account, "POST", path, json=body, retry=retry)

    # 3.1 POST /monitor/getRealTimeInfo  (queryType is a string in the docs)
    def real_time_info(self, terminal_nos: list[str]) -> VendorResponse:
        return self._post("/monitor/getRealTimeInfo",
                          {"queryType": str(QUERY_BY_DEVICE_ID), "queryParams": terminal_nos}, retry=True)

    # 3.2 GET /track/getTrackList
    def track_list(self, terminal_no: str, begin: datetime, end: datetime, *, filter_time: int,
                   stop_status: int, pos_status: int) -> VendorResponse:
        return self._get("/track/getTrackList", {
            "filterTime": filter_time, "stopStatus": stop_status, "posStatus": pos_status,
            "beginTime": fmt_vendor(begin), "endTime": fmt_vendor(end),
            "queryType": QUERY_BY_DEVICE_ID, "queryParam": terminal_no}, retry=True)

    # 5.1 POST /alarm/recentlyAdasList
    def adas_alarms(self, terminal_nos: list[str], alarm_type_ids: list[int], start: datetime, end: datetime,
                    page: int, page_size: int) -> VendorResponse:
        return self._post("/alarm/recentlyAdasList", {
            "ids": alarm_type_ids, "pageNumber": page, "pageSize": page_size, "queryParams": terminal_nos,
            "queryType": QUERY_BY_DEVICE_ID, "startTime": fmt_vendor(start), "endTime": fmt_vendor(end)}, retry=True)

    # 5.8 POST /alarm/getAlarmInfo
    def routine_alarms(self, terminal_nos: list[str], alarm_type_ids: list[int], start: datetime, end: datetime,
                       page: int, page_size: int) -> VendorResponse:
        return self._post("/alarm/getAlarmInfo", {
            "ids": alarm_type_ids, "pageNumber": page, "pageSize": page_size, "queryParams": terminal_nos,
            "queryType": QUERY_BY_DEVICE_ID, "startTime": fmt_vendor(start), "endTime": fmt_vendor(end)}, retry=True)

    # 5.4 POST /alarm/recentlyList (last 24 hours, no time parameters)
    def recent_routine_alarms(self, terminal_nos: list[str], alarm_type_ids: list[int], page: int,
                              page_size: int) -> VendorResponse:
        return self._post("/alarm/recentlyList", {
            "ids": alarm_type_ids, "pageNumber": page, "pageSize": page_size, "queryParams": terminal_nos,
            "queryType": QUERY_BY_DEVICE_ID}, retry=True)

    # 5.7 GET /alarm/getAlarmType  (type: 0 all, 2 ADAS, 3 general, 4 DSM, 5 BSD)
    def alarm_types(self, category: int = 0) -> VendorResponse:
        return self._get("/alarm/getAlarmType", {"type": category}, retry=True)

    # 5.3 POST /multi/list  (type: 0 image, 1 video)
    def multimedia(self, terminal_nos: list[str], start: datetime, end: datetime, media_type: int, page: int,
                   page_size: int) -> VendorResponse:
        return self._post("/multi/list", {
            "startTime": fmt_vendor(start), "endTime": fmt_vendor(end), "pageNumber": page, "pageSize": page_size,
            "queryParams": terminal_nos, "queryType": QUERY_BY_DEVICE_ID, "type": media_type}, retry=True)

    def _report(self, path: str, terminal_nos: list[str], start: datetime, end: datetime, page: int,
                page_size: int) -> VendorResponse:
        return self._post(path, {
            "startTime": fmt_vendor(start), "endTime": fmt_vendor(end), "pageNumber": page, "pageSize": page_size,
            "queryParams": terminal_nos, "queryType": QUERY_BY_DEVICE_ID}, retry=True)

    # 5.2 / 5.5 / 5.6
    def parking_report(self, terminal_nos, start, end, page, page_size) -> VendorResponse:
        return self._report("/parkingReport/list", terminal_nos, start, end, page, page_size)

    def driving_report(self, terminal_nos, start, end, page, page_size) -> VendorResponse:
        return self._report("/drivingReport/list", terminal_nos, start, end, page, page_size)

    def mileage_report(self, terminal_nos, start, end, page, page_size) -> VendorResponse:
        return self._report("/mileageReport/list", terminal_nos, start, end, page, page_size)

    # 4.1 POST /video/devRecordQuery
    def record_query(self, terminal_no: str, start: datetime, end: datetime, channel: int | None) -> VendorResponse:
        body = {"startTime": fmt_vendor(start), "endTime": fmt_vendor(end), "queryType": QUERY_BY_DEVICE_ID,
                "queryParam": terminal_no}
        if channel is not None:
            body["channelNo"] = channel
        return self._post("/video/devRecordQuery", body, retry=True)

    # 4.4 POST /video/devFtpUpload  (sends a command to the terminal -> never retried)
    def ftp_upload(self, terminal_no: str, start: datetime, end: datetime, channel: int, data_type: int,
                   stream_type: int) -> VendorResponse:
        return self._post("/video/devFtpUpload", {
            "startTime": fmt_vendor(start), "endTime": fmt_vendor(end), "queryType": QUERY_BY_DEVICE_ID,
            "queryParam": terminal_no, "channel": channel, "datatype": data_type, "codetype": stream_type},
            retry=False)

    # 4.5 GET /cmd/getUploadResult
    def upload_result(self, uuid: str) -> VendorResponse:
        return self._get("/cmd/getUploadResult", {"uuid": uuid}, retry=True)

    # 4.6 GET /video/monthlyCalendar
    def monthly_calendar(self, terminal_no: str, year_month: str) -> VendorResponse:
        return self._get("/video/monthlyCalendar", {"terminalNo": terminal_no, "yearMonth": year_month}, retry=False)

    # 4.7 GET /video/getAvSdkTempTk
    def av_sdk_temp_token(self) -> VendorResponse:
        return self._get("/video/getAvSdkTempTk", retry=False)

    # 8.3 GET /command/wakenDevice
    def waken_device(self, terminal_nos: list[str]) -> VendorResponse:
        return self._get("/command/wakenDevice", {"terminalNo": ",".join(terminal_nos)}, retry=False)

    # 8.20 - 8.23 sensor calibration commands
    def fuel_set(self, terminal_nos: list[str], scales: list[dict]) -> VendorResponse:
        return self._post("/command/fuelSet", {"scales": scales, "terminalNo": ",".join(terminal_nos)}, retry=False)

    def temperature_set(self, terminal_nos: list[str], name: str, params: list[dict]) -> VendorResponse:
        return self._post("/command/temperatureSet", {"name": name, "temperatureParam": params,
                                                      "terminalNo": ",".join(terminal_nos)}, retry=False)

    def load_set(self, terminal_nos: list[str], load_info: list[dict]) -> VendorResponse:
        return self._post("/command/loadSet", {"loadInfoList": load_info, "terminalNo": ",".join(terminal_nos)},
                          retry=False)

    def ain_set(self, terminal_nos: list[str], sensor_req: dict) -> VendorResponse:
        return self._post("/command/ainSet", {"sensorReq": sensor_req, "terminalNo": ",".join(terminal_nos)},
                          retry=False)

    # 8.29 GET /command/passThroughSet
    def pass_through_set(self, terminal_nos: list[str], pass_through_type: int, content: str) -> VendorResponse:
        return self._get("/command/passThroughSet", {"terminalNo": ",".join(terminal_nos),
                                                     "passThroughType": pass_through_type, "content": content},
                         retry=False)

    # 8.30 GET /command/queryPassThroughData
    def query_pass_through(self, terminal_nos: list[str], pass_through_type: int, start: datetime,
                           end: datetime) -> VendorResponse:
        return self._get("/command/queryPassThroughData", {
            "terminalNo": ",".join(terminal_nos), "passThroughType": pass_through_type,
            "startTime": fmt_vendor(start), "endTime": fmt_vendor(end)}, retry=True)

    # 10.6 GET /path/getVoice  (no parameters)
    def path_voices(self) -> VendorResponse:
        return self._get("/path/getVoice", retry=True)

    # 9.2 GET /voice/getVoice
    def user_voices(self, vendor_user_id: int) -> VendorResponse:
        return self._get("/voice/getVoice", {"userId": vendor_user_id}, retry=True)

    # 9.1 POST /voice/addVoice  (multipart form: userId, name, file)
    def add_voice(self, vendor_user_id: int, name: str, filename: str, content: bytes) -> VendorResponse:
        return self.client.request(self.account, "POST", "/voice/addVoice",
                                   data={"userId": str(vendor_user_id), "name": name},
                                   files={"file": (filename, content, "audio/wav")}, retry=False)

    # 10.3 POST /path/add
    def add_path(self, body: dict) -> VendorResponse:
        return self._post("/path/add", body, retry=False)
