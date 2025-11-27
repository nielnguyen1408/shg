import os, sys, time, argparse
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import pandas as pd

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adsinsights import AdsInsights

API_VERSION = "v23.0"  # có thể đổi khi Meta nâng phiên bản

def init_api(app_id: str, app_secret: str, access_token: str):
    FacebookAdsApi.init(app_id=app_id, app_secret=app_secret,
                        access_token=access_token, api_version=API_VERSION)

def default_fields(level: str) -> List[str]:
    base = [
        AdsInsights.Field.date_start,
        AdsInsights.Field.date_stop,
        AdsInsights.Field.account_id,
        AdsInsights.Field.account_name,
        AdsInsights.Field.campaign_id,
        AdsInsights.Field.campaign_name,
        AdsInsights.Field.adset_id,
        AdsInsights.Field.adset_name,
        AdsInsights.Field.ad_id,
        AdsInsights.Field.ad_name,
        AdsInsights.Field.spend,
        AdsInsights.Field.impressions,
        AdsInsights.Field.reach,
        AdsInsights.Field.clicks,
        AdsInsights.Field.ctr,
        AdsInsights.Field.cpc,
        AdsInsights.Field.cpm,
        AdsInsights.Field.cpp,
        AdsInsights.Field.frequency,
        AdsInsights.Field.actions,        # conversions/clicks by type
        AdsInsights.Field.action_values,  # value by type (e.g., purchase)
    ]
    # Ẩn bớt cột không cần thiết theo level cho gọn
    if level == "account":
        return [f for f in base if f not in
                [AdsInsights.Field.campaign_id, AdsInsights.Field.adset_id, AdsInsights.Field.ad_id,
                 AdsInsights.Field.campaign_name, AdsInsights.Field.adset_name, AdsInsights.Field.ad_name]]
    if level == "campaign":
        return [f for f in base if f not in
                [AdsInsights.Field.adset_id, AdsInsights.Field.ad_id,
                 AdsInsights.Field.adset_name, AdsInsights.Field.ad_name]]
    if level == "adset":
        return [f for f in base if f not in
                [AdsInsights.Field.ad_id, AdsInsights.Field.ad_name]]
    return base  # ad level: giữ tất cả

def parse_breakdowns(bd: Optional[str]) -> List[str]:
    """
    Nhập dạng 'age,gender,country,placement' -> list hợp lệ
    Một số breakdowns phổ biến: age, gender, country, region, dma, impression_device,
    publisher_platform, platform_position, device_platform, placement
    """
    if not bd:
        return []
    return [b.strip() for b in bd.split(",") if b.strip()]

def fetch_insights(
    ad_account_id: str,
    level: str = "campaign",
    fields: Optional[List[str]] = None,
    date_preset: Optional[str] = "last_30d",
    since: Optional[str] = None,
    until: Optional[str] = None,
    time_increment: Optional[int] = None,
    breakdowns: Optional[List[str]] = None,
    limit: int = 1000,
    max_pages: int = 100,
    sleep_sec: float = 0.5,
) -> pd.DataFrame:
    """
    Kéo dữ liệu Insights theo level (account/campaign/adset/ad)
    - date_preset (vd: today, yesterday, last_7d, last_30d, this_month, last_month…)
    - hoặc dùng since/until dạng YYYY-MM-DD
    - time_increment=1 để lấy theo từng ngày
    - breakdowns: list chuỗi breakdown hợp lệ
    """
    acc = AdAccount(ad_account_id)
    params: Dict[str, Any] = {"level": level}
    if date_preset:
        params["date_preset"] = date_preset
    if since and until:
        params["time_range"] = {"since": since, "until": until}
        params.pop("date_preset", None)
    if time_increment:
        params["time_increment"] = time_increment
    if breakdowns:
        params["breakdowns"] = breakdowns

    if not fields:
        fields = default_fields(level)

    all_rows: List[Dict[str, Any]] = []
    cursor = acc.get_insights(fields=fields, params=params)
    pages = 0
    while True:
        for row in cursor:
            all_rows.append(dict(row))
        pages += 1
        if pages >= max_pages or not cursor.load_next_page():
            break
        time.sleep(sleep_sec)  # tránh rate limit nhẹ

    if not all_rows:
        return pd.DataFrame()
    df = pd.DataFrame(all_rows)

    # Chuẩn hoá cột actions/action_values (list of dict) -> cột phẳng
    for col in ["actions", "action_values"]:
        if col in df.columns:
            exploded = (
                df[[col]]
                .applymap(lambda x: x if isinstance(x, list) else [])
                .explode(col)
            )
            if not exploded.empty:
                keyvals = exploded[col].dropna().apply(lambda d: (d.get("action_type"), d.get("value")) if isinstance(d, dict) else (None, None))
                # pivot
                types: Dict[str, float] = {}
                for t, v in keyvals:
                    if t:
                        types[t] = 0.0
                for t in types.keys():
                    df[f"{col}.{t}"] = df[col].apply(
                        lambda lst: next((float(i.get("value", 0)) for i in (lst or []) if i.get("action_type") == t), 0.0)
                        if isinstance(lst, list) else 0.0
                    )
    return df

def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--app_id", default=os.getenv("FB_APP_ID"))
    parser.add_argument("--app_secret", default=os.getenv("FB_APP_SECRET"))
    parser.add_argument("--access_token", default=os.getenv("FB_ACCESS_TOKEN"), help="User/System token")
    parser.add_argument("--ad_account_id", default=os.getenv("AD_ACCOUNT_ID"), help="act_...")
    parser.add_argument("--level", choices=["account","campaign","adset","ad"], default="campaign")
    parser.add_argument("--date_preset", default="last_30d", help="vd: today,yesterday,last_7d,last_30d,this_month,last_month")
    parser.add_argument("--since", help="YYYY-MM-DD", default=None)
    parser.add_argument("--until", help="YYYY-MM-DD", default=None)
    parser.add_argument("--time_increment", type=int, default=None, help="1 = theo ngày")
    parser.add_argument("--breakdowns", default=None, help="vd: age,gender,country,placement")
    parser.add_argument("--out_csv", default="meta_insights.csv")
    args = parser.parse_args()

    required = [args.app_id, args.app_secret, args.access_token, args.ad_account_id]
    if any(not x for x in required):
        print("[ERR] Thiếu app_id/app_secret/access_token/ad_account_id (xem .env hoặc tham số CLI).")
        sys.exit(1)

    init_api(args.app_id, args.app_secret, args.access_token)
    df = fetch_insights(
        ad_account_id=args.ad_account_id,
        level=args.level,
        date_preset=args.date_preset if not args.since else None,
        since=args.since,
        until=args.until,
        time_increment=args.time_increment,
        breakdowns=parse_breakdowns(args.breakdowns),
    )

    if df.empty:
        print("Không có dữ liệu trả về (kiểm tra quyền, khoản thời gian, hoặc ad account).")
        sys.exit(0)

    df.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
    print(f"[OK] Ghi {len(df)} dòng vào: {args.out_csv}")
    # In vài dòng đầu cho xem nhanh
    with pd.option_context("display.max_columns", 0):
        print(df.head(10))

if __name__ == "__main__":
    main()
