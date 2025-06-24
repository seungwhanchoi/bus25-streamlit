import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib as mpl
import folium
from streamlit_folium import folium_static
from collections import defaultdict

from parameters import load_fixed_customers
from basic_simulator import simulate_fixed_route, CUSTOMERS, total_abandoned

# === 폰트 설정 ===
font_path = "C:/Windows/Fonts/malgun.ttf"
font_prop = fm.FontProperties(fname=font_path)
mpl.rcParams['font.family'] = font_prop.get_name()
mpl.rcParams['axes.unicode_minus'] = False

# === 페이지 설정 ===
st.set_page_config(page_title="25번 버스 대시보드", layout="wide")
st.title("🚌 25번 버스 시뮬레이션 & 분석")

# === 사이드바 메뉴 ===
page = st.sidebar.radio("📋 메뉴 선택", ["수요 예측", "시뮬레이션", "정류장 지도"])

# === 정류장 리스트 ===
stops_order = [
    '00_오이도차고지', '02_오이도해양단지.옥터초교입구', '03_오이도중앙로입구',
    '04_오이도종합어시장', '05_함상전망대', '06_오이도박물관', '07_대부도입구',
    '08_시화환경사업소', '09_시화염색단지입구', '10_삼양사', '11_열병합발전소',
    '12_우진플라스코', '13_대한통운.동화산업', '14_우석철강', '15_파워맥스',
    '16_삼화정공', '17_홈플러스', '18_청솔아파트', '19_계룡1차아파트',
    '20_중앙도서관', '21_이마트', '22_시화정형외과.이철신경외과',
    '23_소방서.군서고.여성비전센터', '24_정왕역', '25_정왕역환승센터',
    '26_소방서.군서고.여성비전센터', '27_군서미래국제학교', '28_시화정형외과',
    '29_금강아파트', '30_이마트', '31_중앙도서관', '32_세종3차아파트',
    '33_진로아파트', '34_홈플러스', '35_동국산업', '36_중앙알칸',
    '37_희망공원', '38_대한통운', '39_우진프라스코', '40_열병합발전소',
    '41_삼양사', '42_시화염색단지입구', '43_시화환경사업소', '44_오이도입구',
    '45_오이도박물관', '46_함상전망대', '47_오이도종합어시장', '48_오이도중앙로입구',
    '49_오이도해양단지.옥터초교입구', '50_오이도차고지'
]

# === 1. 수요 예측 ===
if page == "수요 예측":
    st.subheader("📊 수요 예측 분석")

    try:
        df = pd.read_excel("bus_25(10-16).xlsx", sheet_name="Sheet1")
        time_cols = ['10', '11', '12', '13', '14', '15', '16']
        df = df[['정류장_ID', '정류장', '일'] + time_cols]

        selected_date = st.selectbox("📅 날짜 선택", sorted(df["일"].dropna().unique()))
        filtered = df[df["일"] == selected_date]

        if not filtered.empty:
            st.markdown("### 📍 정류장별 수요 데이터")
            st.dataframe(filtered, use_container_width=True)

            total_by_time = filtered[time_cols].sum()

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.plot(total_by_time.index, total_by_time.values, marker='o', linewidth=2, color="#1f77b4")
            ax.fill_between(total_by_time.index, total_by_time.values, alpha=0.15, color="#1f77b4")
            for i, val in enumerate(total_by_time.values):
                ax.text(total_by_time.index[i], val + 0.5, str(int(val)), ha='center', fontsize=9)
            ax.set_xlabel("시간대")
            ax.set_ylabel("총 승객 수")
            ax.set_title(f"{selected_date} 시간대별 총 수요")
            ax.grid(True)
            st.pyplot(fig)

        else:
            st.warning("해당 날짜 데이터 없음")

    except Exception as e:
        st.error(f"❌ 파일 로딩 실패: {e}")

# === 2. 시뮬레이션 ===
elif page == "시뮬레이션":
    st.subheader("🚌 시뮬레이션 실행")

    CUSTOMERS.clear()
    CUSTOMERS.extend(load_fixed_customers())

    if st.button("🚦 실행하기"):
        import basic_simulator
        basic_simulator.total_abandoned = 0
        simulate_fixed_route()

        boarded = len([c for c in CUSTOMERS if c.boarded])
        dropped = len([c for c in CUSTOMERS if c.dropped_off])
        abandoned = len([c for c in CUSTOMERS if c.abandoned])
        total_distance = 0  # 선택 시 반환하도록 수정 가능

        col1, col2, col3 = st.columns(3)
        col1.metric("✅ 탑승자", f"{boarded} 명", delta=f"+{boarded}")
        col2.metric("📤 하차자", f"{dropped} 명")
        col3.metric("🚫 포기자", f"{abandoned} 명", delta=f"-{abandoned}", delta_color="inverse")

        st.markdown("### 👤 고객 상태 상세")
        df_cust = pd.DataFrame([{
            "ID": c.customer_id,
            "승차 정류장": c.boarding_stop,
            "하차 정류장": c.getoff_stop,
            "대기 시작": f"{c.time // 60:02d}:{c.time % 60:02d}",
            "탑승": c.boarded,
            "하차": c.dropped_off,
            "포기": c.abandoned
        } for c in CUSTOMERS])
        st.dataframe(df_cust, use_container_width=True)

# === 3. 정류장 지도 ===
elif page == "정류장 지도":
    st.subheader("🗺️ 정류장 지도 시각화")

    try:
        df_map = pd.read_excel("25번정류장_좌표.xlsx")
        df_map["ID_NUM"] = df_map["정류장_ID"].str.extract(r"(\d+)", expand=False).astype(int)
        df_map = df_map[(df_map["ID_NUM"] >= 0) & (df_map["ID_NUM"] <= 25)]
        df_map = df_map[~df_map["ID_NUM"].isin([1, 24])].sort_values("ID_NUM")
        coords = list(zip(df_map["y"], df_map["x"]))

        m = folium.Map(location=coords[0], zoom_start=14)
        coord_to_stops = defaultdict(list)
        for _, row in df_map.iterrows():
            coord = (row["y"], row["x"])
            coord_to_stops[coord].append((row["ID_NUM"], row["정류장"]))

        for coord, stops in coord_to_stops.items():
            lat, lon = coord
            ids = sorted([s[0] for s in stops])
            name = ", ".join([s[1] for s in stops])
            color = "green" if 0 in ids else "red" if 25 in ids else "blue"

            folium.Marker(coord, popup=name, tooltip=name, icon=folium.Icon(color=color)).add_to(m)
            folium.map.Marker(
                coord,
                icon=folium.DivIcon(html=f"""<div style="font-size:10pt; color:black">{ids[0]}</div>""")
            ).add_to(m)

        folium.PolyLine(coords, color="blue", weight=3, opacity=0.7).add_to(m)
        folium_static(m, width=900, height=600)

    except Exception as e:
        st.error(f"❌ 지도 로딩 실패: {e}")
