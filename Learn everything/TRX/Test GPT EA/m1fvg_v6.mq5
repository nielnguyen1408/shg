//+------------------------------------------------------------------+
//|                                      m1fvg_v2_cluster.mq5       |
//| FVG 3-nến (A=3,B=2,C=1 closed) + Pending Limit + Cluster logic   |
//| - Cụm FVG: liên tiếp => 1 cụm, giữ limit ở FVG đầu của cụm      |
//| - Có "pause" => kết thúc cụm, dời limit & dời mốc "thủng"        |
//| - SLRef (A/B), ZoneBreakRef (A/B), Entry EDGE/MID, risk %        |
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

input bool              EnableTrading   = true;
input bool              AllowLong       = true;
input bool              AllowShort      = true;
input bool              OnlyWithTrend   = false;
input ulong             Magic           = 20251103;
input int               DeviationPoints = 30;
input int               MaxPositions    = 1;

// Lot & risk
input bool              UseRiskPercent  = true;
input double            RiskPercent     = 1.0;
input double            FixedLots       = 0.10;

// SL/TP
input double            StopBufferPts   = 5;
input int               SLExtraPts      = 12;
input bool              UseRR           = true;
input double            RR              = 2.0;
input int               TPPoints        = 100;

// Entry mode
enum ENTRY_PRICE_MODE { ENTRY_EDGE=0, ENTRY_MID=1 };
input ENTRY_PRICE_MODE  EntryMode       = ENTRY_EDGE;

// SL đặt theo A/B (đỘC LẬP với break rule)
enum SL_REF_MODE { SL_FROM_A=0, SL_FROM_B=1 };
input SL_REF_MODE       SLRef           = SL_FROM_B;

// Anti-hedge: xét “FVG bị thủng” theo A/B (độc lập với SLRef)
input bool              EnforceNoHedge     = true;
enum BREAK_REF_MODE { BREAK_FROM_A=0, BREAK_FROM_B=1 };
input BREAK_REF_MODE    ZoneBreakRef      = BREAK_FROM_B;
input int               ZoneBreakBufferPts = 2;

// Cluster: số bar “nghỉ” tối thiểu để kết thúc cụm
// 0 = rất nhạy; 1 = cần ít nhất 1 bar giữa hai FVG để coi là pause
input int               PauseBarsToSwitch  = 1;

//=========================== Globals ===============================
CTrade     trade;
int        emaFastHandle = INVALID_HANDLE;
int        emaSlowHandle = INVALID_HANDLE;
datetime   lastBarTime   = 0;
datetime   EAStartBarTime = 0;

// Zones (để anti-hedge và vẽ)
bool       hasBullZone=false, hasBearZone=false;
double     bullTop=0.0, bullBottom=0.0; // Bull: [HA .. LC]
double     bearTop=0.0, bearBottom=0.0; // Bear: [HC .. LA]
double     bullBreakLevel=0.0;          // dùng cho xét SELL
double     bearBreakLevel=0.0;          // dùng cho xét BUY

// --------- Cluster state ---------
// 1 = bull cluster; -1 = bear cluster; 0 = none
int        clusterDir = 0;
// nến C của FVG ĐẦU TIÊN trong cụm (để đo “liên tiếp”)
datetime   clusterC   = 0;
// Entry & SL/TP của FVG đầu cụm (để không dời khi còn liên tiếp)
double     clusterEntry = 0.0;
double     clusterSL    = 0.0;
double     clusterTP    = 0.0;
// “Break levels” gắn với cụm (được set khi tạo cụm)
double     clusterBullBreakLevel = 0.0;
double     clusterBearBreakLevel = 0.0;

