import os, re, sys
from dotenv import load_dotenv
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adsinsights import AdsInsights

def normalize_ad_account_id(x: str) -> str:
    x = (x or "").strip()
    if x.startswith("act_"):
        return x
    digits = re.sub(r"[^\d]", "", x)
    return f"act_{digits}" if digits else x

def must(var: str) -> str:
    v = os.getenv(var, "").strip()
    if not v:
        print(f"[ERR] Missing {var} in .env")
        sys.exit(1)
    return v

def main():
    load_dotenv()
    APP_ID = must("FB_APP_ID")
    APP_SECRET = must("FB_APP_SECRET")
    ACCESS_TOKEN = must("FB_ACCESS_TOKEN")
    AD_ACCOUNT_ID = normalize_ad_account_id(must("AD_ACCOUNT_ID"))
    API_VERSION = os.getenv("FB_API_VERSION", "v23.0").strip() or "v23.0"

    print(f"[INFO] Using API {API_VERSION}")
    print(f"[INFO] Ad Account: {AD_ACCOUNT_ID}")

    # Init SDK
    FacebookAdsApi.init(app_id=APP_ID, app_secret=APP_SECRET,
                        access_token=ACCESS_TOKEN, api_version=API_VERSION)

    # 1) Sanity check: read ad account basic info
    try:
        info = AdAccount(AD_ACCOUNT_ID).api_get(fields=["id","name","account_status","currency"])
        print(f"[OK] Access granted → {info['id']} | {info['name']} | status={info['account_status']} | {info['currency']}")
    except Exception as e:
        print("\n[FAIL] Không truy cập được Ad Account.")
        print("      Kiểm tra: AD_ACCOUNT_ID (phải dạng act_<digits>), token & quyền (ads_read/ads_management + business_management),")
        print("      và user/system user có quyền trên ad account.")
        raise

    # 2) Tiny insights pull: today, 5 rows max
    try:
        cur = AdAccount(AD_ACCOUNT_ID).get_insights(
            fields=[
                AdsInsights.Field.date_start,
                AdsInsights.Field.date_stop,
                AdsInsights.Field.account_name,
                AdsInsights.Field.spend,
                AdsInsights.Field.impressions,
                AdsInsights.Field.clicks
            ],
            params={"level": "campaign", "date_preset": "today", "limit": 5}
        )
        rows = [dict(r) for r in cur]
        print(f"[OK] Insights call success. Rows returned: {len(rows)}")
        for r in rows[:3]:
            print("   ", r)
        if not rows:
            print("[NOTE] Không có dữ liệu hôm nay (có thể chưa chi tiêu). Insights vẫn gọi thành công.")
    except Exception as e:
        print("\n[FAIL] Insights call thất bại.")
        print("      Thường do thiếu scope `ads_read` (khuyến nghị) hoặc chưa có quyền trên ad account.")
        raise

    print("\n[PRELIGHT PASSED] Cấu hình & quyền hợp lệ. Bạn có thể chạy script thu thập dữ liệu lớn hơn.")

if __name__ == "__main__":
    main()
