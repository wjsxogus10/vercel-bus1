from flask import Flask
import requests
import xml.etree.ElementTree as ET
import json
import time

app = Flask(__name__)

# ==========================================
# 👇 JavaScript 키 (반드시 JS 키여야 함)
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
    all_data = {}
    for route in target_routes:
        all_data[route['name']] = {"buses": [], "path": []}
    
    status_msg = "데이터 수신 중..."
    
    try:
        for route in target_routes:
            # 1. 경로 데이터
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

            # 2. 버스 위치 데이터
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
    except: status_msg = "연결 불안정"

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
            select {{ width:100%; padding:12px; font-size:16px; border-radius:10px; border:1px solid #ddd; margin-top:10px; }}
            .btn-group {{ display:flex; gap:10px; margin-top:10px; }}
            .btn {{ flex:1; padding:12px; font-size:14px; border:none; border-radius:10px; cursor:pointer; font-weight:bold; }}
            .btn-loc {{ background:#FEE500; color:#333; }}
            .btn-view {{ background:#eee; color:#333; }}
        </style>
    </head>
    <body>

    <div id="map"></div>

    <div class="sidebar">
        <h3>🚍 대전 버스 ({current_time})</h3>
        <div style="font-size:12px; color:#666;">상태: {status_msg}</div>
        <select id="routeSelect" onchange="changeRoute()">{options_html}</select>
        <div class="btn-group">
            <button class="btn btn-loc" onclick="moveToMe()">📍 내 위치</button>
            <button class="btn btn-view" onclick="toggleSkyview()">🛰 스카이뷰</button>
        </div>
    </div>

    <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_key}&autoload=false"></script>
    
    <script>
        // 1. 카카오 스크립트가 로드된 후 실행 (Error 해결의 핵심!)
        kakao.maps.load(function() {{
            var mapContainer = document.getElementById('map'), 
                mapOption = {{ center: new kakao.maps.LatLng(36.3504, 127.3845), level: 7 }};
            
            // 전역 변수로 map 설정
            window.map = new kakao.maps.Map(mapContainer, mapOption);
            window.isSkyview = false;
            
            // 데이터 준비
            var allData = {json_data};
            var currentMarkers = [];
            var currentPolyline = null;

            // 기능 함수들 연결
            window.moveToMe = function() {{
                if (navigator.geolocation) {{
                    navigator.geolocation.getCurrentPosition(function(pos) {{
                        var loc = new kakao.maps.LatLng(pos.coords.latitude, pos.coords.longitude);
                        map.panTo(loc); new kakao.maps.Marker({{ position: loc }}).setMap(map);
                    }});
                }} else alert("위치 권한 필요");
            }};

            window.toggleSkyview = function() {{
                if (window.isSkyview) map.setMapTypeId(kakao.maps.MapTypeId.ROADMAP);
                else map.setMapTypeId(kakao.maps.MapTypeId.HYBRID);
                window.isSkyview = !window.isSkyview;
            }};

            window.changeRoute = function() {{
                var routeName = document.getElementById("routeSelect").value;
                var data = allData[routeName];

                // 초기화
                currentMarkers.forEach(m => m.setMap(null)); currentMarkers = [];
                if (currentPolyline) currentPolyline.setMap(null);

                // 경로 그리기
                if (data.path.length > 0) {{
                    var line = data.path.map(p => new kakao.maps.LatLng(p.lat, p.lng));
                    currentPolyline = new kakao.maps.Polyline({{ path: line, strokeWeight: 6, strokeColor: '#ff0000', strokeOpacity: 0.7 }});
                    currentPolyline.setMap(map);
                }}

                // 버스 그리기
                data.buses.forEach(bus => {{
                    var marker = new kakao.maps.Marker({{
                        position: new kakao.maps.LatLng(bus.lat, bus.lng),
                        title: bus.no
                    }});
                    marker.setMap(map); currentMarkers.push(marker);
                }});
            }};
            
            // 처음 실행
            changeRoute();
        }});
    </script>
    </body>
    </html>
    """
