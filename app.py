from flask import Flask
import requests
import xml.etree.ElementTree as ET
import json
import time
import traceback

app = Flask(__name__)

# ==========================================
# 👇 본인의 키를 입력하세요
# ==========================================
kakao_key = "96634d7c069478bed5140146cefd7002" 
data_key  = "d37ef28959d3391d0285eb9bf3e2b1b438f495ff248bbe61ace7f32f290bed83"

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
    # 1. [안전장치] 데이터 통을 먼저 만들어둡니다. (데이터 실패해도 지도는 그려야 하니까)
    all_data = {}
    for route in target_routes:
        all_data[route['name']] = {"buses": [], "path": []}
    
    status_msg = "데이터 수신 중..."
    
    # 2. 데이터 수집 시도 (실패해도 무시하고 진행)
    try:
        for route in target_routes:
            # (1) 노선 경로 (빨간 선)
            try:
                p_params = {'serviceKey': data_key, 'busRouteId': route['id']}
                p_res = requests.get(path_url, params=p_params, timeout=2) # 타임아웃 짧게
                if p_res.status_code == 200:
                    p_root = ET.fromstring(p_res.content)
                    for st in p_root.findall(".//itemList"):
                        all_data[route['name']]["path"].append({
                            "lat": st.find("BUS_NODE_Y_VAL").text, 
                            "lng": st.find("BUS_NODE_X_VAL").text
                        })
            except: pass # 노선 못 가져와도 패스

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

    except Exception:
        status_msg = "서버 연결 불안정 (지도는 표시됨)"

    # 3. HTML 생성 (여기서부터는 무조건 실행됩니다)
    json_data = json.dumps(all_data, ensure_ascii=False)
    current_time = time.strftime("%H:%M")
    options_html = "".join([f'<option value="{r["name"]}">{r["name"]}</option>' for r in target_routes])

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="20">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>대전 버스 관제</title>
        <style>
            * {{ box-sizing: border-box; font-family: 'Apple SD Gothic Neo', '맑은 고딕', sans-serif; }}
            body, html {{ margin:0; padding:0; width:100%; height:100%; overflow: hidden; }}
            
            /* 지도는 무조건 전체 화면에 깝니다 (z-index 0) */
            #map {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; }}

            /* 컨트롤 패널은 지도 위에 띄웁니다 (z-index 1000) */
            .sidebar {{
                position: absolute; bottom: 0; left: 0; right: 0;
                background: white; z-index: 1000;
                border-top-left-radius: 20px; border-top-right-radius: 20px;
                box-shadow: 0 -2px 10px rgba(0,0,0,0.2);
                padding: 20px; display: flex; flex-direction: column;
                height: 200px;
            }}
            
            select {{ width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 10px; }}
            
            @media (min-width: 768px) {{
                .sidebar {{ top: 0; bottom: 0; width: 300px; height: 100%; right: auto; border-radius: 0; }}
            }}
        </style>
    </head>
    <body>

    <div id="map"></div>

    <div class="sidebar">
        <h2 style="margin:0 0 10px 0;">🚍 대전 버스 관제</h2>
        <div style="font-size:12px; color:#666; margin-bottom:5px;">{current_time} 기준 • {status_msg}</div>
        <select id="routeSelect" onchange="changeRoute()">
            {options_html}
        </select>
        <div style="font-size:11px; color:#aaa; margin-top:auto; text-align:center;">
            오른쪽 위 버튼으로 '스카이뷰' 전환 가능
        </div>
    </div>

    <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_key}"></script>
    <script>
        // 지도가 로딩 안 되면 알림 띄우기 (화면이 하얗게 되는 거 방지)
        if (typeof kakao === 'undefined') {{
            alert("❌ 지도를 불러오지 못했습니다.\\n카카오 개발자 사이트에서 '사이트 도메인'을 등록했는지 꼭 확인하세요!");
        }} else {{
            var mapContainer = document.getElementById('map'), 
                mapOption = {{ center: new kakao.maps.LatLng(36.3504, 127.3845), level: 8 }};
            var map = new kakao.maps.Map(mapContainer, mapOption);
            
            // 지도 컨트롤 (스카이뷰 버튼 등)
            var mapTypeControl = new kakao.maps.MapTypeControl();
            map.addControl(mapTypeControl, kakao.maps.ControlPosition.TOPRIGHT);
            var zoomControl = new kakao.maps.ZoomControl();
            map.addControl(zoomControl, kakao.maps.ControlPosition.RIGHT);

            var allData = {json_data};
            var currentMarkers = [];
            var currentPolyline = null;

            function changeRoute() {{
                var select = document.getElementById("routeSelect");
                var selectedRoute = select.value;
                localStorage.setItem("lastRoute", selectedRoute);

                for (var i = 0; i < currentMarkers.length; i++) currentMarkers[i].setMap(null);
                currentMarkers = [];
                if (currentPolyline) {{ currentPolyline.setMap(null); currentPolyline = null; }}

                var data = allData[selectedRoute];
                if (!data) return;

                // 노선 그리기
                if (data.path.length > 0) {{
                    var linePath = [];
                    for (var i = 0; i < data.path.length; i++) {{
                        linePath.push(new kakao.maps.LatLng(data.path[i].lat, data.path[i].lng));
                    }}
                    currentPolyline = new kakao.maps.Polyline({{
                        path: linePath, strokeWeight: 6, strokeColor: '#FF0000', strokeOpacity: 0.7, strokeStyle: 'solid'
                    }});
                    currentPolyline.setMap(map);
                }}

                // 버스 마커
                if (data.buses.length > 0) {{
                    for (var i = 0; i < data.buses.length; i++) {{
                        var bus = data.buses[i];
                        var marker = new kakao.maps.Marker({{
                            position: new kakao.maps.LatLng(bus.lat, bus.lng),
                            image: new kakao.maps.MarkerImage('https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/bus.png', new kakao.maps.Size(30, 32)),
                            title: bus.no
                        }});
                        marker.setMap(map);
                        currentMarkers.push(marker);
                        var iw = new kakao.maps.InfoWindow({{ content: '<div style="padding:5px;">' + bus.no + '</div>' }});
                        kakao.maps.event.addListener(marker, 'click', function() {{ iw.open(map, marker); }});
                    }}
                }}
            }}

            window.onload = function() {{
                var savedRoute = localStorage.getItem("lastRoute");
                if (savedRoute) document.getElementById("routeSelect").value = savedRoute;
                changeRoute();
            }};
        }}
    </script>
    </body>
    </html>
    """



