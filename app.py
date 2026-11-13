"""
AI301 - ĐỀ DỰ ÁN 08: GIAO DIỆN WEB STREAMLIT
Đánh giá hiệu quả chương trình bán hàng - Công ty Gia Hòa
Chạy ứng dụng: streamlit run app.py
"""

import os
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from agent_engine import (
    GiaHoaCampaignAgent,
    REQUIRED_SCHEMAS,
    parse_google_sheet_url,
    auto_classify_dataframe,
)

st.set_page_config(
    page_title="AI301 - Đề Dự Án 08 | AI Agent Công ty Gia Hòa",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện chuyên nghiệp theo đúng màu sắc sơ đồ Workflow
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        color: white;
        padding: 1.4rem 1.8rem;
        border-radius: 14px;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.12);
    }
    .badge-expand {
        background-color: #dcfce7;
        color: #166534;
        border: 1.5px solid #22c55e;
        padding: 6px 12px;
        border-radius: 8px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-adjust {
        background-color: #fef9c3;
        color: #854d0e;
        border: 1.5px solid #eab308;
        padding: 6px 12px;
        border-radius: 8px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-stop {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1.5px solid #ef4444;
        padding: 6px 12px;
        border-radius: 8px;
        font-weight: 700;
        display: inline-block;
    }
    .step-box {
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 8px;
        border-left: 5px solid #2563eb;
        background-color: #f8fafc;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
        <div>
            <span style="background:#3b82f6; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:700;">
                AI301 - AI AGENT | ĐỀ DỰ ÁN 08
            </span>
            <h2 style="margin:8px 0 4px 0; color:white;">Hệ Thống AI Agent Đánh Giá Hiệu Quả Chương Trình Bán Hàng - Công Ty Gia Hòa</h2>
            <p style="margin:0; opacity:0.9; font-size:0.95rem;">
                Chuẩn hóa dữ liệu đa nguồn • Khử trùng lặp doanh thu • Đối soát hàng trả • Phân bổ chi phí nhất quán • Đề xuất ngân sách giải thích được
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = BASE_DIR / "sample_data"
WORKFLOW_IMG = BASE_DIR / "workflow_gia_hoa.jpg"


def load_sample_datasets():
    mapping = {
        "don_hang": SAMPLE_DIR / "1_don_hang_giao_dich.csv",
        "uu_dai": SAMPLE_DIR / "2_su_dung_uu_dai.csv",
        "doi_tra": SAMPLE_DIR / "3_doi_tra_hang.csv",
        "san_pham": SAMPLE_DIR / "4_danh_muc_san_pham_gia_von.csv",
        "chi_phi": SAMPLE_DIR / "5_chi_phi_chuong_trinh.csv",
    }
    loaded = {}
    for k, path in mapping.items():
        if path.exists():
            loaded[k] = pd.read_csv(path)
    return loaded


# ================= SIDEBAR: CẤU HÌNH ĐẦU VÀO & QUY TẮC =================
with st.sidebar:
    st.header("📥 1. Nguồn Dữ Liệu Đầu Vào")
    input_mode = st.radio(
        "Chọn phương thức nạp dữ liệu:",
        options=[
            "Dữ liệu mẫu chuẩn Công ty Gia Hòa",
            "Tải lên file CSV / Excel (.xlsx)",
            "Liên kết Google Sheets (URL)"
        ],
        index=0
    )

    raw_tables = {}

    if input_mode == "Dữ liệu mẫu chuẩn Công ty Gia Hòa":
        raw_tables = load_sample_datasets()
        st.success(f"Đã nạp {len(raw_tables)}/5 tệp dữ liệu chuẩn của Công ty Gia Hòa.")
        with st.expander("Giả lập lỗi thiếu dữ liệu (Test nhánh Đỏ)"):
            simulate_missing = st.multiselect(
                "Bỏ bớt bảng để test bước 'Yêu cầu bổ sung dữ liệu':",
                options=list(REQUIRED_SCHEMAS.keys()),
                format_func=lambda k: REQUIRED_SCHEMAS[k]["label"]
            )
            for k in simulate_missing:
                raw_tables.pop(k, None)

    elif input_mode == "Tải lên file CSV / Excel (.xlsx)":
        st.info("Bạn có thể tải lên nhiều file `.csv` hoặc file `.xlsx` (nhiều sheet). AI Agent sẽ tự động phân loại bảng.")
        uploaded_files = st.file_uploader(
            "Chọn các tệp dữ liệu (CSV, XLSX):",
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=True
        )
        if uploaded_files:
            for uf in uploaded_files:
                fname = uf.name.lower()
                if fname.endswith(".csv"):
                    df = pd.read_csv(uf)
                    t_type = auto_classify_dataframe(df, uf.name) or uf.name
                    raw_tables[t_type] = df
                else:
                    xls = pd.ExcelFile(uf)
                    for sheet_name in xls.sheet_names:
                        df = pd.read_excel(uf, sheet_name=sheet_name)
                        t_type = auto_classify_dataframe(df, sheet_name) or f"{uf.name}_{sheet_name}"
                        raw_tables[t_type] = df

    elif input_mode == "Liên kết Google Sheets (URL)":
        st.info("Dán link Google Sheets (chế độ Bất kỳ ai có liên kết đều có thể xem) cho từng tệp dữ liệu:")
        for key, spec in REQUIRED_SCHEMAS.items():
            sheet_url = st.text_input(f"Link {spec['label']}:", key=f"gsheet_{key}", placeholder="https://docs.google.com/spreadsheets/d/...")
            if sheet_url.strip():
                try:
                    csv_export_url = parse_google_sheet_url(sheet_url)
                    raw_tables[key] = pd.read_csv(csv_export_url)
                    st.caption(f"✅ Đã kết nối {spec['label']}")
                except Exception as e:
                    st.error(f"Lỗi đọc link {spec['label']}: {e}")

    st.divider()
    st.header("⚙️ 2. Quy Tắc & Tiêu Chí Đánh Giá")
    attribution_rule = st.selectbox(
        "Quy tắc ghi nhận doanh thu (khi 1 đơn tiếp xúc nhiều CT):",
        options=["TY_TRONG_UU_DAI", "CHIA_DEU_LINEAR", "FIRST_TOUCH", "LAST_TOUCH"],
        format_func=lambda x: {
            "TY_TRONG_UU_DAI": "Theo tỷ trọng mức giảm giá thực tế (Khuyên dùng)",
            "CHIA_DEU_LINEAR": "Chia đều (Linear Multi-touch)",
            "FIRST_TOUCH": "Ưu tiên điểm chạm đầu tiên (First-Touch)",
            "LAST_TOUCH": "Ưu tiên điểm chạm cuối cùng (Last-Touch)"
        }[x]
    )

    shared_cost_rule = st.selectbox(
        "Quy tắc phân bổ chi phí chung (Marketing & Vận hành):",
        options=["THEO_DOANH_THU_THUAN", "THEO_SO_DON_QUY_DOI", "CHIA_DEU"],
        format_func=lambda x: {
            "THEO_DOANH_THU_THUAN": "Theo tỷ trọng Doanh thu thuần (Chuẩn kế toán)",
            "THEO_SO_DON_QUY_DOI": "Theo tỷ trọng Số lượng đơn hàng quy đổi",
            "CHIA_DEU": "Chia đều cho 4 chương trình (25%/CT)"
        }[x]
    )

    roi_expand_threshold = st.slider(
        "Ngưỡng ROI tối thiểu để TIẾP TỤC / MỞ RỘNG (%):",
        min_value=10.0, max_value=60.0, value=30.0, step=5.0
    )
    max_return_rate_expand = st.slider(
        "Ngưỡng Tỷ lệ trả hàng tối đa cho nhóm Mở rộng (%):",
        min_value=3.0, max_value=15.0, value=8.0, step=1.0
    )

# ================= KHỞI TẠO & CHẠY AI AGENT =================
agent = GiaHoaCampaignAgent()
val_report = agent.validate_and_classify(raw_tables)

# Hiển thị Sơ đồ quy trình & Trạng thái kiểm tra dữ liệu
with st.expander("🗺️ Xem Sơ Đồ Quy Trình Chuẩn (Workflow Công ty Gia Hòa - Đề 08)", expanded=False):
    if WORKFLOW_IMG.exists():
        st.image(str(WORKFLOW_IMG), caption="Quy trình đánh giá hiệu quả chương trình bán hàng - Công ty Gia Hòa (AI301 - Đề dự án 08)", use_container_width=True)

# Kiểm tra nhánh Decision 1: Dữ liệu hợp lệ & Đủ thông tin?
if not val_report["is_valid"]:
    st.error("🚨 **BƯỚC 3 (KIỂM TRA DỮ LIỆU): DỮ LIỆU CHƯA HỢP LỆ HOẶC THIẾU THÔNG TIN -> YÊU CẦU BỔ SUNG / LÀM RÕ DỮ LIỆU**")
    for err in val_report["missing_tables"] + val_report["schema_errors"]:
        st.warning(f"• {err}")
    st.info("💡 Vui lòng tải bổ sung các tệp còn thiếu ở thanh công cụ bên trái hoặc chọn **'Dữ liệu mẫu chuẩn Công ty Gia Hòa'** để tiếp tục.")
    st.stop()

# Nếu hợp lệ -> Chạy toàn bộ Pipeline (Bước 4 -> Bước 7)
results = agent.run_evaluation_pipeline(
    attribution_rule=attribution_rule,
    shared_cost_rule=shared_cost_rule,
    roi_expand_threshold=roi_expand_threshold,
    roi_stop_threshold=0.0,
    max_return_rate_expand=max_return_rate_expand
)

camp_df = results["campaign_metrics"]
attr_df = results["order_attribution"]
kpis = results["summary_kpis"]

# Hiển thị thanh trạng thái Pipeline
st.success(
    f"✅ **Trạng thái Quy trình AI Agent:** Đã thu thập 5 nguồn dữ liệu ➜ Kiểm tra hợp lệ (Đạt) ➜ "
    f"Khử trùng lặp {val_report['multi_touch_orders_count']} đơn đa chương trình ➜ Đối soát hàng trả & Phân bổ {kpis['total_shared_cost']:,.0f}đ chi phí chung ➜ Hoàn tất đánh giá 4 chương trình."
)

# ================= KPI TỔNG QUAN TOÀN CÔNG TY =================
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric(
    "Doanh thu báo cáo cũ (Trùng lặp)",
    f"{kpis['naive_reported_revenue']:,.0f} đ",
    delta="Bị cộng trùng & chưa trừ trả hàng",
    delta_color="off"
)
col2.metric(
    "Doanh thu ảo bị tính trùng",
    f"-{kpis['phantom_duplicate_revenue']:,.0f} đ",
    delta=f"{val_report['multi_touch_orders_count']} đơn tiếp xúc nhiều CT",
    delta_color="inverse"
)
col3.metric(
    "Hàng trả sau chương trình",
    f"-{kpis['total_returns_value']:,.0f} đ",
    delta="Đã đối soát & trừ khỏi doanh thu",
    delta_color="inverse"
)
col4.metric(
    "Doanh thu thuần thực tế",
    f"{kpis['true_net_revenue']:,.0f} đ",
    delta="Số thực thu chuẩn xác",
    delta_color="normal"
)
col5.metric(
    "Tổng Lợi nhuận đóng góp ròng",
    f"{kpis['total_net_profit']:,.0f} đ",
    delta="Sau giá vốn & tổng chi phí",
    delta_color="normal" if kpis["total_net_profit"] > 0 else "inverse"
)

# ================= TABS KẾT QUẢ PHÂN TÍCH & ĐỀ XUẤT =================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 1. Kết Quả Đánh Giá & Đề Xuất Kinh Doanh",
    "📊 2. Biểu Đồ Trực Quan & Bảng P&L Chi Tiết",
    "🔍 3. Truy Vết Đơn Trùng Lặp & Hàng Trả",
    "✅ 4. Trưởng Phòng Phê Duyệt & Ngân Sách",
    "🤖 5. Chat Hỏi Đáp Cùng AI Agent"
])

# ----------------- TAB 1: KẾT QUẢ & ĐỀ XUẤT KINH DOANH -----------------
with tab1:
    st.subheader("📌 Đề Xuất Quyết Định Kinh Doanh Cho 4 Chương Trình Bán Hàng")
    st.caption("Mỗi kết quả đều được AI Agent truy vết từ đơn hàng gốc, đối soát trả hàng, giá vốn và phân bổ chi phí chung.")

    cols = st.columns(2)
    for idx, row in camp_df.iterrows():
        with cols[idx % 2]:
            status = row["Ma_Trang_Thai"]
            badge_class = (
                "badge-expand" if status == "EXPAND"
                else ("badge-adjust" if status == "ADJUST" else "badge-stop")
            )
            icon = "🟢" if status == "EXPAND" else ("🟡" if status == "ADJUST" else "🔴")

            with st.container(border=True):
                st.markdown(
                    f"#### {icon} {row['Ma_Chuong_Trinh']} — {row['Ten_Chuong_Trinh']}\n"
                    f"<span class='{badge_class}'>{row['Quyet_Dinh_De_Xuat']}</span>",
                    unsafe_allow_html=True
                )
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Báo cáo cũ", f"{row['Doanh_Thu_Bao_Cao_Cu']/1e6:.2f} Tr")
                m2.metric("Doanh thu thuần", f"{row['Doanh_Thu_Thuan']/1e6:.2f} Tr")
                m3.metric("Lợi nhuận ròng", f"{row['Loi_Nhuan_Dong_Gop']/1e6:+.2f} Tr")
                m4.metric("ROI thực tế", f"{row['ROI_Pct']:+.1f}%")

                st.markdown(f"**🔎 Giải thích của AI Agent:** {row['Giai_Thich_AI_Agent']}")
                st.markdown(f"**💡 Đề xuất hành động:** {row['Ke_Hoach_Hanh_Dong']}")
                st.caption(
                    f"Số đơn tiếp xúc: {int(row['So_Don_Tiep_Xuc'])} đơn (Trùng lặp: {int(row['So_Don_Trung_Lap'])} đơn) | "
                    f"Tỷ lệ hoàn trả: {row['Ty_Le_Tra_Hang_Pct']:.1f}% | Chi phí trực tiếp + phân bổ: {row['Tong_Chi_Phi_Van_Hanh_Mkt']:,.0f}đ"
                )

# ----------------- TAB 2: BIỂU ĐỒ & BẢNG P&L CHI TIẾT -----------------
with tab2:
    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown("##### 📉 So sánh: Doanh thu báo cáo cũ (Trùng lặp) vs Doanh thu thuần & Lợi nhuận ròng")
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(
            name="Doanh thu báo cáo cũ (Tính trùng)",
            x=camp_df["Ten_Chuong_Trinh"],
            y=camp_df["Doanh_Thu_Bao_Cao_Cu"],
            marker_color="#94a3b8"
        ))
        fig_rev.add_trace(go.Bar(
            name="Doanh thu thuần (Sau khử trùng & Trả hàng)",
            x=camp_df["Ten_Chuong_Trinh"],
            y=camp_df["Doanh_Thu_Thuan"],
            marker_color="#2563eb"
        ))
        fig_rev.add_trace(go.Bar(
            name="Lợi nhuận đóng góp ròng",
            x=camp_df["Ten_Chuong_Trinh"],
            y=camp_df["Loi_Nhuan_Dong_Gop"],
            marker_color=["#16a34a" if v >= 0 else "#dc2626" for v in camp_df["Loi_Nhuan_Dong_Gop"]]
        ))
        fig_rev.update_layout(barmode="group", height=380, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_rev, use_container_width=True)

    with c_right:
        st.markdown("##### 🎯 Tương quan ROI (%) và Tỷ lệ hoàn trả hàng (%) của 4 Chương trình")
        color_map = {
            "TIẾP TỤC / MỞ RỘNG": "#16a34a",
            "ĐIỀU CHỈNH CƠ CHẾ": "#eab308",
            "DỪNG TRIỂN KHAI": "#dc2626"
        }
        fig_roi = px.bar(
            camp_df,
            x="Ten_Chuong_Trinh",
            y="ROI_Pct",
            color="Quyet_Dinh_De_Xuat",
            color_discrete_map=color_map,
            text=camp_df["ROI_Pct"].map(lambda v: f"{v:+.1f}%"),
            labels={"ROI_Pct": "ROI (%)", "Ten_Chuong_Trinh": "Chương trình"}
        )
        fig_roi.add_hline(y=roi_expand_threshold, line_dash="dash", line_color="green", annotation_text=f"Ngưỡng Mở rộng (+{roi_expand_threshold:.0f}%)")
        fig_roi.add_hline(y=0, line_dash="solid", line_color="red", annotation_text="Điểm hòa vốn (0%)")
        fig_roi.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_roi, use_container_width=True)

    st.markdown("##### 📋 Bảng Báo Cáo Kết Quả Kinh Doanh (P&L) Đầy Đủ Theo Chương Trình")
    display_cols = {
        "Ma_Chuong_Trinh": "Mã CT",
        "Ten_Chuong_Trinh": "Tên Chương Trình",
        "So_Don_Tiep_Xuc": "Số Đơn Tiếp Xúc",
        "So_Don_Trung_Lap": "Đơn Trùng Lặp",
        "Doanh_Thu_Bao_Cao_Cu": "DT Báo Cáo Cũ (VNĐ)",
        "Doanh_Thu_Bi_Tinh_Trung": "DT Ảo Do Trùng (VNĐ)",
        "Gia_Tri_Hang_Tra": "Hàng Trả (VNĐ)",
        "Ty_Le_Tra_Hang_Pct": "Tỷ Lệ Trả (%)",
        "Doanh_Thu_Thuan": "Doanh Thu Thuần (VNĐ)",
        "Gia_Von_Thuc_Te": "Giá Vốn Thực Tế (VNĐ)",
        "Loi_Nhuan_Gop": "Lợi Nhuận Gộp (VNĐ)",
        "Chi_Phi_Truc_Tiep": "Chi Phí Trực Tiếp (VNĐ)",
        "Chi_Phi_Chung_Phan_Bo": "Chi Phí Chung Phân Bổ (VNĐ)",
        "Loi_Nhuan_Dong_Gop": "Lợi Nhuận Đóng Góp (VNĐ)",
        "ROI_Pct": "ROI (%)",
        "Quyet_Dinh_De_Xuat": "Đề Xuất AI Agent"
    }
    st.dataframe(
        camp_df[list(display_cols.keys())].rename(columns=display_cols),
        use_container_width=True,
        hide_index=True
    )

