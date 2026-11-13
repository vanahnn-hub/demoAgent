"""
AI301 - ĐỀ DỰ ÁN 08: AI AGENT ĐÁNH GIÁ HIỆU QUẢ CHƯƠNG TRÌNH BÁN HÀNG (CÔNG TY GIA HÒA)
Module: agent_engine.py
Mô tả: Pipeline xử lý đa bước theo đúng sơ đồ quy trình (Workflow) của Công ty Gia Hòa.
"""

import re
import io
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import numpy as np

DEFAULT_AGENT_API_KEY = "AQ.Ab8RN6KNYAyjFtmst0jZBg4fx32YRNZLnfu3U1VKee32O7GRVw"


REQUIRED_SCHEMAS = {
    "don_hang": {
        "label": "1. Giao dịch Đơn hàng (Orders)",
        "required_cols": ["Ma_Don_Hang", "Ma_SP", "So_Luong", "Tong_Tien_Niem_Yet"],
        "keywords": ["Ma_Don_Hang", "Tong_Tien_Niem_Yet", "Kenh_Ban"]
    },
    "uu_dai": {
        "label": "2. Sử dụng Ưu đãi (Promo Touchpoints)",
        "required_cols": ["Ma_Don_Hang", "Ma_Chuong_Trinh", "Gia_Tri_Giam_Gia"],
        "keywords": ["Ma_Luot_Uu_Dai", "Thu_Tu_Tiep_Xuc", "Gia_Tri_Giam_Gia"]
    },
    "doi_tra": {
        "label": "3. Đổi trả hàng (Post-campaign Returns)",
        "required_cols": ["Ma_Tra_Hang", "Ma_Don_Hang", "Gia_Tri_Hoan_Tien_Khach"],
        "keywords": ["Ma_Tra_Hang", "Gia_Tri_Hoan_Tien_Khach", "Trang_Thai_Kho"]
    },
    "san_pham": {
        "label": "4. Danh mục Sản phẩm & Giá vốn (Catalog & COGS)",
        "required_cols": ["Ma_SP", "Gia_Von_COGS"],
        "keywords": ["Gia_Von_COGS", "Don_Gia_Niem_Yet"]
    },
    "chi_phi": {
        "label": "5. Chi phí Chương trình & Chi phí chung (Campaign Costs)",
        "required_cols": ["Ma_Chuong_Trinh", "Loai_Chi_Phi", "So_Tien_VND"],
        "keywords": ["Ma_Chi_Phi", "Loai_Chi_Phi", "So_Tien_VND"]
    }
}


