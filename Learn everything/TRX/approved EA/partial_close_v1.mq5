#property copyright "Free to use"
#property version   "1.06"
#property strict
#property description "EA: Partial close at N*R (R = initial stop distance)."
#property description "MT5 only. No SL move. Can freeze the first SL as initial R."

#include <Trade/Trade.mqh>
CTrade trade;

//---------------------
// Inputs
//---------------------
input double InpRMultiple        = 5.0;   // R multiple to trigger partial close
input double InpClosePercent     = 50.0;  // Percent of current volume to close
input bool   InpManageAllSymbols = true;  // Manage all symbols (false = only current chart symbol)
input bool   InpFilterByMagic    = false; // Filter by Magic Number
input long   InpMagicNumber      = 0;     // Magic Number if enabled
input int    InpDeviationPoints  = 10;    // Max slippage (points)
input bool   InpOneTimeOnly      = true;  // Do partial close once per position
input bool   InpFreezeInitialSL  = true;  // Freeze first SL as reference R

//---------------------
// Global-var keys
//---------------------
string KeyPCDone(ulong ticket) { return(StringFormat("pc_done_%I64u", ticket)); }
string KeySLInit(ulong ticket) { return(StringFormat("sl_init_%I64u", ticket)); }
string KeyRInit(ulong ticket)  { return(StringFormat("r_init_%I64u", ticket)); }

bool IsPartialDone(ulong ticket)
{
   string key = KeyPCDone(ticket);
   if(!GlobalVariableCheck(key)) return(false);
   return(GlobalVariableGet(key) > 0.0);
}

void MarkPartialDone(ulong ticket)
{
   GlobalVariableSet(KeyPCDone(ticket), (double)TimeCurrent()); // return is datetime, we ignore it :contentReference[oaicite:3]{index=3}
}

bool SymbolMatches(const string sym)
{
   if(InpManageAllSymbols) return true;
   return (sym == _Symbol);
}

bool MagicMatches()
{
   if(!InpFilterByMagic) return true;
   long mg = (long)PositionGetInteger(POSITION_MAGIC);
   return (mg == InpMagicNumber);
}

// Freeze first SL/R once
void CaptureInitialSLandR(ulong ticket, ENUM_POSITION_TYPE type, double price_open, double sl)
{
   if(!InpFreezeInitialSL) return;
   if(sl <= 0.0) return;

   string kSL = KeySLInit(ticket);
   string kR  = KeyRInit(ticket);
   if(!GlobalVariableCheck(kSL))
   {
      GlobalVariableSet(kSL, sl);
      double r = (type == POSITION_TYPE_BUY) ? MathAbs(price_open - sl)
                                             : MathAbs(sl - price_open);
      if(r > 0.0) GlobalVariableSet(kR, r);
   }
}

bool GetFrozenR(ulong ticket, double &r_out)
{
   if(!InpFreezeInitialSL) return false;
   string kR = KeyRInit(ticket);
   if(!GlobalVariableCheck(kR)) return false;
   r_out = GlobalVariableGet(kR);
   return (r_out > 0.0);
}

// Live R from current SL
double ComputeLiveR(ENUM_POSITION_TYPE type, double price_open, double sl)
{
   if(sl <= 0.0) return 0.0;
   return (type == POSITION_TYPE_BUY) ? MathAbs(price_open - sl)
                                      : MathAbs(sl - price_open);
}

// Target = entry ± multiple * R
bool ComputeTarget(ENUM_POSITION_TYPE type, double price_open, double R, double multiple, double &target)
{
   if(R <= 0.0 || multiple <= 0.0) return false;
   target = (type == POSITION_TYPE_BUY) ? price_open + multiple * R
                                        : price_open - multiple * R;
   return true;
}

// Normalize volume to symbol constraints
double NormalizeVolume(const string sym, double volume)
{
   double minlot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double maxlot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);

   if(volume < minlot) volume = minlot;
   if(volume > maxlot) volume = maxlot;

   double steps   = MathFloor((volume + 1e-12) / step);
   double snapped = steps * step;
   if(snapped < minlot - 1e-12) return 0.0;
   return snapped;
}

// Partial close by ticket (hedging-safe) :contentReference[oaicite:4]{index=4}
bool ClosePartialByTicket(const ulong ticket, const double requested_volume)
{
   if(!PositionSelectByTicket(ticket)) return false;
   string sym = "";
   if(!PositionGetString(POSITION_SYMBOL, sym)) return false; // safe variant with string& :contentReference[oaicite:5]{index=5}

   double vol = NormalizeVolume(sym, requested_volume);
   if(vol <= 0.0) return false;

   trade.SetDeviationInPoints(InpDeviationPoints);
   return trade.PositionClosePartial(ticket, vol);
}

//---------------------
// EA lifecycle
//---------------------
int OnInit()
{
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   int total = PositionsTotal(); // :contentReference[oaicite:6]{index=6}
   int i;
   for(i = 0; i < total; i++)
   {
      // safest pattern per docs: get ticket, then select by ticket :contentReference[oaicite:7]{index=7}
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;

      // fetch props
      string sym = "";
      if(!PositionGetString(POSITION_SYMBOL, sym)) continue;  // string via &receiver :contentReference[oaicite:8]{index=8}
      if(!SymbolMatches(sym)) continue;

      if(!MagicMatches()) continue;

      ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE); // :contentReference[oaicite:9]{index=9}
      double entry = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl    = PositionGetDouble(POSITION_SL);
      double vol   = PositionGetDouble(POSITION_VOLUME);
      if(vol <= 0.0) continue;

      // freeze first R when SL appears
      CaptureInitialSLandR(ticket, type, entry, sl);

      // resolve R
      double R = 0.0;
      if(!GetFrozenR(ticket, R)) R = ComputeLiveR(type, entry, sl);
      if(R <= 0.0) continue;

      double target = 0.0;
      if(!ComputeTarget(type, entry, R, InpRMultiple, target)) continue;

      // last tick
      MqlTick last;
      if(!SymbolInfoTick(sym, last)) continue;  // correct call signature :contentReference[oaicite:10]{index=10}

      bool reached = (type == POSITION_TYPE_BUY) ? (last.bid >= target)
                                                 : (last.ask <= target);
      if(!reached) continue;

      if(InpOneTimeOnly && IsPartialDone(ticket)) continue;

      // compute partial volume, keep at least minlot remaining
      double close_vol = vol * (InpClosePercent / 100.0);
      double minlot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
      close_vol = NormalizeVolume(sym, close_vol);
      if(close_vol <= 0.0 || (vol - close_vol) < (minlot - 1e-12))
         close_vol = NormalizeVolume(sym, vol - minlot);

      if(close_vol > 0.0)
      {
         if(ClosePartialByTicket(ticket, close_vol))
         {
            // No SL move. Leave order unchanged.
            if(InpOneTimeOnly) MarkPartialDone(ticket);
         }
      }
   }
}

void OnDeinit(const int reason)
{
   // keep globals; you can add OnTradeTransaction to clean by ticket when position ends if you wish
}
