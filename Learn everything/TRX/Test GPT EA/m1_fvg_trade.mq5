//+------------------------------------------------------------------+
//|                                         m1_fvg_trade.mq5        |
//| FVG marker + auto-trade (entry/SL/TP) khi vùng FVG được fill.    |
//| Mặc định chạy trên M1, đổi ở Inputs khi attach EA.               |
//+------------------------------------------------------------------+
#property strict
#include <Trade/Trade.mqh>

//============================ Inputs ===============================
// Khung thời gian làm việc
input ENUM_TIMEFRAMES   WorkTF         = PERIOD_M1;   // TF để quét FVG

// Xác nhận xu hướng (tùy chọn)
input bool              UseEMATrend    = true;        // Dùng EMA để xác nhận xu hướng
input int               FastEMA        = 50;          // EMA nhanh
input int               SlowEMA        = 200;         // EMA chậm

// Quét & hiển thị
input int               LookbackBars   = 1500;        // Số nến tối đa để quét
input bool              ExtendToNow    = true;        // Kéo vùng FVG đến hiện tại
input color             BullFVGColor   = clrLime;     // Màu FVG tăng
input color             BearFVGColor   = clrTomato;   // Màu FVG giảm
input int               RectWidth      = 1;           // Độ dày viền
input ENUM_LINE_STYLE   RectStyle      = STYLE_SOLID; // Kiểu viền
input uchar             RectOpacity    = 40;          // 0..255, trộn vào ARGB khi vẽ

// Ranging trước khi FVG
input bool              MarkPreRange   = true;        // Đánh dấu vùng range trước FVG
input int               RangeWindow    = 10;          // Số nến kiểm tra range trước FVG
input int               ATRPeriod      = 14;          // ATR period
input double            RangeATRMult   = 0.6;         // Range nếu (max-min) <= ATR*mult
input color             RangeColor     = clrSilver;   // Màu range

//========================= Trading Inputs ==========================
input bool              EnableTrading   = false;      // Bật auto-trade
input bool              AllowLong       = true;       // Cho BUY
input bool              AllowShort      = true;       // Cho SELL
input bool              OnlyWithTrend   = false;      // Chỉ giao dịch thuận EMA
input ulong             Magic           = 20251103;   // Magic number
input int               DeviationPoints = 30;         // Độ lệch giá khi khớp (points)
input int               MaxPositions    = 1;          // Tối đa lệnh mở (theo symbol+magic)

// Khối lượng và rủi ro
input bool              UseRiskPercent  = true;       // Tính lot theo % rủi ro
input double            RiskPercent     = 1.0;        // % rủi ro mỗi lệnh
input double            FixedLots       = 0.10;       // Lot cố định nếu không dùng %

// SL/TP
input double            StopBufferPts   = 10;         // Đệm SL ngoài mép FVG (points)
input bool              UseRR           = true;       // Dùng RR để đặt TP
input double            RR              = 2.0;        // Risk:Reward (ví dụ 2:1)
input int               TPPoints        = 100;        // Nếu không dùng RR, TP cố định (points)
input bool              TradeOnClose    = true;       // Vào khi nến vừa đóng nằm trong vùng

//=========================== Globals ===============================
CTrade     trade;
int        atrHandle     = INVALID_HANDLE;
int        emaFastHandle = INVALID_HANDLE;
int        emaSlowHandle = INVALID_HANDLE;
datetime   lastBarTime   = 0;

//=========================== Helpers ===============================
color ColorWithAlpha(color base, uchar alpha){ return (color)ColorToARGB(base, alpha); }

bool IsNewBar(){
   datetime t0 = iTime(_Symbol, WorkTF, 0);
   if(t0 == lastBarTime) return false;
   lastBarTime = t0;
   return true;
}

string TFToString(ENUM_TIMEFRAMES tf){
   switch(tf){
      case PERIOD_M1:   return "M1";  case PERIOD_M2:   return "M2";  case PERIOD_M3:   return "M3";
      case PERIOD_M4:   return "M4";  case PERIOD_M5:   return "M5";  case PERIOD_M6:   return "M6";
      case PERIOD_M10:  return "M10"; case PERIOD_M12:  return "M12"; case PERIOD_M15:  return "M15";
      case PERIOD_M20:  return "M20"; case PERIOD_M30:  return "M30"; case PERIOD_H1:   return "H1";
      case PERIOD_H2:   return "H2";  case PERIOD_H3:   return "H3";  case PERIOD_H4:   return "H4";
      case PERIOD_H6:   return "H6";  case PERIOD_H8:   return "H8";  case PERIOD_H12:  return "H12";
      case PERIOD_D1:   return "D1";  case PERIOD_W1:   return "W1";  case PERIOD_MN1:  return "MN1";
   }
   return "TF";
}

string RectName(const string prefix, datetime tA, datetime tC){
   return StringFormat("%s_%s_%s_%I64d_%I64d", prefix, _Symbol, TFToString(WorkTF), (long)tA, (long)tC);
}