# ----------------- TAB 3: TRUY VẾT ĐƠN TRÙNG LẶP & HÀNG TRẢ -----------------
with tab3:
    st.subheader("🔍 Bằng Chứng Truy Vết: Các Đơn Hàng Tiếp Xúc Nhiều Chương Trình (Khử Trùng Lặp)")
    multi_df = attr_df[attr_df["So_CT_Tiep_Xuc"] > 1].copy()
    st.write(f"Phát hiện **{multi_df['Ma_Don_Hang'].nunique()} đơn hàng** áp dụng đồng thời nhiều chương trình. Dưới đây là cách AI Agent phân bổ lại doanh thu để không bị tính trùng:")
    trace_cols = [
        "Ma_Don_Hang", "Kenh_Ban", "Ma_Chuong_Trinh", "Ten_Chuong_Trinh",
        "Gia_Tri_Giam_Gia", "Ty_Trong_Phan_Bo", "Doanh_Thu_Bao_Cao_Cu_Bi_Trung",
        "Doanh_Thu_Sau_Khu_Trung_Truoc_Tra", "Gia_Tri_Hang_Tra_Phan_Bo"
    ]
    st.dataframe(multi_df[trace_cols], use_container_width=True, hide_index=True)

    st.subheader("📦 Dữ Liệu Đối Soát Hàng Trả Sau Chương Trình")
    st.dataframe(agent.datasets["doi_tra"], use_container_width=True, hide_index=True)

