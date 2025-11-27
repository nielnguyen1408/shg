//+------------------------------------------------------------------+
//|                                         m1fvg_v5_fix.mq5        |
//| FVG 3 nến + pending limit, anti-hedge, entry EDGE/MID, SL extra |
//+------------------------------------------------------------------+
#property strict
#include <Trade/Trade.mqh>

//============================ Inputs ===============================
input ENUM_TIMEFRAMES   WorkTF         = PERIOD_M1;
input bool              UseEMATrend    = true;
input int               FastEMA        = 50;
input int               SlowEMA        = 200;

input int               LookbackBars   = 1500;
input color             BullFVGColor   = clrLime;
input color             BearFVGColor   = clrTomato;
input int               RectWidth      = 1;
input ENUM_LINE_STYLE   RectStyle      = STYLE_SOLID;
input uchar             RectOpacity    = 40;

input bool              MarkPreRange   = true;
input int               RangeWindow    = 10;
input int               ATRPeriod      = 14;
input double            RangeATRMult   = 0.6;
input color             RangeColor     = clrSilver;

//========================= Trading Inputs ==========================
input bool              EnableTrading   = true;
input bool              AllowLong       = true;
input bool              AllowShort      = true;
input bool              OnlyWithTrend   = false;
input ulong             Magic           = 20251103;
input int               DeviationPoints = 30;     // chỉ áp dụng cho market orders
input int               MaxPositions    = 1;      // số vị thế MỞ tối đa (không tính pending)

// Khối lượng & rủi ro
input bool              UseRiskPercent  = true;
input double            RiskPercent     = 1.0;
input double            FixedLots       = 0.10;

// SL/TP
input double            StopBufferPts   = 5;      // buffer từ mốc nến B
input int               SLExtraPts      = 12;     // bù spread
input bool              UseRR           = true;
input double            RR              = 2.0;
input int               TPPoints        = 100;

// Entry mode: EDGE (mép FVG) hoặc MID (giữa vùng FVG)
enum ENTRY_PRICE_MODE { ENTRY_EDGE=0, ENTRY_MID=1 };
input ENTRY_PRICE_MODE  EntryMode       = ENTRY_EDGE;

// Anti-hedge theo vùng FVG gần nhất
input bool              EnforceNoHedge     = true; // bật chặn lệnh ngược chiều
input int               ZoneBreakBufferPts = 2;    // biên độ phụ (points) khi xét “thủng”

//=========================== Globals ===============================
CTrade     trade;
int        atrHandle     = INVALID_HANDLE;
int        emaFastHandle = INVALID_HANDLE;
int        emaSlowHandle = INVALID_HANDLE;
datetime   lastBarTime   = 0;
datetime   EAStartBarTime = 0;

// Lưu vùng FVG gần nhất cho mỗi hướng
bool       hasBullZone=false, hasBearZone=false;
// Bullish zone: [bottom=HA .. top=LC]
double     bullTop=0.0, bullBottom=0.0;
// Bearish zone: [bottom=LA .. top=HC]
double     bearTop=0.0, bearBottom=0.0;

//=========================== Helpers ===============================
color ColorWithAlpha(color base, uchar alpha){ return (color)ColorToARGB(base, alpha); }

bool IsNewBar(){
   datetime t0 = iTime(_Symbol, WorkTF, 0);
   if(t0 == lastBarTime) return false;
   lastBarTime = t0; return true;
}

string TFToString(ENUM_TIMEFRAMES tf){
   switch(tf){
      case PERIOD_M1: return "M1"; case PERIOD_M5: return "M5"; case PERIOD_M15: return "M15";
      case PERIOD_M30: return "M30"; case PERIOD_H1: return "H1"; case PERIOD_H4: return "H4";
      case PERIOD_D1: return "D1"; case PERIOD_W1: return "W1"; case PERIOD_MN1: return "MN1";
      default: return "TF";
   }
}

string RectName(const string prefix, datetime tA, datetime tC){
   return StringFormat("%s_%s_%s_%I64d_%I64d", prefix, _Symbol, TFToString(WorkTF), (long)tA, (long)tC);
}