//=========================== Helpers ===============================
color ColorWithAlpha(color base, uchar alpha){ return (color)ColorToARGB(base, alpha); }
bool  IsNewBar(){ datetime t0=iTime(_Symbol,WorkTF,0); if(t0==lastBarTime) return false; lastBarTime=t0; return true; }
int   BarIndexByTime(datetime t){ return iBarShift(_Symbol, WorkTF, t, true); }

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
   double top=MathMax(priceTop,priceBot), bot=MathMin(priceTop,priceBot);
   if(ObjectFind(0,name)==-1) ObjectCreate(0,name,OBJ_RECTANGLE,0,tA,top,tC,bot);
   color drawColor=(RectOpacity<255)? ColorWithAlpha(c,RectOpacity):c;
   ObjectSetInteger(0,name,OBJPROP_COLOR,(long)drawColor);
   ObjectSetInteger(0,name,OBJPROP_STYLE,(long)RectStyle);
   ObjectSetInteger(0,name,OBJPROP_WIDTH,(long)RectWidth);
   ObjectSetInteger(0,name,OBJPROP_BACK,true);
   ObjectSetInteger(0,name,OBJPROP_FILL,true);
   ObjectSetInteger(0,name,OBJPROP_ZORDER,0);
   ObjectMove(0,name,0,tA,top);
   ObjectMove(0,name,1,tC,bot);
}

bool GetEMATrend(int shift,int &trend){
   if(!UseEMATrend){ trend=0; return true; }
   double f[],s[];
   if(CopyBuffer(emaFastHandle,0,shift,1,f)<=0) return false;
   if(CopyBuffer(emaSlowHandle,0,shift,1,s)<=0) return false;
   trend=(f[0]>s[0])?1:((f[0]<s[0])?-1:0);
   return true;
}

// Lots & risk helpers
double NormalizeLots(double lots){
   double minlot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maxlot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step  =SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   lots=MathMax(minlot,MathMin(maxlot,lots));
   double steps=MathFloor((lots+1e-12)/step);
   lots=steps*step;
   if(lots<minlot-1e-12) return 0.0;
   return lots;
}
double ValuePerPointPerLot(){
   double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(ts<=0.0) return 0.0;
   return tv/ts;
}
double CalcLotsByRisk(double stop_points){
   if(stop_points<=0.0) return NormalizeLots(FixedLots);
   double bal=AccountInfoDouble(ACCOUNT_EQUITY);
   double risk_money=bal*(RiskPercent/100.0);
   double vpp=ValuePerPointPerLot();
   if(vpp<=0.0) return NormalizeLots(FixedLots);
   double lots=risk_money/(stop_points*vpp);
   return NormalizeLots(lots);
}

