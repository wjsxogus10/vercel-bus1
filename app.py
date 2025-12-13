from flask import Flask
import requests
import xml.etree.ElementTree as ET
import json
import time

app = Flask(__name__)

# ==========================================
# 👇 방금 주신 최신 키(b614...) 적용 완료!
# ==========================================
kakao_key = "b614d52fa9ba9e548875038b15710d66"
data_key  = "d37ef28959d3391d0285eb9bf3e2b1b438f495ff248bbe61ace7f32f290bed83"

# 추적할 노선 리스트
target_routes = [
    {"id": "30300040", "name": "102번 (수통골-대전역)"},
    {"id": "30300037", "name": "105번 (충대-비래동)"},
    {"id": "30300038", "name": "106번 (비래동-목원대)"},
    {"id": "30300001", "name": "급행1번 (원내동-대전역)"},
    {"id": "30300002", "name": "급행2번 (봉산동-옥계동)"}
]

pos_url = "http://openapitraffic.daejeon.go.kr/api/rest/busposinfo/getBusPosByRtid"
path_url = "http://openapitraffic.daejeon.go.kr/api/rest/busRouteInfo/getStaionByRoute"

@app.route('/')
def home():
    # 1. 데이터 저장소 초기화
    all_data = {}
    for route in target_routes:
        all_data[route['name']] = {"buses": [], "path": []}

    status_msg = "데이터 수신 중..."

    # 2. 데이터 수집 (에러 무시하고 진행)
    try:
        for route in target_routes:
            # (1) 노선 경로
            try:
                p_params = {'serviceKey': data_key, 'busRouteId': route['id']}
                p_res = requests.get(path_url, params=p_params, timeout=2)
                if p_res.status_code == 200:
                    p_root = ET.fromstring(p_res.content)
                    for st in p_root.findall(".//itemList"):
                        all_data[route['name']]["path"].append({
                            "lat": st.find("BUS_NODE_Y_VAL").text, 
                            "lng": st.find("BUS_NODE_X_VAL").text
                        })
            except: pass

            # (2) 실시간 버스
            try:
                b_params = {'serviceKey': data_key, 'busRouteId': route['id']}
                b_res = requests.get(pos_url, params=b_params, timeout=2)
                if b_res.status_code == 200:
                    b_root = ET.fromstring(b_res.content)
                    items = b_root.findall(".//itemList")
                    if items:
                        for bus in items:
                            all_data[route['name']]["buses"].append({
                                "no": bus.find("PLATE_NO").text,
                                "lat": bus.find("GPS_LATI").text,
                                "lng": bus.find("GPS_LONG").text
                            })
            except: pass
        status_msg = "업데이트 완료"
    except:
        status_msg = "연결 불안정 (지도는 표시됨)"

    # 3. HTML 생성
    json_data = json.dumps(all_data, ensure_ascii=False)
    current_time = time.strftime("%H:%M")
    options_html = "".join([f'<option value="{r["name"]}">{r["name"]}</option>' for r in target_routes])

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="25">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>대전 버스 관제</title>
        <style>
            * {{ box-sizing: border-box; }}
            body, html {{ margin:0; padding:0; width:100%; height:100%; overflow:hidden; }}
            #map {{ position:absolute; top:0; left:0; width:100%; height:100%; z-index:0; }}
            .sidebar {{
                position:absolute; bottom:0; left:0; right:0; background:white; z-index:10;
                border-top-left-radius:20px; border-top-right-radius:20px;
                box-shadow:0 -3px 12px rgba(0,0,0,0.2); padding:20px; display:flex; flex-direction:column;
            }}
            .header-row {{ display:flex; justify-content:space-between; align-items:center; }}
            select {{ width:100%; padding:12px; font-size:16px; border-radius:10px; border:1px solid #ddd; margin-top:10px; }}
            .btn-group {{ display:flex; gap:10px; margin-top:10px; }}
            .btn {{ flex:1; padding:12px; font-size:14px; border:none; border-radius:10px; cursor:pointer; font-weight:bold; }}
            .btn-loc {{ background:#FEE500; color:#333; }}
            .btn-view {{ background:#eee; color:#333; }}
            @media (min-width: 768px) {{ .sidebar {{ top:0; bottom:0; width:320px; height:100%; right:auto; border-radius:0; }} }}
        </style>
    </head>
    <body>

    <div id="map"></div>

    <div class="sidebar">
        <div class="header-row">
            <h3 style="margin:0;">🚍 대전 버스 관제</h3>
            <span style="font-size:12px; background:#eee; padding:4px 8px; border-radius:10px;">{current_time}</span>
        </div>
        <div style="color:#666; font-size:13px; margin-top:5px;">상태: {status_msg}</div>
        <select id="routeSelect" onchange="changeRoute()">{options_html}</select>
        <div class="btn-group">
            <button class="btn btn-loc" onclick="moveToMe()">📍 내 위치</button>
            <button class="btn btn-view" onclick="toggleSkyview()">🛰 스카이뷰</button>
        </div>
        <div class="btn-group">
            <button class="btn btn-view" onclick="toggleTraffic()">🚦 교통정보</button>
        </div>
    </div>

    <script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_key}"></script>

    <script>
        if (typeof kakao === 'undefined') {{
            alert("❌ 지도 로딩 실패!\\n카카오 개발자 사이트 [플랫폼]-[Web] 메뉴에\\n현재 주소(URL)를 등록했는지 확인하세요.");
        }} else {{
            var mapContainer = document.getElementById('map'), 
                mapOption = {{ 
                    center: new kakao.maps.LatLng(36.3504, 127.3845), // 대전 시청 좌표
                    level: 7 
                }};
            var map = new kakao.maps.Map(mapContainer, mapOption);

            // [사용자 요청 기능] 줌 컨트롤 & 지도타입 컨트롤 추가
            var mapTypeControl = new kakao.maps.MapTypeControl();
            map.addControl(mapTypeControl, kakao.maps.ControlPosition.TOPRIGHT);
            var zoomControl = new kakao.maps.ZoomControl();
            map.addControl(zoomControl, kakao.maps.ControlPosition.RIGHT);

            var allData = {json_data};
            var currentMarkers = [];
            var currentPolyline = null;
            var isSkyview = false;
            var isTraffic = false;

            // 1. 내 위치
            function moveToMe() {{
                if (navigator.geolocation) {{
                    navigator.geolocation.getCurrentPosition(function(pos) {{
                        var loc = new kakao.maps.LatLng(pos.coords.latitude, pos.coords.longitude);
                        map.panTo(loc); new kakao.maps.Marker({{ position: loc }}).setMap(map);
                    }});
                }} else alert("위치 권한이 필요합니다.");
            }}

            // 2. 스카이뷰
            function toggleSkyview() {{
                if (isSkyview) map.setMapTypeId(kakao.maps.MapTypeId.ROADMAP);
                else map.setMapTypeId(kakao.maps.MapTypeId.HYBRID);
                isSkyview = !isSkyview;
            }}

            // 3. 교통정보 (사용자 요청 기능)
            function toggleTraffic() {{
                if (isTraffic) map.removeOverlayMapTypeId(kakao.maps.MapTypeId.TRAFFIC);
                else map.addOverlayMapTypeId(kakao.maps.MapTypeId.TRAFFIC);
                isTraffic = !isTraffic;
            }}

            // 4. 노선 변경
            function changeRoute() {{
                var routeName = document.getElementById("routeSelect").value;
                var data = allData[routeName];

                currentMarkers.forEach(m => m.setMap(null)); currentMarkers = [];
                if (currentPolyline) currentPolyline.setMap(null);

                // 빨간 선
                if (data.path.length > 0) {{
                    var line = data.path.map(p => new kakao.maps.LatLng(p.lat, p.lng));
                    currentPolyline = new kakao.maps.Polyline({{ path: line, strokeWeight: 6, strokeColor: '#ff0000', strokeOpacity: 0.7 }});
                    currentPolyline.setMap(map);
                }}
                // 버스 마커
                data.buses.forEach(bus => {{
                    var marker = new kakao.maps.Marker({{
                        position: new kakao.maps.LatLng(bus.lat, bus.lng),
                        image: new kakao.maps.MarkerImage('https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/bus.png', new kakao.maps.Size(30, 32)),
                        title: bus.no
                    }});
                    marker.setMap(map); currentMarkers.push(marker);
                    var iw = new kakao.maps.InfoWindow({{ content: '<div style="padding:5px;">' + bus.no + '</div>' }});
                    kakao.maps.event.addListener(marker, 'click', function() {{ iw.open(map, marker); }});
                }});
            }}
            changeRoute();
        }}
    </script>
    </body>
    </html>
    """