# ----------------- TAB 4: TRƯỞNG PHÒNG PHÊ DUYỆT & NGÂN SÁCH -----------------
with tab4:
    st.subheader("✅ Bước 8 & 9: Trưởng Phòng Kinh Doanh Phê Duyệt & Tái Phân Bổ Ngân Sách")
    st.info("Trưởng phòng Kinh doanh rà soát đề xuất của AI Agent, phê duyệt quyết định cuối cùng và cập nhật kế hoạch ngân sách tháng tới.")

    approval_rows = []
    with st.form("manager_approval_form"):
        for idx, row in camp_df.iterrows():
            c1, c2, c3, c4 = st.columns([2.2, 1.8, 1.5, 2.5])
            with c1:
                st.markdown(f"**{row['Ma_Chuong_Trinh']} - {row['Ten_Chuong_Trinh']}**")
                st.caption(f"ROI thực tế: {row['ROI_Pct']:+.1f}% | Lợi nhuận: {row['Loi_Nhuan_Dong_Gop']:,.0f}đ")
            with c2:
                default_idx = ["TIẾP TỤC / MỞ RỘNG", "ĐIỀU CHỈNH CƠ CHẾ", "DỪNG TRIỂN KHAI"].index(row["Quyet_Dinh_De_Xuat"])
                mgr_decision = st.selectbox(
                    "Quyết định phê duyệt:",
                    options=["TIẾP TỤC / MỞ RỘNG", "ĐIỀU CHỈNH CƠ CHẾ", "DỪNG TRIỂN KHAI"],
                    index=default_idx,
                    key=f"mgr_dec_{row['Ma_Chuong_Trinh']}"
                )
            with c3:
                cur_budget = float(row["Chi_Phi_Truc_Tiep"])
                rec_multiplier = 1.35 if mgr_decision == "TIẾP TỤC / MỞ RỘNG" else (0.85 if mgr_decision == "ĐIỀU CHỈNH CƠ CHẾ" else 0.0)
                new_budget = st.number_input(
                    "Ngân sách trực tiếp kỳ tới (VNĐ):",
                    min_value=0.0,
                    value=float(round(cur_budget * rec_multiplier, -5)),
                    step=500000.0,
                    key=f"mgr_bud_{row['Ma_Chuong_Trinh']}"
                )
            with c4:
                mgr_note = st.text_input(
                    "Chỉ đạo của Trưởng phòng:",
                    value=row["Ke_Hoach_Hanh_Dong"],
                    key=f"mgr_note_{row['Ma_Chuong_Trinh']}"
                )
            approval_rows.append({
                "Ma_Chuong_Trinh": row["Ma_Chuong_Trinh"],
                "Ten_Chuong_Trinh": row["Ten_Chuong_Trinh"],
                "ROI_Hien_Tai_Pct": round(row["ROI_Pct"], 2),
                "Loi_Nhuan_Dong_Gop_VND": round(row["Loi_Nhuan_Dong_Gop"], 0),
                "De_Xuat_AI_Agent": row["Quyet_Dinh_De_Xuat"],
                "Quyet_Dinh_Truong_Phong": mgr_decision,
                "Ngan_Sach_Cu_VND": cur_budget,
                "Ngan_Sach_Moi_Phe_Duyet_VND": new_budget,
                "Chi_Dao_Thuc_Hien": mgr_note
            })

        submitted = st.form_submit_button("💾 Phê Duyệt & Xuất Kế Hoạch Ngân Sách Mới")
        if submitted:
            st.success("🎉 Đã phê duyệt kế hoạch kinh doanh & cập nhật giám sát ngân sách thành công!")

    approval_df = pd.DataFrame(approval_rows)
    st.dataframe(approval_df, use_container_width=True, hide_index=True)

    csv_bytes = approval_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Tải Báo Cáo Phê Duyệt & Kế Hoạch Ngân Sách (.CSV)",
        data=csv_bytes,
        file_name="Bao_Cao_Phe_Duyet_Chuong_Trinh_Gia_Hoa.csv",
        mime="text/csv"
    )

