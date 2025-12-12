from flask import Flask
import requests
import xml.etree.ElementTree as ET
import json
import time
import traceback

app = Flask(__name__)

# ==========================================
# 👇 본인의 키를 입력하세요 (따옴표 안에!)
# ==========================================
kakao_key = "949989b1747758ede537aac1af1d60db" 
data_key  = "d37ef28959d3391d0285eb9bf3e2b1b438f495ff248bbe61ace7f32f290bed83"

# 표시할 주요 노선 리스트
target_routes = [
    {"id": "30300040", "name": "102번 (수통골-대전역)"},
    {"id": "30300037", "name": "105번 (충대-비래동)"},
    {"id": "30300038", "name": "106번 (비래동-목원대)"},
    {"id": "30300001", "name": "급행1번 (원내동-대전역)"},
    {"id": "30300002", "name": "급행2번 (봉산동-옥계동)"}
]

# 1. 버스 위치 URL (실시간)
pos_url = "http://openapitraffic.daejeon.go.kr/api/rest/busposinfo/getBusPosByRtid"
# 2. 노선 경유지 URL (선 그리기용 - 정류장 목록)
path_url = "http://openapitraffic.daejeon.go.kr/api/rest/busRouteInfo/getStaionByRoute"

@app.route('/')
def home():
    try:
        all_data = {} # 여기에 { "102번": { "buses": [], "path": [] } } 형태로 담습니다.
        
        # 각 노선별로 데이터 수집
        for route in target_routes:
            route_info = {
                "buses": [],  # 실시간 버스 위치
                "path": []    # 노선 경로 (선 그리기용)
            }
            
            # --- [1] 노선 경로(정류장) 가져오기 ---
            # 선은 자주 안 변하니까 에러나면 그냥 빈 선으로 둡니다.
            try:
                p_params = {'serviceKey': data_key, 'busRouteId': route['id']}
                p_res = requests.get(path_url, params=p_params, timeout=3)
                if p_res.status_code == 200:
                    p_root = ET.fromstring(p_res.content)
                    stations = p_root.findall(".//itemList")
                    for st in stations:
                        # 대전 API: BUS_NODE_Y_VAL = 위도(Latitude), BUS_NODE_X_VAL = 경도(Longitude)
                        # 순서 헷갈리면 지도가 엉망이 되니 주의!
                        route_info["path"].append({
                            "lat": st.find("BUS_NODE_Y_VAL").text, 
                            "lng": st.find("BUS_NODE_X_VAL").text
                        })
            except:
                pass 

            # --- [2] 실시간 버스 위치 가져오기 ---
            try:
                b_params = {'serviceKey': data_key, 'busRouteId': route['id']}
                b_res = requests.get(pos_url, params=b_params, timeout=3)
                if b_res.status_code == 200:
                    b_root = ET.fromstring(b_res.content)
                    items = b_root.findall(".//itemList")
                    if items:
                        for bus in items:
                            route_info["buses"].append({
                                "no": bus.find("PLATE_NO").text,
                                "lat": bus.find("GPS_LATI").text,
                                "lng": bus.find("GPS_LONG").text
                            })
            except:
                pass

            all_data[route['name']] = route_info

        # HTML 생성
        json_data = json.dumps(all_data, ensure_ascii=False)
        current_time = time.strftime("%H:%M")
        
        options_html = ""
        for route in target_routes:
            options_html += f'<option value="{route["name"]}">{route["name"]}</option>'

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta http-equiv="refresh" content="20"> <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <title>대전 버스 노선 관제</title>
            <style>
                * {{ box-sizing: border-box; font-family: 'Apple SD Gothic Neo', '맑은 고딕', sans-serif; }}
                body, html {{ margin:0; padding:0; width:100%; height:100%; overflow: hidden; }}
                
                .sidebar {{
                    position: absolute; bottom: 0; left: 0; right: 0;
                    background: white; z-index: 1000;
                    border-top-left-radius: 20px; border-top-right-radius: 20px;
                    box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
                    padding: 20px; display: flex; flex-direction: column;
                    height: 200px;
                }}
                select {{ width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 10px; }}
                .status {{ font-size: 12px; color: #666; margin-bottom: 5px; text-align: center; }}
                #map {{ position: absolute; top: 0; left: 0; right: 0; bottom: 200px; }}

                @media (min-width: 768px) {{
                    .sidebar {{ top: 0; bottom: 0; width: 300px; height: 100%; right: auto; border-radius: 0; }}
                    #map {{ bottom: 0; left: 300px; }}
                }}
            </style>
        </head>
        <body>

        <div id="map"></div>

        <div class="sidebar">
            <h2 style="margin:0 0 10px 0;">🚍 노선별 실시간 관제</h2>
            <div class="status">업데이트: {current_time}</div>
            <select id="routeSelect" onchange="changeRoute()">
                {options_html}
            </select>
            <div style="font-size:11px; color:#aaa; margin-top:auto; text-align:center;">
                노선을 선택하면 경로(빨간선)와 버스가 표시됩니다.
            </div>
        </div>

        <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_key}"></script>
        <script>
            var mapContainer = document.getElementById('map'), 
                mapOption = {{ center: new kakao.maps.LatLng(36.3504, 127.3845), level: 8 }};
            var map = new kakao.maps.Map(mapContainer, mapOption);
            
            var allData = {json_data};
            var currentMarkers = [];
            var currentPolyline = null; // 현재 그려진 선을 저장할 변수

            function changeRoute() {{
                var select = document.getElementById("routeSelect");
                var selectedRoute = select.value;
                localStorage.setItem("lastRoute", selectedRoute);

                // 1. 기존 마커 지우기
                for (var i = 0; i < currentMarkers.length; i++) currentMarkers[i].setMap(null);
                currentMarkers = [];

                // 2. 기존 선 지우기 (이게 없으면 선이 계속 겹쳐서 그려짐!)
                if (currentPolyline) {{
                    currentPolyline.setMap(null);
                    currentPolyline = null;
                }}

                var data = allData[selectedRoute];
                if (!data) return;

                // 3. 노선 그리기 (빨간 선)
                if (data.path.length > 0) {{
                    var linePath = [];
                    for (var i = 0; i < data.path.length; i++) {{
                        // 주의: 카카오맵은 (위도, 경도) 순서입니다.
                        linePath.push(new kakao.maps.LatLng(data.path[i].lat, data.path[i].lng));
                    }}
                    
                    currentPolyline = new kakao.maps.Polyline({{
                        path: linePath,
                        strokeWeight: 6,      // 선의 두께
                        strokeColor: '#FF0000', // 선의 색깔 (빨강)
                        strokeOpacity: 0.6,   // 선의 투명도 (0~1)
                        strokeStyle: 'solid'  // 선의 스타일
                    }});
                    currentPolyline.setMap(map);
                }}

                // 4. 버스 마커 찍기
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

                        var content = '<div style="padding:5px; font-size:12px;">' + bus.no + '</div>';
                        var iw = new kakao.maps.InfoWindow({{ content: content }});
                        kakao.maps.event.addListener(marker, 'click', function() {{ iw.open(map, marker); }});
                    }}
                }} else {{
                    // 버스는 없는데 노선만 있을 경우 (새벽 등)
                    if(data.path.length === 0) alert("데이터 수신 대기 중...");
                }}
            }}

            window.onload = function() {{
                var savedRoute = localStorage.getItem("lastRoute");
                if (savedRoute) document.getElementById("routeSelect").value = savedRoute;
                changeRoute();
            }};
        </script>
        </body>
        </html>
        """

    except Exception as e:
        return f"<h1>⚠️ 에러 발생</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>"