void DrawRect(const string name, datetime tA, double priceTop, datetime tC, double priceBot, color c)
{
   double top = MathMax(priceTop, priceBot);
   double bot = MathMin(priceTop, priceBot);
   if(ObjectFind(0, name) == -1)
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, tA, top, tC, bot);

   color drawColor = (RectOpacity < 255) ? ColorWithAlpha(c, RectOpacity) : c;
   ObjectSetInteger(0, name, OBJPROP_COLOR,   (long)drawColor);
   ObjectSetInteger(0, name, OBJPROP_STYLE,   (long)RectStyle);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,   (long)RectWidth);
   ObjectSetInteger(0, name, OBJPROP_BACK,    true);
   ObjectSetInteger(0, name, OBJPROP_FILL,    true);
   ObjectSetInteger(0, name, OBJPROP_ZORDER,  0);

   ObjectMove(0, name, 0, tA, top);
   ObjectMove(0, name, 1, tC, bot);
}

bool GetEMATrend(int shift, int &trend){
   if(!UseEMATrend){ trend=0; return true; }
   double f[], s[];
   if(CopyBuffer(emaFastHandle, 0, shift, 1, f) <= 0) return false;
   if(CopyBuffer(emaSlowHandle, 0, shift, 1, s) <= 0) return false;
   trend = (f[0] > s[0]) ? 1 : ((f[0] < s[0]) ? -1 : 0);
   return true;
}

bool GetATR(int shift, double &atrVal){
   double a[]; if(CopyBuffer(atrHandle, 0, shift, 1, a) <= 0) return false;
   atrVal = a[0]; return true;
}

bool FindPreRangeBeforeA_TF(int sA, int window, double atrMult,
                            double &rangeHigh, double &rangeLow,
                            datetime &tStart, datetime &tEnd)
{
   if(window <= 1) return false;
   if(sA + window > LookbackBars - 1) return false;
   int start = sA + window, end = sA + 1;
   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int i = start; i >= end; --i){
      double h = iHigh(_Symbol, WorkTF, i);
      double l = iLow (_Symbol, WorkTF, i);
      if(h > hi) hi = h; if(l < lo) lo = l;
   }
   double atrVal; if(!GetATR(sA+1, atrVal)) return false;
   if((hi - lo) > atrVal * atrMult) return false;
   rangeHigh=hi; rangeLow=lo; tStart=iTime(_Symbol,WorkTF,start); tEnd=iTime(_Symbol,WorkTF,end);
   return true;
}

// Positions count (open only)
int CountOpenPositionsBySymbolMagic()
{
   int count=0;
   for(int i=0;i<PositionsTotal();++i){
      ulong tk=PositionGetTicket(i); if(!tk||!PositionSelectByTicket(tk)) continue;
      string sym=""; PositionGetString(POSITION_SYMBOL,sym);
      ulong mg=(ulong)PositionGetInteger(POSITION_MAGIC);
      if(sym==_Symbol && mg==Magic) count++;
   }
   return count;
}

