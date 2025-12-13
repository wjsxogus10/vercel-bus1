from flask import Flask

app = Flask(__name__)

# 사용자님의 키
kakao_key = "04aff0fd4597913b68a5686cbe46d559"

@app.route('/')
def home():
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>지도 테스트</title>
        <style>body, html {{ margin:0; width:100%; height:100%; }} #map {{ width:100%; height:100%; }}</style>
    </head>
    <body>
        <div id="map"></div>
        <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_key}"></script>
        <script>
            var container = document.getElementById('map');
            var options = {{ center: new kakao.maps.LatLng(36.3504, 127.3845), level: 7 }};
            var map = new kakao.maps.Map(container, options);
        </script>
    </body>
    </html>
    """
