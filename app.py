from flask import Flask
import requests
import xml.etree.ElementTree as ET
import json
import time

app = Flask(__name__)

# =======================
# 반드시 JavaScript 키!
# =======================
kakao_key = "04aff0fd4597913b68a5686cbe46d559"  
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
            except:
                pass

            # (2) 실시간 버스 위치
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
            except:
                pass

        status_msg = "업데이트 완료"

    except:
        status_msg = "연결 불안정 (지도는 표시됨)"

    json_data = json.dumps(all_data, ensure_ascii=False)
    current_time = time.strftime("%H:%M")
    options_html = "".join(
        [f'<option value="{r["name"]}">{r["name"]}</option>' for r in target_routes]
    )

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

            #map {{
                position:absolute; top:0; left:0;
                width:100%; height:100%; z-index:0;
            }}

            .sidebar {{
                position:absolute; bottom:0; left:0; right:0;
                background:white; z-index:10;
                border-top-left-radius:20px; border-top-right-radius:20px;
                box-shadow:0 -3px 12px rgba(0,0,0,0.2);
                padding:20px;
            }}

            select {{
                width:100%; padding:12px; font-size:16px;
                border-radius:10px; border:1px solid #ddd; margin-top:10px;
            }}

            .btn-group {{
                display:flex; gap:10px; margin-top:10px;
            }}

            .btn {{
                flex:1; padding:12px; font-size:15px;
                border:none; border-radius:10px; cursor:pointer;
                font-weight:bold;
            }}

            .btn-loc {{ background:#FEE500; }}
            .btn-view {{ background:#eee; }}
        </style>
    </head>
    <body>

    <div id="map"></div>

    <div class="sidebar">
        <div style="display:flex; justify-content:space-between;">
            <h3 style="margin:0;">🚍 대전 버스 관제</h3>
            <span style="font-size:12px; background:#eee; padding:4px 8px; border-radius:10px;">
                {current_time}
            </span>
        </div>

        <div style="color:#666; font-size:13px; margin-bottom:8px;">
            상태: {status_msg}
        </div>

        <select id="routeSelect" onchange="changeRoute()">{options_html}</select>

        <div class="btn-group">
            <button class="btn btn-loc" onclick="moveToMe()">📍 내 위치</button>
            <button class="btn btn-view" onclick="toggleSkyview()">🛰 스카이뷰</button>
        </div>

        <div class="btn-group">
            <button class="btn btn-view" onclick="toggleTraffic()">🚦 교통정보</button>
        </div>
    </div>

    <!-- ===== 카카오맵 JS SDK (안정화 버전) ===== -->
    <script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_key}&autoload=false"></script>

    <script>
        // SDK 로딩 완료 후 실행
        kakao.maps.load(function() {{
            try {{
                var mapContainer = document.getElementById('map');
                var mapOption = {{
                    center: new kakao.maps.LatLng(36.3504, 127.3845),
                    level: 7
                }};

                window.map = new kakao.maps.Map(mapContainer, mapOption);

                var isSkyview = false;
                var isTraffic = false;
                var allData = {json_data};
                var currentMarkers = [];
                var currentPolyline = null;

                // ========== 내 위치 ==========
                window.moveToMe = function() {{
                    if (navigator.geolocation) {{
                        navigator.geolocation.getCurrentPosition(function(pos) {{
                            var loc = new kakao.maps.LatLng(pos.coords.latitude, pos.coords.longitude);
                            map.panTo(loc);
                            new kakao.maps.Marker({{ position: loc }}).setMap(map);
                        }});
                    }}
                }}

                // ========== 스카이뷰 ==========
                window.toggleSkyview = function() {{
                    if (isSkyview) {{
                        map.setMapTypeId(kakao.maps.MapTypeId.ROADMAP);
                    }} else {{
                        map.setMapTypeId(kakao.maps.MapTypeId.HYBRID);
                    }}
                    isSkyview = !isSkyview;
                }}

                // ========== 교통정보 ==========
                window.toggleTraffic = function() {{
                    if (isTraffic) {{
                        map.removeOverlayMapTypeId(kakao.maps.MapTypeId.TRAFFIC);
                    }} else {{
                        map.addOverlayMapTypeId(kakao.maps.MapTypeId.TRAFFIC);
                    }}
                    isTraffic = !isTraffic;
                }}

                // ========== 노선 변경 ==========
                window.changeRoute = function() {{
                    var routeName = document.getElementById("routeSelect").value;
                    var data = allData[routeName];

                    // 기존 마커 제거
                    currentMarkers.forEach(m => m.setMap(null));
                    currentMarkers = [];

                    // 경로 제거
                    if (currentPolyline) currentPolyline.setMap(null);

                    // 경로 다시 그림
                    if (data.path.length > 0) {{
                        var line = data.path.map(p => new kakao.maps.LatLng(p.lat, p.lng));
                        currentPolyline = new kakao.maps.Polyline({{
                            path: line,
                            strokeWeight: 6,
                            strokeColor: '#ff0000',
                            strokeOpacity: 0.7
                        }});
                        currentPolyline.setMap(map);
                    }}

                    // 버스 마커 표시
                    data.buses.forEach(bus => {{
                        var marker = new kakao.maps.Marker({{
                            position: new kakao.maps.LatLng(bus.lat, bus.lng),
                            image: new kakao.maps.MarkerImage(
                                'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/bus.png',
                                new kakao.maps.Size(30, 32)
                            ),
                            title: bus.no
                        }});
                        marker.setMap(map);
                        currentMarkers.push(marker);
                    }});
                }}

                // 첫 로딩 시 노선 선택
                changeRoute();

            }} catch(e) {{
                alert("❌ 지도 초기화 오류: " + e);
            }}
        }});

        // 로딩 실패 체크
        setTimeout(function(){{
            if (typeof kakao === "undefined") {{
                alert(
                    "❌ 카카오맵 로딩 실패!\\n" +
                    "카카오 개발자사이트 → 웹 플랫폼에 아래 도메인을 등록하세요.\\n\\n" +
                    "- http://localhost:5000\\n" +
                    "- http://127.0.0.1:5000\\n" +
                    "- http://localhost\\n" +
                    "- http://127.0.0.1"
                );
            }}
        }}, 1500);
    </script>

    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)