def parse_google_sheet_url(url: str) -> str:
    """Chuyển đổi link Google Sheets bất kỳ sang link export CSV trực tiếp."""
    url = url.strip()
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        raise ValueError("Link Google Sheets không hợp lệ. Vui lòng dán link có dạng https://docs.google.com/spreadsheets/d/...")
    sheet_id = match.group(1)
    gid_match = re.search(r"[#&?]gid=([0-9]+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def auto_classify_dataframe(df: pd.DataFrame, filename: str = "") -> Optional[str]:
    """Bước 2: Tự động phân loại bảng dữ liệu dựa trên tên cột."""
    cols = set(df.columns.astype(str).str.strip())
    for key, spec in REQUIRED_SCHEMAS.items():
        if all(c in cols for c in spec["required_cols"]):
            return key
    # Fallback theo từ khóa
    best_key, best_score = None, 0
    for key, spec in REQUIRED_SCHEMAS.items():
        score = sum(1 for c in spec["required_cols"] + spec["keywords"] if c in cols)
        if score > best_score and score >= 2:
            best_key, best_score = key, score
    return best_key


class GiaHoaCampaignAgent:
    """
    AI Agent thực thi quy trình 9 bước đánh giá hiệu quả chương trình bán hàng Công ty Gia Hòa.
    """

    def __init__(self):
        self.datasets: Dict[str, pd.DataFrame] = {}
        self.validation_report: Dict[str, Any] = {}
        self.order_attribution_df: Optional[pd.DataFrame] = None
        self.campaign_metrics_df: Optional[pd.DataFrame] = None
        self.workflow_logs: List[Dict[str, str]] = []

    def log_step(self, step_code: str, step_name: str, status: str, detail: str):
        self.workflow_logs.append({
            "step_code": step_code,
            "step_name": step_name,
            "status": status,
            "detail": detail
        })

    # =========================================================================
    # BƯỚC 1, 2, 3: THU THẬP, PHÂN LOẠI & KIỂM TRA TÍNH HỢP LỆ CỦA DỮ LIỆU
    # =========================================================================
    def validate_and_classify(self, raw_tables: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Kiểm tra xem đã đủ 5 bảng cốt lõi chưa, các cột bắt buộc có hợp lệ không,
        và kiểm tra tính toàn vẹn khóa ngoại (Mã đơn hàng, Mã sản phẩm).
        """
        self.datasets = {}
        missing_tables = []
        schema_errors = []
        warnings = []

        for name, df in raw_tables.items():
            df = df.copy()
            df.columns = df.columns.astype(str).str.strip()
            table_type = name if name in REQUIRED_SCHEMAS else auto_classify_dataframe(df, name)
            if table_type:
                self.datasets[table_type] = df

        for key, spec in REQUIRED_SCHEMAS.items():
            if key not in self.datasets:
                missing_tables.append(f"Thiếu bảng dữ liệu: {spec['label']}")
            else:
                df = self.datasets[key]
                missing_cols = [c for c in spec["required_cols"] if c not in df.columns]
                if missing_cols:
                    schema_errors.append(
                        f"Bảng {spec['label']} thiếu các cột bắt buộc: {', '.join(missing_cols)}"
                    )
                if len(df) == 0:
                    schema_errors.append(f"Bảng {spec['label']} đang rỗng (0 dòng).")

        is_valid = (len(missing_tables) == 0) and (len(schema_errors) == 0)

        # Kiểm tra chéo khóa ngoại nếu đủ bảng
        multi_touch_orders_count = 0
        unmatched_returns = 0
        if is_valid:
            orders_df = self.datasets["don_hang"]
            promo_df = self.datasets["uu_dai"]
            returns_df = self.datasets["doi_tra"]
            prod_df = self.datasets["san_pham"]

            touch_counts = promo_df.groupby("Ma_Don_Hang")["Ma_Chuong_Trinh"].nunique()
            multi_touch_orders_count = int((touch_counts > 1).sum())
            if multi_touch_orders_count > 0:
                warnings.append(
                    f"Phát hiện {multi_touch_orders_count} đơn hàng tiếp xúc từ 2-3 chương trình cùng lúc -> Cần chạy bước Khử trùng lặp doanh thu."
                )

            valid_orders = set(orders_df["Ma_Don_Hang"].unique())
            orphan_returns = set(returns_df["Ma_Don_Hang"].unique()) - valid_orders
            unmatched_returns = len(orphan_returns)
            if unmatched_returns > 0:
                warnings.append(
                    f"Có {unmatched_returns} mã đơn trong tệp Đổi trả không tìm thấy trong tệp Đơn hàng: {', '.join(orphan_returns)}"
                )

            missing_sp = set(orders_df["Ma_SP"].unique()) - set(prod_df["Ma_SP"].unique())
            if missing_sp:
                schema_errors.append(
                    f"Mã sản phẩm trong đơn hàng chưa có Giá vốn (COGS) trong Danh mục SP: {', '.join(missing_sp)}"
                )
                is_valid = False

        self.validation_report = {
            "is_valid": is_valid,
            "missing_tables": missing_tables,
            "schema_errors": schema_errors,
            "warnings": warnings,
            "multi_touch_orders_count": multi_touch_orders_count,
            "summary": (
                "Dữ liệu hợp lệ & đầy đủ 5 nguồn. Sẵn sàng chuẩn hóa & khử trùng lặp."
                if is_valid
                else "Dữ liệu chưa hợp lệ hoặc thiếu thông tin. Cần bổ sung/làm rõ trước khi tính toán."
            )
        }

        self.log_step(
            "STEP_2_3",
            "Phân loại & Kiểm tra thông tin",
            "SUCCESS" if is_valid else "ERROR",
            self.validation_report["summary"]
        )
        return self.validation_report

    # =========================================================================
    # BƯỚC 4, 5, 6, 7: PIPELINE TÍNH TOÁN & ĐÁNH GIÁ CHƯƠNG TRÌNH BÁN HÀNG
    # =========================================================================
    def run_evaluation_pipeline(
        self,
        attribution_rule: str = "TY_TRONG_UU_DAI",
        shared_cost_rule: str = "THEO_DOANH_THU_THUAN",
        roi_expand_threshold: float = 30.0,
        roi_stop_threshold: float = 0.0,
        max_return_rate_expand: float = 8.0
    ) -> Dict[str, Any]:
        """
        Thực thi toàn bộ luồng xử lý từ Bước 4 đến Bước 7:
        - Bước 4: Chuẩn hóa & Khử trùng lặp doanh thu (Multi-touch Attribution)
        - Bước 5: Đối soát hàng trả (Returns) & Phân bổ chi phí chung (Cost Allocation)
        - Bước 6: Tính toán chỉ số thực tế (Doanh thu thuần, Lợi nhuận gộp, Lợi nhuận đóng góp, ROI)
        - Bước 7: Đánh giá theo tiêu chuẩn kinh doanh & Đề xuất (Tiếp tục / Điều chỉnh / Dừng)
        """
        if not self.validation_report or not self.validation_report.get("is_valid"):
            raise ValueError("Dữ liệu chưa vượt qua bước kiểm tra hợp lệ.")

        orders = self.datasets["don_hang"].copy()
        promos = self.datasets["uu_dai"].copy()
        returns = self.datasets["doi_tra"].copy()
        products = self.datasets["san_pham"].copy()
        costs = self.datasets["chi_phi"].copy()

        # Ép kiểu số an toàn
        for col in ["So_Luong", "Tong_Tien_Niem_Yet", "Tong_Giam_Gia"]:
            orders[col] = pd.to_numeric(orders[col], errors="coerce").fillna(0.0)
        promos["Gia_Tri_Giam_Gia"] = pd.to_numeric(promos["Gia_Tri_Giam_Gia"], errors="coerce").fillna(0.0)
        if "Thu_Tu_Tiep_Xuc" not in promos.columns:
            promos["Thu_Tu_Tiep_Xuc"] = 1
        else:
            promos["Thu_Tu_Tiep_Xuc"] = pd.to_numeric(promos["Thu_Tu_Tiep_Xuc"], errors="coerce").fillna(1)

        for col in ["So_Luong_Tra", "Gia_Tri_Hoan_Tien_Khach"]:
            returns[col] = pd.to_numeric(returns[col], errors="coerce").fillna(0.0)
        if "Phi_Xu_Ly_Va_Hao_Hut" not in returns.columns:
            returns["Phi_Xu_Ly_Va_Hao_Hut"] = 0.0
        else:
            returns["Phi_Xu_Ly_Va_Hao_Hut"] = pd.to_numeric(returns["Phi_Xu_Ly_Va_Hao_Hut"], errors="coerce").fillna(0.0)

        products["Gia_Von_COGS"] = pd.to_numeric(products["Gia_Von_COGS"], errors="coerce").fillna(0.0)
        costs["So_Tien_VND"] = pd.to_numeric(costs["So_Tien_VND"], errors="coerce").fillna(0.0)

        # Kết nối Giá vốn (COGS) vào Đơn hàng
        orders = orders.merge(products[["Ma_SP", "Ten_SP", "Nhom_Hang", "Gia_Von_COGS"]], on="Ma_SP", how="left")
        orders["Tong_Gia_Von_Ban_Dau"] = orders["So_Luong"] * orders["Gia_Von_COGS"]
        orders["Doanh_Thu_Thuc_Thu_Truoc_Tra"] = orders["Tong_Tien_Niem_Yet"] - orders["Tong_Giam_Gia"]

        # Tổng hợp Hàng trả theo Mã Đơn Hàng
        returns_merged = returns.merge(products[["Ma_SP", "Gia_Von_COGS"]], on="Ma_SP", how="left")
        if "Tinh_Trang_Hang_Tra" not in returns_merged.columns:
            returns_merged["Tinh_Trang_Hang_Tra"] = "Nhap_Lai_Kho"

        # Nếu hàng trả nhập lại kho (Nhap_Lai_Kho) thì hoàn nhập được Giá vốn COGS.
        # Nếu hàng hỏng/hao hụt (Hong_Hao_Hut) thì không hoàn nhập được COGS (mất vốn hàng đó).
        returns_merged["Gia_Von_Thu_Hoi_Duoc"] = np.where(
            returns_merged["Tinh_Trang_Hang_Tra"].astype(str).str.contains("Nhap_Lai_Kho", case=False, na=False),
            returns_merged["So_Luong_Tra"] * returns_merged["Gia_Von_COGS"],
            0.0
        )

        order_returns = returns_merged.groupby("Ma_Don_Hang", as_index=False).agg({
            "So_Luong_Tra": "sum",
            "Gia_Tri_Hoan_Tien_Khach": "sum",
            "Phi_Xu_Ly_Va_Hao_Hut": "sum",
            "Gia_Von_Thu_Hoi_Duoc": "sum"
        })

        orders = orders.merge(order_returns, on="Ma_Don_Hang", how="left")
        for col in ["So_Luong_Tra", "Gia_Tri_Hoan_Tien_Khach", "Phi_Xu_Ly_Va_Hao_Hut", "Gia_Von_Thu_Hoi_Duoc"]:
            orders[col] = orders[col].fillna(0.0)

        # ---------------------------------------------------------------------
        # BƯỚC 4: CHUẨN HÓA & KHỬ TRÙNG LẶP DOANH THU (ATTRIBUTION)
        # ---------------------------------------------------------------------
        promo_orders = promos.merge(orders, on="Ma_Don_Hang", how="inner")

        # Tính tổng giảm giá và số chương trình tiếp xúc trên mỗi đơn
        order_promo_stats = promo_orders.groupby("Ma_Don_Hang").agg(
            Tong_Giam_Gia_Don=("Gia_Tri_Giam_Gia", "sum"),
            So_CT_Tiep_Xuc=("Ma_Chuong_Trinh", "count"),
            Min_Touch=("Thu_Tu_Tiep_Xuc", "min"),
            Max_Touch=("Thu_Tu_Tiep_Xuc", "max")
        ).reset_index()

        promo_orders = promo_orders.merge(order_promo_stats, on="Ma_Don_Hang", how="left")

        # Xác định trọng số phân bổ (Weight) cho từng chương trình trong mỗi đơn hàng
        if attribution_rule == "CHIA_DEU_LINEAR":
            promo_orders["Ty_Trong_Phan_Bo"] = 1.0 / promo_orders["So_CT_Tiep_Xuc"]
        elif attribution_rule == "FIRST_TOUCH":
            is_first = promo_orders["Thu_Tu_Tiep_Xuc"] == promo_orders["Min_Touch"]
            first_counts = is_first.groupby(promo_orders["Ma_Don_Hang"]).transform("sum")
            promo_orders["Ty_Trong_Phan_Bo"] = np.where(is_first, 1.0 / first_counts, 0.0)
        elif attribution_rule == "LAST_TOUCH":
            is_last = promo_orders["Thu_Tu_Tiep_Xuc"] == promo_orders["Max_Touch"]
            last_counts = is_last.groupby(promo_orders["Ma_Don_Hang"]).transform("sum")
            promo_orders["Ty_Trong_Phan_Bo"] = np.where(is_last, 1.0 / last_counts, 0.0)
        else:
            # Mặc định: TY_TRONG_UU_DAI (Phân bổ theo tỷ trọng mức giảm giá đóng góp)
            promo_orders["Ty_Trong_Phan_Bo"] = np.where(
                promo_orders["Tong_Giam_Gia_Don"] > 0,
                promo_orders["Gia_Tri_Giam_Gia"] / promo_orders["Tong_Giam_Gia_Don"],
                1.0 / promo_orders["So_CT_Tiep_Xuc"]
            )

        # Doanh thu báo cáo cũ (bị tính trùng 100% doanh thu đơn cho mỗi chương trình tiếp xúc, chưa trừ hàng trả)
        promo_orders["Doanh_Thu_Bao_Cao_Cu_Bi_Trung"] = promo_orders["Doanh_Thu_Thuc_Thu_Truoc_Tra"]
        promo_orders["Doanh_Thu_Niem_Yet_Bao_Cao_Cu"] = promo_orders["Tong_Tien_Niem_Yet"]

        # Doanh thu và chỉ số sau khi phân bổ khử trùng lặp theo Ty_Trong_Phan_Bo
        promo_orders["So_Don_Quy_Doi"] = promo_orders["Ty_Trong_Phan_Bo"]
        promo_orders["Doanh_Thu_Niem_Yet_Phan_Bo"] = promo_orders["Tong_Tien_Niem_Yet"] * promo_orders["Ty_Trong_Phan_Bo"]
        promo_orders["Chiet_Khau_Truc_Tiep"] = promo_orders["Gia_Tri_Giam_Gia"]
        promo_orders["Doanh_Thu_Sau_Khu_Trung_Truoc_Tra"] = (
            promo_orders["Doanh_Thu_Niem_Yet_Phan_Bo"] - promo_orders["Chiet_Khau_Truc_Tiep"]
        )

        # ---------------------------------------------------------------------
        # BƯỚC 5: ĐỐI SOÁT HÀNG TRẢ & PHÂN BỔ CHI PHÍ CHUNG
        # ---------------------------------------------------------------------
        promo_orders["Gia_Tri_Hang_Tra_Phan_Bo"] = (
            promo_orders["Gia_Tri_Hoan_Tien_Khach"] * promo_orders["Ty_Trong_Phan_Bo"]
        )
        promo_orders["Phi_Hao_Hut_Hoan_Hang_Phan_Bo"] = (
            promo_orders["Phi_Xu_Ly_Va_Hao_Hut"] * promo_orders["Ty_Trong_Phan_Bo"]
        )
        promo_orders["Gia_Von_Thuc_Te_Phan_Bo"] = (
            (promo_orders["Tong_Gia_Von_Ban_Dau"] - promo_orders["Gia_Von_Thu_Hoi_Duoc"])
            * promo_orders["Ty_Trong_Phan_Bo"]
        )

        self.order_attribution_df = promo_orders

        # Nhóm theo Chương trình bán hàng
        camp_df = promo_orders.groupby(["Ma_Chuong_Trinh", "Ten_Chuong_Trinh"], as_index=False).agg(
            So_Don_Tiep_Xuc=("Ma_Don_Hang", "nunique"),
            So_Don_Trung_Lap=("So_CT_Tiep_Xuc", lambda s: int((s > 1).sum())),
            So_Don_Quy_Doi=("So_Don_Quy_Doi", "sum"),
            Doanh_Thu_Bao_Cao_Cu=("Doanh_Thu_Bao_Cao_Cu_Bi_Trung", "sum"),
            Doanh_Thu_Niem_Yet_Phan_Bo=("Doanh_Thu_Niem_Yet_Phan_Bo", "sum"),
            Chiet_Khau_Uu_Dai=("Chiet_Khau_Truc_Tiep", "sum"),
            Doanh_Thu_Sau_Khu_Trung=("Doanh_Thu_Sau_Khu_Trung_Truoc_Tra", "sum"),
            Gia_Tri_Hang_Tra=("Gia_Tri_Hang_Tra_Phan_Bo", "sum"),
            Phi_Xu_Ly_Hang_Tra=("Phi_Hao_Hut_Hoan_Hang_Phan_Bo", "sum"),
            Gia_Von_Thuc_Te=("Gia_Von_Thuc_Te_Phan_Bo", "sum")
        )

        # Doanh thu bị thổi phồng do tính trùng (Phantom Revenue)
        camp_df["Doanh_Thu_Bi_Tinh_Trung"] = camp_df["Doanh_Thu_Bao_Cao_Cu"] - camp_df["Doanh_Thu_Sau_Khu_Trung"]

        # Doanh thu thuần thực tế (Net Revenue) = Doanh thu sau khử trùng - Giá trị hoàn tiền hàng trả
        camp_df["Doanh_Thu_Thuan"] = camp_df["Doanh_Thu_Sau_Khu_Trung"] - camp_df["Gia_Tri_Hang_Tra"]

        # Tỷ lệ trả hàng (%) = Giá trị hàng trả / Doanh thu sau khử trùng
        camp_df["Ty_Le_Tra_Hang_Pct"] = np.where(
            camp_df["Doanh_Thu_Sau_Khu_Trung"] > 0,
            (camp_df["Gia_Tri_Hang_Tra"] / camp_df["Doanh_Thu_Sau_Khu_Trung"]) * 100.0,
            0.0
        )

        # Lợi nhuận gộp (Gross Profit) = Doanh thu thuần - Giá vốn thực tế - Phí xử lý/hao hụt hàng trả
        camp_df["Loi_Nhuan_Gop"] = (
            camp_df["Doanh_Thu_Thuan"] - camp_df["Gia_Von_Thuc_Te"] - camp_df["Phi_Xu_Ly_Hang_Tra"]
        )

        # Kết nối Chi phí trực tiếp và Chi phí chung
        direct_costs = (
            costs[costs["Loai_Chi_Phi"].astype(str).str.contains("Truc_Tiep", case=False, na=False)]
            .groupby("Ma_Chuong_Trinh", as_index=False)["So_Tien_VND"]
            .sum()
            .rename(columns={"So_Tien_VND": "Chi_Phi_Truc_Tiep"})
        )
        total_shared_cost = float(
            costs[costs["Loai_Chi_Phi"].astype(str).str.contains("Chi_Phi_Chung|Chung", case=False, na=False)]["So_Tien_VND"].sum()
        )

        camp_df = camp_df.merge(direct_costs, on="Ma_Chuong_Trinh", how="left")
        camp_df["Chi_Phi_Truc_Tiep"] = camp_df["Chi_Phi_Truc_Tiep"].fillna(0.0)

        # Phân bổ chi phí chung nhất quán
        if shared_cost_rule == "THEO_SO_DON_QUY_DOI":
            total_orders_eq = camp_df["So_Don_Quy_Doi"].sum()
            camp_df["Chi_Phi_Chung_Phan_Bo"] = (
                (camp_df["So_Don_Quy_Doi"] / total_orders_eq) * total_shared_cost
                if total_orders_eq > 0 else total_shared_cost / len(camp_df)
            )
        elif shared_cost_rule == "CHIA_DEU":
            camp_df["Chi_Phi_Chung_Phan_Bo"] = total_shared_cost / len(camp_df)
        else:
            # Mặc định: THEO_DOANH_THU_THUAN
            total_net_rev = camp_df["Doanh_Thu_Thuan"].clip(lower=0).sum()
            camp_df["Chi_Phi_Chung_Phan_Bo"] = (
                (camp_df["Doanh_Thu_Thuan"].clip(lower=0) / total_net_rev) * total_shared_cost
                if total_net_rev > 0 else total_shared_cost / len(camp_df)
            )

        # ---------------------------------------------------------------------
        # BƯỚC 6: TÍNH TOÁN CHỈ SỐ THỰC TẾ (LỢI NHUẬN ĐÓNG GÓP & ROI)
        # ---------------------------------------------------------------------
        camp_df["Tong_Chi_Phi_Van_Hanh_Mkt"] = camp_df["Chi_Phi_Truc_Tiep"] + camp_df["Chi_Phi_Chung_Phan_Bo"]
        camp_df["Tong_Ngan_Sach_Tieu_ao"] = camp_df["Tong_Chi_Phi_Van_Hanh_Mkt"] + camp_df["Chiet_Khau_Uu_Dai"]

        # Lợi nhuận đóng góp ròng (Net Contribution Margin)
        camp_df["Loi_Nhuan_Dong_Gop"] = camp_df["Loi_Nhuan_Gop"] - camp_df["Tong_Chi_Phi_Van_Hanh_Mkt"]

        # Biên lợi nhuận đóng góp / Doanh thu thuần (%)
        camp_df["Bien_Loi_Nhuan_Rong_Pct"] = np.where(
            camp_df["Doanh_Thu_Thuan"] > 0,
            (camp_df["Loi_Nhuan_Dong_Gop"] / camp_df["Doanh_Thu_Thuan"]) * 100.0,
            0.0
        )

        # ROI (%) = Lợi nhuận đóng góp / (Chi phí trực tiếp + Chi phí chung phân bổ) * 100
        camp_df["ROI_Pct"] = np.where(
            camp_df["Tong_Chi_Phi_Van_Hanh_Mkt"] > 0,
            (camp_df["Loi_Nhuan_Dong_Gop"] / camp_df["Tong_Chi_Phi_Van_Hanh_Mkt"]) * 100.0,
            0.0
        )

        # ---------------------------------------------------------------------
        # BƯỚC 7: ĐÁNH GIÁ THEO TIÊU CHUẨN KINH DOANH & GIẢI THÍCH KẾT QUẢ
        # ---------------------------------------------------------------------
        decisions = []
        status_Codes = []
        explanations = []
        action_plans = []

        for _, row in camp_df.iterrows():
            roi = row["ROI_Pct"]
            net_profit = row["Loi_Nhuan_Dong_Gop"]
            ret_rate = row["Ty_Le_Tra_Hang_Pct"]
            phantom_rev = row["Doanh_Thu_Bi_Tinh_Trung"]
            overlap_cnt = row["So_Don_Trung_Lap"]
            discount_ratio = (
                (row["Chiet_Khau_Uu_Dai"] / row["Doanh_Thu_Niem_Yet_Phan_Bo"] * 100.0)
                if row["Doanh_Thu_Niem_Yet_Phan_Bo"] > 0 else 0.0
            )

            if net_profit < 0 or roi < roi_stop_threshold or ret_rate >= 15.0:
                decisions.append("DỪNG TRIỂN KHAI")
                status_Codes.append("STOP")
                explanations.append(
                    f"Báo cáo cũ ghi nhận doanh thu {row['Doanh_Thu_Bao_Cao_Cu']:,.0f}đ, nhưng có tới {overlap_cnt}/{int(row['So_Don_Tiep_Xuc'])} đơn bị tính trùng ({phantom_rev:,.0f}đ doanh thu ảo). "
                    f"Sau khi trừ hàng trả ({row['Gia_Tri_Hang_Tra']:,.0f}đ - tỷ lệ trả {ret_rate:.1f}%), chiết khấu sâu ({discount_ratio:.1f}%) và chi phí ({row['Tong_Chi_Phi_Van_Hanh_Mkt']:,.0f}đ), "
                    f"chương trình bị LỖ RÒNG {abs(net_profit):,.0f}đ (ROI: {roi:.1f}%)."
                )
                action_plans.append(
                    "Dừng ngay chương trình để cắt lỗ; thu hồi ngân sách quảng cáo chuyển sang chương trình có ROI cao; rà soát chất lượng đóng gói & mô tả sản phẩm điện gia dụng để giảm hoàn trả."
                )
            elif roi >= roi_expand_threshold and ret_rate <= max_return_rate_expand:
                decisions.append("TIẾP TỤC / MỞ RỘNG")
                status_Codes.append("EXPAND")
                explanations.append(
                    f"Hiệu quả thực tế xuất sắc: Doanh thu thuần đạt {row['Doanh_Thu_Thuan']:,.0f}đ, tỷ lệ trả hàng rất thấp ({ret_rate:.1f}%), "
                    f"tạo ra Lợi nhuận đóng góp dương cao +{net_profit:,.0f}đ với ROI đạt +{roi:.1f}% (vượt ngưỡng chuẩn {roi_expand_threshold:.0f}%)."
                )
                action_plans.append(
                    "Tiếp tục triển khai và mở rộng quy mô (+25% đến +40% ngân sách từ khoản cắt giảm của chương trình lỗ); nhân rộng mô hình Combo sang các nhóm sản phẩm nhà bếp khác."
                )
            else:
                decisions.append("ĐIỀU CHỈNH CƠ CHẾ")
                status_Codes.append("ADJUST")
                issue_detail = (
                    f"Có tới {overlap_cnt} đơn bị cộng dồn mã (stacking) với chương trình khác làm tăng chi phí chiết khấu"
                    if overlap_cnt >= 4
                    else f"Chi phí trực tiếp & quà tặng đang chiếm tỷ trọng cao ({row['Chi_Phi_Truc_Tiep']:,.0f}đ) làm kìm hãm biên lợi nhuận"
                )
                explanations.append(
                    f"Chương trình có Lợi nhuận đóng góp dương (+{net_profit:,.0f}đ) và tỷ lệ trả hàng kiểm soát tốt ({ret_rate:.1f}%), "
                    f"nhưng ROI mới đạt +{roi:.1f}% (chưa đạt ngưỡng mở rộng {roi_expand_threshold:.0f}%). Nguyên nhân chính: {issue_detail}."
                )
                action_plans.append(
                    "Điều chỉnh cơ chế: Chặn cộng dồn (stacking) mã ưu đãi với chương trình giảm sâu >20%; nâng giá trị đơn hàng tối thiểu (Min Order Value) hoặc tối ưu định mức chi phí trực tiếp/quà tặng tại điểm bán."
                )

        camp_df["Quyet_Dinh_De_Xuat"] = decisions
        camp_df["Ma_Trang_Thai"] = status_Codes
        camp_df["Giai_Thich_AI_Agent"] = explanations
        camp_df["Ke_Hoach_Hanh_Dong"] = action_plans

        self.campaign_metrics_df = camp_df.sort_values("Ma_Chuong_Trinh").reset_index(drop=True)

        # Tổng hợp toàn công ty để đối chiếu
        naive_total_rev = float(camp_df["Doanh_Thu_Bao_Cao_Cu"].sum())
        true_net_rev = float(camp_df["Doanh_Thu_Thuan"].sum())
        total_phantom = float(camp_df["Doanh_Thu_Bi_Tinh_Trung"].sum())
        total_returns = float(camp_df["Gia_Tri_Hang_Tra"].sum())
        total_net_profit = float(camp_df["Loi_Nhuan_Dong_Gop"].sum())

        return {
            "campaign_metrics": self.campaign_metrics_df,
            "order_attribution": self.order_attribution_df,
            "summary_kpis": {
                "naive_reported_revenue": naive_total_rev,
                "true_net_revenue": true_net_rev,
                "phantom_duplicate_revenue": total_phantom,
                "total_returns_value": total_returns,
                "total_net_profit": total_net_profit,
                "total_shared_cost": total_shared_cost
            }
        }

    def answer_business_question(self, question: str) -> str:
        """
        Trợ lý AI Agent trả lời câu hỏi truy vết dữ liệu trực tiếp dựa trên kết quả tính toán.
        """
        if self.campaign_metrics_df is None:
            return "Vui lòng nạp dữ liệu để Agent chạy quy trình đánh giá trước khi đặt câu hỏi."

        q_lower = question.lower()
        df = self.campaign_metrics_df

        # Nếu hỏi về một chương trình cụ thể (CT01, CT02, CT03, CT04)
        for _, row in df.iterrows():
            code = str(row["Ma_Chuong_Trinh"]).lower()
            name = str(row["Ten_Chuong_Trinh"]).lower()
            if code in q_lower or any(w in q_lower for w in name.split() if len(w) > 3):
                return (
                    f"**Phân tích chi tiết {row['Ma_Chuong_Trinh']} - {row['Ten_Chuong_Trinh']}:**\n"
                    f"- **Doanh thu báo cáo ban đầu (chưa khử trùng):** `{row['Doanh_Thu_Bao_Cao_Cu']:,.0f} VNĐ` ({int(row['So_Don_Tiep_Xuc'])} đơn tiếp xúc, trong đó `{int(row['So_Don_Trung_Lap'])}` đơn trùng lặp).\n"
                    f"- **Doanh thu ảo do tính trùng:** `-{row['Doanh_Thu_Bi_Tinh_Trung']:,.0f} VNĐ`\n"
                    f"- **Giá trị hàng trả sau chương trình:** `-{row['Gia_Tri_Hang_Tra']:,.0f} VNĐ` (Tỷ lệ trả: `{row['Ty_Le_Tra_Hang_Pct']:.1f}%`)\n"
                    f"- **Doanh thu thuần thực tế:** `{row['Doanh_Thu_Thuan']:,.0f} VNĐ`\n"
                    f"- **Giá vốn thực tế & Phí hoàn hàng:** `-{row['Gia_Von_Thuc_Te'] + row['Phi_Xu_Ly_Hang_Tra']:,.0f} VNĐ`\n"
                    f"- **Lợi nhuận gộp:** `{row['Loi_Nhuan_Gop']:,.0f} VNĐ`\n"
                    f"- **Chi phí trực tiếp + Chi phí chung phân bổ:** `-{row['Chi_Phi_Truc_Tiep']:,.0f}đ` + `-{row['Chi_Phi_Chung_Phan_Bo']:,.0f}đ` = `-{row['Tong_Chi_Phi_Van_Hanh_Mkt']:,.0f} VNĐ`\n"
                    f"- **Lợi nhuận đóng góp ròng:** `{row['Loi_Nhuan_Dong_Gop']:,.0f} VNĐ` (**ROI: `{row['ROI_Pct']:.1f}%`**)\n"
                    f"- **Đề xuất của AI Agent:** **{row['Quyet_Dinh_De_Xuat']}** — {row['Giai_Thich_AI_Agent']}\n"
                    f"- **Hành động cụ thể:** {row['Ke_Hoach_Hanh_Dong']}"
                )

        # Tổng quan so sánh 4 chương trình
        lines = ["**Tổng hợp kết quả đánh giá 4 chương trình bán hàng Công ty Gia Hòa:**\n"]
        for _, row in df.iterrows():
            lines.append(
                f"1. **{row['Ma_Chuong_Trinh']} ({row['Ten_Chuong_Trinh']})**: "
                f"Báo cáo cũ `{row['Doanh_Thu_Bao_Cao_Cu']:,.0f}đ` → Doanh thu thuần `{row['Doanh_Thu_Thuan']:,.0f}đ` | "
                f"Lợi nhuận đóng góp: `{row['Loi_Nhuan_Dong_Gop']:,.0f}đ` | ROI: `{row['ROI_Pct']:.1f}%` | "
                f"Đề xuất: **{row['Quyet_Dinh_De_Xuat']}**"
            )
        lines.append(
            "\n💡 *Gợi ý:* Bạn có thể hỏi sâu về từng chương trình (ví dụ: 'Tại sao CT02 doanh thu cao nhưng bị đề xuất Dừng?', 'Chi tiết đơn trùng lặp của CT03')."
        )
        return "\n".join(lines)