// Pending count + direction (1=buy, -1=sell, 0=none)
int CountPendingsBySymbolMagic(int &dir)
{
   dir=0;
   int count=0;
   for(int j=0;j<OrdersTotal();++j){
      ulong ticket = OrderGetTicket(j);
      if(ticket==0 || !OrderSelect(ticket)) continue;
      string sym = OrderGetString(ORDER_SYMBOL);
      ulong  mg  = (ulong)OrderGetInteger(ORDER_MAGIC);
      ENUM_ORDER_TYPE type=(ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(sym==_Symbol && mg==Magic && (type==ORDER_TYPE_BUY_LIMIT || type==ORDER_TYPE_SELL_LIMIT)){
         count++;
         dir = (type==ORDER_TYPE_BUY_LIMIT) ? 1 : -1;
      }
   }
   return count;
}

void DeleteAllPendingsBySymbolMagic()
{
   for(int j=OrdersTotal()-1;j>=0;--j){
      ulong ticket = OrderGetTicket(j);
      if(ticket==0 || !OrderSelect(ticket)) continue;
      string sym = OrderGetString(ORDER_SYMBOL);
      ulong  mg  = (ulong)OrderGetInteger(ORDER_MAGIC);
      ENUM_ORDER_TYPE type=(ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(sym==_Symbol && mg==Magic && (type==ORDER_TYPE_BUY_LIMIT || type==ORDER_TYPE_SELL_LIMIT)){
         trade.OrderDelete(ticket);
      }
   }
}

double NormalizeLots(double lots)
{
   double minlot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxlot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lots = MathMax(minlot, MathMin(maxlot, lots));
   double steps = MathFloor((lots + 1e-12)/step);
   lots = steps * step;
   if(lots < minlot - 1e-12) return 0.0;
   return lots;
}

double ValuePerPointPerLot()
{
   double tick_value = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick_size<=0) return 0.0;
   return tick_value / tick_size;
}

double CalcLotsByRisk(double stop_points)
{
   if(stop_points<=0) return FixedLots;
   double bal = AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_money = bal * (RiskPercent/100.0);
   double vpp = ValuePerPointPerLot();
   if(vpp<=0) return FixedLots;
   return NormalizeLots(risk_money / (stop_points * vpp));
}

//-------------------- Zone-break helpers (anti-hedge) ----------------
bool BullZoneBroken()
{
   if(!hasBullZone) return true; // không có zone => không chặn
   double lastLow = iLow(_Symbol, WorkTF, 1); // nến đã đóng gần nhất
   double thresh  = bullBottom - ZoneBreakBufferPts * _Point;
   return (lastLow < thresh);
}

bool BearZoneBroken()
{
   if(!hasBearZone) return true;
   double lastHigh = iHigh(_Symbol, WorkTF, 1); // nến đã đóng gần nhất
   double thresh   = bearTop + ZoneBreakBufferPts * _Point;
   return (lastHigh > thresh);
}

//========================== EA lifecycle ===========================
int OnInit()
{
   atrHandle = iATR(_Symbol, WorkTF, ATRPeriod);
   if(atrHandle == INVALID_HANDLE){ Print("ATR handle failed"); return INIT_FAILED; }

   emaFastHandle = iMA(_Symbol, WorkTF, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
   emaSlowHandle = iMA(_Symbol, WorkTF, SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(UseEMATrend && (emaFastHandle==INVALID_HANDLE || emaSlowHandle==INVALID_HANDLE)){
      Print("EMA handle failed"); return INIT_FAILED;
   }

   trade.SetExpertMagicNumber(Magic);
   trade.SetDeviationInPoints(DeviationPoints); // chỉ ảnh hưởng market orders

   lastBarTime    = iTime(_Symbol, WorkTF, 0);
   EAStartBarTime = lastBarTime; // mốc attach
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason){}

//============================== Core ===============================
void OnTick()
{
   if(!IsNewBar()) return;

   int bars = iBars(_Symbol, WorkTF);
   int maxScan = MathMin(bars - 1, LookbackBars);
   if(maxScan < 4) return; // cần ít nhất 4 nến (0..3), A=3,B=2,C=1

   int openPos = CountOpenPositionsBySymbolMagic();

   // Duyệt A=3, B=2, C=1 (đều đã đóng)
   for(int s = 3; s < maxScan; ++s)
   {
      datetime tA = iTime(_Symbol, WorkTF, s);
      datetime tB = iTime(_Symbol, WorkTF, s-1);
      datetime tC = iTime(_Symbol, WorkTF, s-2);
      if(tC < EAStartBarTime) continue;

      // OHLC
      double HA = iHigh(_Symbol, WorkTF, s);
      double LA = iLow (_Symbol, WorkTF, s);
      double HB = iHigh(_Symbol, WorkTF, s-1);
      double LB = iLow (_Symbol, WorkTF, s-1);
      double HC = iHigh(_Symbol, WorkTF, s-2);
      double LC = iLow (_Symbol, WorkTF, s-2);

      // FVG rule 3 nến (đều closed):
      bool bullFVG = (LC > HA);  // BUY: [HA .. LC]
      bool bearFVG = (HC < LA);  // SELL: [HC .. LA]
      if(!bullFVG && !bearFVG) continue;

      // Lọc EMA nếu bật
      int trend=0; GetEMATrend(s, trend);
      if(OnlyWithTrend){
         if(bullFVG && trend<0) continue;
         if(bearFVG && trend>0) continue;
      }

      // Cập nhật vùng gần nhất
      if(bullFVG){ hasBullZone=true; bullBottom=HA; bullTop=LC; }
      if(bearFVG){ hasBearZone=true; bearBottom=LA; bearTop=HC; }

      // Vẽ vùng tham chiếu
      if(bullFVG){
         string rname = RectName("FVG_BULL", tA, tC);
         if(ObjectFind(0, rname)==-1){
            DrawRect(rname, tA, LC, tC, HA, BullFVGColor);
            if(MarkPreRange){
               double rh, rl; datetime ts, te;
               if(FindPreRangeBeforeA_TF(s, RangeWindow, RangeATRMult, rh, rl, ts, te)){
                  string rng = RectName("RANGE_PRE", ts, te);
                  DrawRect(rng, ts, rh, te, rl, RangeColor);
               }
            }
         }
      } else if(bearFVG){
         string rname = RectName("FVG_BEAR", tA, tC);
         if(ObjectFind(0, rname)==-1){
            DrawRect(rname, tA, HC, tC, LA, BearFVGColor);
            if(MarkPreRange){
               double rh, rl; datetime ts, te;
               if(FindPreRangeBeforeA_TF(s, RangeWindow, RangeATRMult, rh, rl, ts, te)){
                  string rng = RectName("RANGE_PRE", ts, te);
                  DrawRect(rng, ts, rh, te, rl, RangeColor);
               }
            }
         }
      }

      // Entry theo EDGE/MID
      int    digits     = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
      double entry_buy  = (EntryMode==ENTRY_MID) ? (HA+LC)/2.0 : LC;
      double entry_sell = (EntryMode==ENTRY_MID) ? (HC+LA)/2.0 : HC;
      entry_buy  = NormalizeDouble(entry_buy,  digits);
      entry_sell = NormalizeDouble(entry_sell, digits);

      // Đặt/đổi pending nếu được phép
      if(EnableTrading && openPos < MaxPositions)
      {
         int pendDir=0; int pendCount = CountPendingsBySymbolMagic(pendDir);
         int needDir = bullFVG ? 1 : -1;

         // Nếu có pending NGƯỢC CHIỀU => xoá hết pending cũ trước khi đặt mới
         if(pendCount>0 && pendDir!=0 && pendDir!=needDir){
            DeleteAllPendingsBySymbolMagic();
            pendCount = 0; pendDir = 0;
         }

         // Chỉ đặt khi không còn pending nào
         if(pendCount==0)
         {
            trade.SetExpertMagicNumber(Magic);

            if(bullFVG && AllowLong){
               // Chống hedge: không BUY khi bearish zone chưa thủng
               if(!EnforceNoHedge || BearZoneBroken()){
                  double entry = entry_buy;
                  double sl    = LB - (StopBufferPts + SLExtraPts) * _Point;
                  sl = NormalizeDouble(sl, digits);

                  double stop_points = MathAbs(entry - sl)/_Point;
                  double lots = UseRiskPercent ? CalcLotsByRisk(stop_points) : NormalizeLots(FixedLots);
                  if(lots > 0){
                     double tp = UseRR ? (entry + stop_points*_Point*RR)
                                       : (entry + TPPoints*_Point);
                     tp = NormalizeDouble(tp, digits);
                     trade.BuyLimit(lots, entry, _Symbol, sl, tp);
                  }
               }
            }
            else if(bearFVG && AllowShort){
               // Chống hedge: không SELL khi bullish zone chưa thủng
               if(!EnforceNoHedge || BullZoneBroken()){
                  double entry = entry_sell;
                  double sl    = HB + (StopBufferPts + SLExtraPts) * _Point;
                  sl = NormalizeDouble(sl, digits);

                  double stop_points = MathAbs(entry - sl)/_Point;
                  double lots = UseRiskPercent ? CalcLotsByRisk(stop_points) : NormalizeLots(FixedLots);
                  if(lots > 0){
                     double tp = UseRR ? (entry - stop_points*_Point*RR)
                                       : (entry - TPPoints*_Point);
                     tp = NormalizeDouble(tp, digits);
                     trade.SellLimit(lots, entry, _Symbol, sl, tp);
                  }
               }
            }
         }
      }

      // Chỉ xử lý FVG đầu tiên trong lượt quét
      break;
   }
}