# ----------------- TAB 5: CHAT VỚI AI AGENT -----------------
with tab5:
    st.subheader("🤖 Trợ Lý AI Agent Giải Trình Dữ Liệu Kinh Doanh")
    st.caption("Hỏi đáp trực tiếp về nguyên nhân lãi/lỗ, đơn hàng trùng lặp, tỷ lệ trả hàng hoặc kịch bản phân bổ chi phí.")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": (
                    "Xin chào Trưởng phòng Kinh doanh! Tôi là **AI Agent Đánh giá Hiệu quả Chương trình Bán hàng của Công ty Gia Hòa**.\n\n"
                    "Tôi đã đối soát xong 5 nguồn dữ liệu. Bạn có thể hỏi tôi:\n"
                    "- *'Tại sao CT02 (Flash Deal 30%) có doanh thu báo cáo cao nhất nhưng lại bị đề xuất DỪNG TRIỂN KHAI?'*\n"
                    "- *'Phân tích chi tiết hiệu quả của CT01 (Combo Bếp Ấm Gia Hòa)'*\n"
                    "- *'Vì sao CT03 và CT04 cần ĐIỀU CHỈNH CƠ CHẾ?'*"
                )
            }
        ]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_q = st.chat_input("Nhập câu hỏi cho AI Agent (VD: Tại sao CT02 bị lỗ sau khi trừ hàng trả?)...")
    if user_q:
        st.session_state.chat_messages.append({"role": "user", "content": user_q})
        with st.chat_message("user"):
            st.markdown(user_q)

        ans = agent.answer_business_question(user_q)
        st.session_state.chat_messages.append({"role": "assistant", "content": ans})
        with st.chat_message("assistant"):
            st.markdown(ans)