void DrawRect(const string name, datetime time1, double priceTop, datetime time2, double priceBot, color c)
{
   double top = MathMax(priceTop, priceBot);
   double bot = MathMin(priceTop, priceBot);

   if(ObjectFind(0, name) == -1)
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, time1, top, time2, bot);

   color drawColor = (RectOpacity < 255) ? ColorWithAlpha(c, RectOpacity) : c;
   ObjectSetInteger(0, name, OBJPROP_COLOR,   (long)drawColor);
   ObjectSetInteger(0, name, OBJPROP_STYLE,   (long)RectStyle);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,   (long)RectWidth);
   ObjectSetInteger(0, name, OBJPROP_BACK,    true);
   ObjectSetInteger(0, name, OBJPROP_FILL,    true);
   ObjectSetInteger(0, name, OBJPROP_ZORDER,  0);

   datetime rightTime = ExtendToNow ? iTime(_Symbol, WorkTF, 0) : time2;

   // update 2 anchor points
   ObjectMove(0, name, 0, time1,     top);
   ObjectMove(0, name, 1, rightTime, bot);
}

bool GetEMATrend(int shift, int &trend){
   if(!UseEMATrend) { trend = 0; return true; }
   double f[], s[];
   if(CopyBuffer(emaFastHandle, 0, shift, 1, f) <= 0) return false;
   if(CopyBuffer(emaSlowHandle, 0, shift, 1, s) <= 0) return false;
   trend = (f[0] > s[0]) ? 1 : ((f[0] < s[0]) ? -1 : 0);
   return true;
}

bool IsBullFVG_TF(int s, double &lowC, double &highA){
   if(s < 2) return false;
   double highA_ = iHigh(_Symbol, WorkTF, s);
   double lowC_  = iLow (_Symbol, WorkTF, s-2);
   if(lowC_ > highA_) { lowC = lowC_; highA = highA_; return true; }
   return false;
}

bool IsBearFVG_TF(int s, double &highC, double &lowA){
   if(s < 2) return false;
   double lowA_  = iLow (_Symbol, WorkTF, s);
   double highC_ = iHigh(_Symbol, WorkTF, s-2);
   if(highC_ < lowA_) { highC = highC_; lowA = lowA_; return true; }
   return false;
}

bool GetATR(int shift, double &atrVal){
   double a[];
   if(CopyBuffer(atrHandle, 0, shift, 1, a) <= 0) return false;
   atrVal = a[0];
   return true;
}

bool FindPreRangeBeforeA_TF(int sA, int window, double atrMult,
                            double &rangeHigh, double &rangeLow,
                            datetime &tStart, datetime &tEnd)
{
   if(window <= 1) return false;
   if(sA + window > LookbackBars - 1) return false;

   int start = sA + window;
   int end   = sA + 1;

   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int i = start; i >= end; --i){
      double h = iHigh(_Symbol, WorkTF, i);
      double l = iLow (_Symbol, WorkTF, i);
      if(h > hi) hi = h;
      if(l < lo) lo = l;
   }

   double atrVal;
   if(!GetATR(sA+1, atrVal)) return false;
   bool isRange = ((hi - lo) <= atrVal * atrMult);
   if(!isRange) return false;

   rangeHigh = hi; rangeLow = lo;
   tStart = iTime(_Symbol, WorkTF, start);
   tEnd   = iTime(_Symbol, WorkTF, end);
   return true;
}

//========================= Trading Helpers =========================
bool AlreadyTraded(const string key){ return GlobalVariableCheck("TRADED_" + key); }
void MarkTraded(const string key){ GlobalVariableSet("TRADED_" + key, TimeCurrent()); }