// Pending helpers
void DeleteAllPendingsBySymbolMagic(){
   for(int j=OrdersTotal()-1;j>=0;--j){
      ulong ticket=OrderGetTicket(j);
      if(ticket==0 || !OrderSelect(ticket)) continue;
      string sym=OrderGetString(ORDER_SYMBOL);
      ulong  mg =(ulong)OrderGetInteger(ORDER_MAGIC);
      ENUM_ORDER_TYPE type=(ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(sym==_Symbol && mg==Magic && (type==ORDER_TYPE_BUY_LIMIT || type==ORDER_TYPE_SELL_LIMIT))
         trade.OrderDelete(ticket);
   }
}

// Anti-hedge using last closed bar
bool BullZoneBroken(){ // allow SELL when bull zone is broken DOWN
   if(!hasBullZone) return true;
   double lastLow=iLow(_Symbol,WorkTF,1);
   double thresh=(clusterDir!=0? clusterBullBreakLevel:bullBreakLevel) - ZoneBreakBufferPts*_Point;
   return (lastLow < thresh);
}
bool BearZoneBroken(){ // allow BUY when bear zone is broken UP
   if(!hasBearZone) return true;
   double lastHigh=iHigh(_Symbol,WorkTF,1);
   double thresh=(clusterDir!=0? clusterBearBreakLevel:bearBreakLevel) + ZoneBreakBufferPts*_Point;
   return (lastHigh > thresh);
}

//========================== EA lifecycle ===========================
int OnInit()
{
   emaFastHandle=iMA(_Symbol,WorkTF,FastEMA,0,MODE_EMA,PRICE_CLOSE);
   emaSlowHandle=iMA(_Symbol,WorkTF,SlowEMA,0,MODE_EMA,PRICE_CLOSE);
   if(UseEMATrend && (emaFastHandle==INVALID_HANDLE || emaSlowHandle==INVALID_HANDLE)){
      Print("EMA handle failed"); return INIT_FAILED;
   }
   trade.SetExpertMagicNumber(Magic);
   trade.SetDeviationInPoints(DeviationPoints);
   lastBarTime=iTime(_Symbol,WorkTF,0);
   EAStartBarTime=lastBarTime;
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){}

//============================== Core ===============================
void OnTick()
{
   if(!IsNewBar()) return;

   int bars=iBars(_Symbol,WorkTF);
   int maxScan=MathMin(bars-1,LookbackBars);
   if(maxScan<4) return;

   // số vị thế mở (không tính pending)
   int openPos=0;
   for(int i=0;i<PositionsTotal();++i){
      ulong tk=PositionGetTicket(i); if(!tk||!PositionSelectByTicket(tk)) continue;
      string sym=""; PositionGetString(POSITION_SYMBOL,sym);
      ulong mg=(ulong)PositionGetInteger(POSITION_MAGIC);
      if(sym==_Symbol && mg==Magic) openPos++;
   }

   for(int s=3; s<maxScan; ++s)
   {
      datetime tA=iTime(_Symbol,WorkTF,s);
      datetime tB=iTime(_Symbol,WorkTF,s-1);
      datetime tC=iTime(_Symbol,WorkTF,s-2);
      if(tC<EAStartBarTime) continue;

      double HA=iHigh(_Symbol,WorkTF,s);
      double LA=iLow (_Symbol,WorkTF,s);
      double HB=iHigh(_Symbol,WorkTF,s-1);
      double LB=iLow (_Symbol,WorkTF,s-1);
      double HC=iHigh(_Symbol,WorkTF,s-2);
      double LC=iLow (_Symbol,WorkTF,s-2);

      bool bullFVG=(LC>HA); // [HA..LC]
      bool bearFVG=(HC<LA); // [HC..LA]
      if(!bullFVG && !bearFVG) continue;

      int trend=0; GetEMATrend(s,trend);
      if(OnlyWithTrend){
         if(bullFVG && trend<0) continue;
         if(bearFVG && trend>0) continue;
      }

      // Cập nhật zone gần nhất (để hiển thị & fallback)
      if(bullFVG){ hasBullZone=true; bullBottom=HA; bullTop=LC; }
      if(bearFVG){ hasBearZone=true; bearBottom=LA; bearTop=HC; }

      // Vẽ vùng phát hiện
      if(bullFVG){
         string rn=RectName("FVG_BULL",tA,tC);
         if(ObjectFind(0,rn)==-1) DrawRect(rn,tA,LC,tC,HA,BullFVGColor);
      }else{
         string rn=RectName("FVG_BEAR",tA,tC);
         if(ObjectFind(0,rn)==-1) DrawRect(rn,tA,HC,tC,LA,BearFVGColor);
      }

      // Tính entry của FVG hiện tại (NHƯNG sẽ chỉ dùng để khởi tạo cụm mới)
      int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
      double entry_buy =(EntryMode==ENTRY_MID)? (HA+LC)/2.0 : LC;
      double entry_sell=(EntryMode==ENTRY_MID)? (HC+LA)/2.0 : HC;
      entry_buy =NormalizeDouble(entry_buy ,digits);
      entry_sell=NormalizeDouble(entry_sell,digits);

      // --- CLUSTER DECISION ---
      int newDir = bullFVG? 1 : -1;
      bool sameDirAsCluster = (clusterDir!=0 && newDir==clusterDir);
      int  barsBetween = 0;
      if(clusterC>0){
         int idxPrev=BarIndexByTime(clusterC);
         int idxNew =BarIndexByTime(tC);
         if(idxPrev>=0 && idxNew>=0) barsBetween = idxPrev - idxNew; // idx giảm dần về hiện tại
      }

      bool isPause = (!sameDirAsCluster) ? true              // đổi chiều => coi như kết thúc cụm
                                         : (barsBetween > PauseBarsToSwitch); // cùng chiều nhưng có nghỉ

      // Nếu chưa có cluster hoặc có pause/đổi chiều => tạo CỤM MỚI từ FVG hiện tại
      if(clusterDir==0 || isPause){
         // Hủy mọi pending cũ (nếu có) để dời limit sang cụm mới
         DeleteAllPendingsBySymbolMagic();

         // Khởi tạo cụm mới
         clusterDir = newDir;
         clusterC   = tC;

         // Break levels của CỤM (đi theo cụm)
         // SELL chỉ hợp lệ khi bull cluster bị thủng xuống Low(ref)
         // BUY  chỉ hợp lệ khi bear cluster bị thủng lên High(ref)
         clusterBullBreakLevel = (ZoneBreakRef==BREAK_FROM_A ? LA : LB);
         clusterBearBreakLevel = (ZoneBreakRef==BREAK_FROM_A ? HA : HB);

         // Tính entry/SL/TP của FVG đầu cụm
         if(clusterDir==1){
            clusterEntry = entry_buy;
            double slRefPrice = (SLRef==SL_FROM_A ? LA : LB);
            clusterSL = NormalizeDouble(slRefPrice - (StopBufferPts + SLExtraPts)*_Point, digits);
            double stop_pts = MathAbs(clusterEntry - clusterSL)/_Point;
            double lots = UseRiskPercent ? CalcLotsByRisk(stop_pts) : NormalizeLots(FixedLots);
            if(lots>0 && EnableTrading && AllowLong && (openPos<MaxPositions)
               && (!EnforceNoHedge || BearZoneBroken())) // BUY chỉ khi bear-zone (theo cụm) đã thủng lên
            {
               double tp = UseRR ? (clusterEntry + stop_pts*_Point*RR)
                                 : (clusterEntry + TPPoints*_Point);
               clusterTP = NormalizeDouble(tp, digits);
               trade.BuyLimit(lots, clusterEntry, _Symbol, clusterSL, clusterTP);
            }
         }else{ // clusterDir==-1
            clusterEntry = entry_sell;
            double slRefPrice = (SLRef==SL_FROM_A ? HA : HB);
            clusterSL = NormalizeDouble(slRefPrice + (StopBufferPts + SLExtraPts)*_Point, digits);
            double stop_pts = MathAbs(clusterEntry - clusterSL)/_Point;
            double lots = UseRiskPercent ? CalcLotsByRisk(stop_pts) : NormalizeLots(FixedLots);
            if(lots>0 && EnableTrading && AllowShort && (openPos<MaxPositions)
               && (!EnforceNoHedge || BullZoneBroken())) // SELL chỉ khi bull-zone (theo cụm) đã thủng xuống
            {
               double tp = UseRR ? (clusterEntry - stop_pts*_Point*RR)
                                 : (clusterEntry - TPPoints*_Point);
               clusterTP = NormalizeDouble(tp, digits);
               trade.SellLimit(lots, clusterEntry, _Symbol, clusterSL, clusterTP);
            }
         }
      }
      else {
         // Cùng chiều & KHÔNG pause => tiếp tục coi là FVG LIÊN TIẾP trong cùng CỤM
         // => KHÔNG dời limit; có thể cập nhật hiển thị zone gần nhất (optional)
         // Không làm gì với pending hiện có.
      }

      // Cập nhật “zones” để các hàm BearZoneBroken/BullZoneBroken dùng cụm nếu có
      // (đã gán cluster*BreakLevel ở trên; còn hasBullZone/hasBearZone phục vụ vẽ + fallback)
      if(clusterDir!=0){
         // Đồng bộ biến “*BreakLevel” runtime với cluster (để guard dùng được)
         bullBreakLevel = clusterBullBreakLevel;
         bearBreakLevel = clusterBearBreakLevel;
      }

      // Chỉ xử lý FVG đầu tiên mỗi tick
      break;
   }
}
