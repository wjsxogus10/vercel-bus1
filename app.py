Python 3.13.7 (tags/v3.13.7:bcee1c3, Aug 14 2025, 14:15:11) [MSC v.1944 64 bit (AMD64)] on win32
Enter "help" below or click "Help" above for more information.
>>> from flask import Flask
... import requests
... import xml.etree.ElementTree as ET
... import json
... import time
... 
... app = Flask(__name__)
... 
... # ==========================================
... # 👇 본인의 키를 입력하세요
... # ==========================================
... kakao_key = "949989b1747758ede537aac1af1d60db"
... data_key  = "d37ef28959d3391d0285eb9bf3e2b1b438f495ff248bbe61ace7f32f290bed83"
... 
... target_routes = [
...     {"id": "30300040", "name": "102번 (수통골-대전역)"},
...     {"id": "30300037", "name": "105번 (충대-비래동)"},
...     {"id": "30300038", "name": "106번 (비래동-목원대)"},
...     {"id": "30300001", "name": "급행1번 (원내동-대전역)"},
...     {"id": "30300002", "name": "급행2번 (봉산동-옥계동)"}
... ]
... 
... url = "http://openapitraffic.daejeon.go.kr/api/rest/busposinfo/getBusPosByRtid"
... 
... @app.route('/')
... def home():
...     all_bus_data = {}
...     total_bus_count = 0
...     status_msg = "데이터 수신 중..."
...     
...     try:
...         for route in target_routes:
...             all_bus_data[route['name']] = []
...             params = {'serviceKey': data_key, 'busRouteId': route['id']}
...             res = requests.get(url, params=params, timeout=3)
...             
...             if res.status_code == 200:
...                 root = ET.fromstring(res.content)
                items = root.findall(".//itemList")
                route_buses = []
                for bus in items:
                    route_buses.append({
                        "no": bus.find("PLATE_NO").text,
                        "lat": bus.find("GPS_LATI").text,
                        "lng": bus.find("GPS_LONG").text
                    })
                all_bus_data[route['name']] = route_buses
                total_bus_count += len(route_buses)

        if total_bus_count == 0:
            status_msg = "운행 종료 / 차량 없음"
        else:
            status_msg = f"현재 {total_bus_count}대 운행 중"

    except Exception as e:
        status_msg = "서버 연결 불안정"

    json_data = json.dumps(all_bus_data, ensure_ascii=False)
    current_time = time.strftime("%H:%M")
    
    options_html = ""
    for route in target_routes:
        options_html += f'<option value="{route["name"]}">{route["name"]}</option>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="15">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>대전 버스 시민 관제</title>
        <style>
            * {{ box-sizing: border-box; font-family: 'Apple SD Gothic Neo', '맑은 고딕', sans-serif; }}
            body, html {{ margin:0; padding:0; width:100%; height:100%; overflow: hidden; }}
            .sidebar {{
                position: absolute; bottom: 0; left: 0; right: 0;
                background: white; z-index: 1000;
                border-top-left-radius: 20px; border-top-right-radius: 20px;
                box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
                padding: 20px; display: flex; flex-direction: column;
                height: 220px;
            }}
            select {{ width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 10px; background: #fff; }}
            .btn-group {{ display: flex; gap: 10px; }}
            .btn {{ flex: 1; padding: 12px; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; }}
            .btn-loc {{ background: #4A90E2; color: white; }}
            .btn-traffic {{ background: #e8f0fe; color: #4A90E2; }}
            #map {{ position: absolute; top: 0; left: 0; right: 0; bottom: 220px; }}
            @media (min-width: 768px) {{
                .sidebar {{ top: 0; bottom: 0; width: 320px; height: 100%; right: auto; border-radius: 0; border-right: 1px solid #ddd; }}
                #map {{ bottom: 0; left: 320px; }}
            }}
        </style>
    </head>
    <body>
    <div id="map"></div>
    <div class="sidebar">
        <div style="font-weight:bold; font-size:18px; margin-bottom:5px;">🚍 대전 버스</div>
        <div style="font-size:12px; color:#666; margin-bottom:10px;">{current_time} 기준 • {status_msg}</div>
        <select id="routeSelect" onchange="changeRoute()">{options_html}</select>
        <div class="btn-group">
            <button class="btn btn-loc" onclick="moveToMe()">📍 내 위치</button>
            <button class="btn btn-traffic" id="trafficBtn" onclick="toggleTraffic()">🚦 교통 끄기</button>
        </div>
    </div>
    <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_key}"></script>
    <script>
        var mapContainer = document.getElementById('map'), mapOption = {{ center: new kakao.maps.LatLng(36.3504, 127.3845), level: 7 }};
        var map = new kakao.maps.Map(mapContainer, mapOption);
        map.addOverlayMapTypeId(kakao.maps.MapTypeId.TRAFFIC);
        var isTrafficOn = true;
        var allBusData = {json_data};
        var currentMarkers = [];
        
        function moveToMe() {{
            if (navigator.geolocation) {{
                navigator.geolocation.getCurrentPosition(function(position) {{
                    var locPosition = new kakao.maps.LatLng(position.coords.latitude, position.coords.longitude);
                    map.panTo(locPosition);
                    new kakao.maps.Marker({{ position: locPosition }}).setMap(map);
                }});
            }} else alert("위치 기능을 사용할 수 없습니다.");
        }}
        function toggleTraffic() {{
            var btn = document.getElementById("trafficBtn");
            if (isTrafficOn) {{ map.removeOverlayMapTypeId(kakao.maps.MapTypeId.TRAFFIC); btn.innerText = "🚦 교통 켜기"; btn.style.background = "#eee"; btn.style.color = "#333"; isTrafficOn = false; }}
            else {{ map.addOverlayMapTypeId(kakao.maps.MapTypeId.TRAFFIC); btn.innerText = "🚦 교통 끄기"; btn.style.background = "#e8f0fe"; btn.style.color = "#4A90E2"; isTrafficOn = true; }}
        }}
        function changeRoute() {{
            var select = document.getElementById("routeSelect");
            var selectedRoute = select.value;
            localStorage.setItem("lastRoute", selectedRoute);
            for (var i = 0; i < currentMarkers.length; i++) currentMarkers[i].setMap(null);
            currentMarkers = [];
            var buses = allBusData[selectedRoute];
            if (!buses) return;
            for (var i = 0; i < buses.length; i++) {{
                var bus = buses[i];
                var marker = new kakao.maps.Marker({{ position: new kakao.maps.LatLng(bus.lat, bus.lng), image: new kakao.maps.MarkerImage('https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/bus.png', new kakao.maps.Size(30, 32)), title: bus.no }});
                marker.setMap(map);
                currentMarkers.push(marker);
                var content = '<div style="padding:5px; font-weight:bold;">' + selectedRoute + '<br>' + bus.no + '</div>';
                var iw = new kakao.maps.InfoWindow({{ content: content }});
                kakao.maps.event.addListener(marker, 'click', function() {{ iw.open(map, marker); }});
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