int CountOpenBySymbolMagic()
{
   int total = PositionsTotal();
   int count = 0;
   for(int idx=0; idx<total; ++idx)
   {
      ulong ticket = PositionGetTicket(idx);
      if(ticket==0) continue;
      if(!PositionSelectByTicket(ticket)) continue;

      string sym = ""; PositionGetString(POSITION_SYMBOL, sym);
      ulong  mg  = (ulong)PositionGetInteger(POSITION_MAGIC);
      if(sym==_Symbol && mg==Magic) count++;
   }
   return count;
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

bool TryTradeFromRect(const string rectName, bool isBull)
{
   if(!EnableTrading) return false;
   if(AlreadyTraded(rectName)) return false;
   if(isBull && !AllowLong) return false;
   if(!isBull && !AllowShort) return false;

   int trend=0; GetEMATrend(1, trend);
   if(OnlyWithTrend){
      if(isBull && trend<0) return false;
      if(!isBull && trend>0) return false;
   }

   // LẤY GIÁ TỪ RECTANGLE THEO DOCS MQL5: OBJPROP_PRICE với modifier 0/1
   double top = ObjectGetDouble(0, rectName, OBJPROP_PRICE, 0);
   double bot = ObjectGetDouble(0, rectName, OBJPROP_PRICE, 1);
   if(top<=0 || bot<=0) return false;
   double hi = MathMax(top, bot);
   double lo = MathMin(top, bot);

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   bool filled = false;
   if(TradeOnClose){
      double cH = iHigh(_Symbol, WorkTF, 1);
      double cL = iLow (_Symbol, WorkTF, 1);
      filled = (cH>=lo && cL<=hi);
   } else {
      double price = isBull?ask:bid;
      filled = (price>=lo && price<=hi);
   }
   if(!filled) return false;

   double entry = isBull?ask:bid;
   double sl    = isBull ? (lo - StopBufferPts*_Point)
                         : (hi + StopBufferPts*_Point);

   double stop_points = MathAbs(entry - sl)/_Point;
   double lots = UseRiskPercent ? CalcLotsByRisk(stop_points) : FixedLots;
   lots = NormalizeLots(lots);
   if(lots <= 0) { Print("Lot size <=0"); return false; }

   double tp = UseRR
      ? (isBull ? (entry + stop_points*_Point*RR) : (entry - stop_points*_Point*RR))
      : (isBull ? (entry + TPPoints*_Point)       : (entry - TPPoints*_Point));

   if(CountOpenBySymbolMagic() >= MaxPositions) return false;
   trade.SetExpertMagicNumber(Magic);
   trade.SetDeviationInPoints(DeviationPoints);
   bool ok = isBull ? trade.Buy(lots, _Symbol, entry, sl, tp)
                    : trade.Sell(lots, _Symbol, entry, sl, tp);

   if(ok) MarkTraded(rectName); else Print("Order send failed: ", _LastError);
   return ok;
}

//========================== EA lifecycle ===========================
int OnInit()
{
   atrHandle = iATR(_Symbol, WorkTF, ATRPeriod);
   if(atrHandle == INVALID_HANDLE){ Print("Failed to create ATR handle"); return INIT_FAILED; }

   emaFastHandle = iMA(_Symbol, WorkTF, FastEMA, 0, MODE_EMA, PRICE_CLOSE);
   emaSlowHandle = iMA(_Symbol, WorkTF, SlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(UseEMATrend && (emaFastHandle == INVALID_HANDLE || emaSlowHandle == INVALID_HANDLE)){
      Print("Failed to create EMA handles"); return INIT_FAILED;
   }

   trade.SetExpertMagicNumber(Magic);
   trade.SetDeviationInPoints(DeviationPoints);

   lastBarTime = iTime(_Symbol, WorkTF, 0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason){ /* giữ object để tham chiếu sau */ }

void OnTick()
{
   if(!IsNewBar()) return;

   // quét các FVG đã vẽ để xem fill
   int objTotal = ObjectsTotal(0, -1, -1);
   for(int i=0; i<objTotal; ++i)
   {
      string name = ObjectName(0, i, -1, -1);
      if(StringLen(name)==0) continue;
      if(StringFind(name, "FVG_BULL")==0) TryTradeFromRect(name, true);
      else if(StringFind(name, "FVG_BEAR")==0) TryTradeFromRect(name, false);
   }

   // dò FVG mới và vẽ
   int bars = iBars(_Symbol, WorkTF);
   int maxScan = MathMin(bars - 1, LookbackBars);
   if(maxScan < 3) return;

   for(int s = 2; s < maxScan; ++s)
   {
      datetime tA = iTime(_Symbol, WorkTF, s);
      datetime tC = iTime(_Symbol, WorkTF, s-2);

      string bullName = RectName("FVG_BULL", tA, tC);
      string bearName = RectName("FVG_BEAR", tA, tC);
      if(ObjectFind(0, bullName) != -1 || ObjectFind(0, bearName) != -1) continue;

      double x1, x2;
      int trend = 0; GetEMATrend(s, trend);

      if(IsBullFVG_TF(s, x1, x2))
      {
         if(!OnlyWithTrend || trend >= 0)
         {
            DrawRect(bullName, tA, x1, tC, x2, BullFVGColor);
            if(MarkPreRange){
               double rh, rl; datetime ts, te;
               if(FindPreRangeBeforeA_TF(s, RangeWindow, RangeATRMult, rh, rl, ts, te)){
                  string rname = RectName("RANGE_PRE", ts, te);
                  DrawRect(rname, ts, rh, te, rl, RangeColor);
               }
            }
            TryTradeFromRect(bullName, true);
         }
      }
      else if(IsBearFVG_TF(s, x1, x2))
      {
         if(!OnlyWithTrend || trend <= 0)
         {
            DrawRect(bearName, tA, x2, tC, x1, BearFVGColor);
            if(MarkPreRange){
               double rh, rl; datetime ts, te;
               if(FindPreRangeBeforeA_TF(s, RangeWindow, RangeATRMult, rh, rl, ts, te)){
                  string rname = RectName("RANGE_PRE", ts, te);
                  DrawRect(rname, ts, rh, te, rl, RangeColor);
               }
            }
            TryTradeFromRect(bearName, false);
         }
      }
   }
}
//+------------------------------------------------------------------+
