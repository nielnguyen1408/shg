//+------------------------------------------------------------------+
//|                                EA_Logger_RStudy_v1_05.mq5        |
//|   Logger: R = realized_profit / initial_risk($); TP hits; MFE    |
//|   Appends _<account_login> to filename; logs on close events     |
//|   Clean header (removed R_PriceDistance)                         |
//+------------------------------------------------------------------+
#property copyright "Free"
#property version   "1.05"
#property strict

//=========================== INPUTS ==================================
input bool   InpApplyAllSymbols   = true;          // Apply to all symbols
input string InpSymbolFilter      = "";            // Filter by symbol (empty = any)
input long   InpMagicFilter       = -1;            // Magic filter (-1 = any)

input bool   InpUseInitialSL      = true;          // Freeze INITIAL SL for reference
input bool   InpEnableLogging     = true;          // Enable CSV logging
input string InpLogFileName       = "EA_PartialClose_Logs.csv"; // Base CSV name (Common Files)

// R study parameters
input double InpTP1_RMultiple     = 1.0;
input double InpTP2_RMultiple     = 2.0;
input double InpTP0_RMultiple     = 3.0;           // TP0=3R just to record hit/no hit
input double InpMinRPoints        = 5;             // Minimum R distance in points

//=========================== KEYS ====================================
string KeyInitSL(ulong ticket){ return StringFormat("PC_INITSL_%I64u", ticket); }
string KeyInitVol(ulong ticket){ return StringFormat("PC_INITVOL_%I64u", ticket); }
string KeyMFE  (ulong ticket){ return StringFormat("PC_MFE_%I64u",    ticket); }
string KeyEntry(ulong ticket){ return StringFormat("PC_ENTRY_%I64u",  ticket); }
string KeyLogged(ulong ticket){ return StringFormat("PC_LOGGED_%I64u", ticket); }

//=========================== UTILS ===================================
bool GVSetDouble(const string name, double val){ return GlobalVariableSet(name, val) > 0; }
bool GVGetDouble(const string name, double &val)
{
   if(!GlobalVariableCheck(name)) return false;
   val = GlobalVariableGet(name);
   return true;
}
bool GVIsFlag(const string name){ double v; return GVGetDouble(name, v) && (v>0.5); }
bool GVSetFlag(const string name){ return GVSetDouble(name, 1.0); }

string AppendLoginSuffix(const string base)
{
   long login = AccountInfoInteger(ACCOUNT_LOGIN);
   int dot = StringFind(base, ".", 0);
   if(dot < 0) return StringFormat("%s_%I64d.csv", base, (long)login);
   string name = StringSubstr(base, 0, dot);
   string ext  = StringSubstr(base, dot); // includes dot
   return StringFormat("%s_%I64d%s", name, (long)login, ext);
}

void MaybeFreezeInitials(const ulong ticket, const double sl, const double vol, const double entry)
{
   if(sl > 0.0 && !GlobalVariableCheck(KeyInitSL(ticket)))
      GVSetDouble(KeyInitSL(ticket), sl);
   if(vol > 0.0 && !GlobalVariableCheck(KeyInitVol(ticket)))
      GVSetDouble(KeyInitVol(ticket), vol);
   if(entry > 0.0 && !GlobalVariableCheck(KeyEntry(ticket)))
      GVSetDouble(KeyEntry(ticket), entry);
}

bool PriceTick(const string sym, double &bid, double &ask)
{
   MqlTick tk; if(!SymbolInfoTick(sym, tk)) return false;
   bid = tk.bid; ask = tk.ask; return true;
}

// Update MFE (Most Favorable Excursion) price per position
void UpdateMFE(const ulong ticket, const string sym, const long ptype)
{
   double bid, ask; if(!PriceTick(sym, bid, ask)) return;
   double cur = (ptype == POSITION_TYPE_BUY) ? bid : ask;

   double mfe;
   if(!GVGetDouble(KeyMFE(ticket), mfe))
   {
      GVSetDouble(KeyMFE(ticket), cur);
      return;
   }
   if(ptype == POSITION_TYPE_BUY)
   {
      if(cur > mfe) GVSetDouble(KeyMFE(ticket), cur);
   }
   else
   {
      if(cur < mfe) GVSetDouble(KeyMFE(ticket), cur);
   }
}

//=========================== LOGGING =================================
string EffectiveLogName(){ return AppendLoginSuffix(InpLogFileName); }

int OpenLog()
{
   if(!InpEnableLogging) return INVALID_HANDLE;
   string fname = EffectiveLogName();

   int h = FileOpen(fname, FILE_CSV|FILE_READ|FILE_WRITE|FILE_SHARE_WRITE|FILE_COMMON|FILE_ANSI);
   if(h == INVALID_HANDLE)
   {
      PrintFormat("Logger: FileOpen failed. name=%s, err=%d, common=%s\\Files",
                  fname, GetLastError(), TerminalInfoString(TERMINAL_COMMONDATA_PATH));
      return h;
   }
   if(FileSize(h) == 0)
   {
      FileWrite(h,
        "TimeClose","Ticket","Symbol","Type",
        "Entry","InitialSL","SL_Points",
        "RiskMoney","R",
        "TP0_Price","TP1_Price","TP2_Price",
        "MFEPrice","HighestRMultiple",
        "TP0_Hit","TP1_Hit","TP2_Hit",
        "ClosePrice","CloseCause","CloseProfit","Commission","Swap",
        "InitLots","Magic");
   }
   FileSeek(h, 0, SEEK_END);
   return h;
}

string CloseCauseToString(const ENUM_DEAL_REASON reason)
{
   switch(reason)
   {
      case DEAL_REASON_SL:               return "SL";
      case DEAL_REASON_TP:               return "TP";
      case DEAL_REASON_SO:               return "StopOut";
      case DEAL_REASON_CLIENT:           return "Manual";
      case DEAL_REASON_EXPERT:           return "EA";
      case DEAL_REASON_ROLLOVER:         return "Rollover";
      case DEAL_REASON_VMARGIN:          return "VariationMargin";
      case DEAL_REASON_SPLIT:            return "Split";
      case DEAL_REASON_CORPORATE_ACTION: return "CorporateAction";
      case DEAL_REASON_MOBILE:           return "Mobile";
      case DEAL_REASON_WEB:              return "Web";
      default:                           return "Other";
   }
}

// Compute initial risk in account currency based on entry, initial SL, initial volume
double ComputeInitialRiskMoney(const string sym, const double entry, const double initSL, const double initVol)
{
   if(entry<=0 || initSL<=0 || initVol<=0) return 0.0;
   double tick_size  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double tick_value = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   if(tick_size <= 0.0 || tick_value == 0.0)
   {
      // Fallback to point if needed
      tick_size  = SymbolInfoDouble(sym, SYMBOL_POINT);
      tick_value = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   }
   if(tick_size <= 0.0 || tick_value == 0.0) return 0.0;

   double price_diff = MathAbs(entry - initSL);
   double ticks = price_diff / tick_size;
   double risk_per_lot = ticks * tick_value;
   double total_risk = risk_per_lot * initVol;
   return total_risk;
}

// Core routine: build row and write
void LogPositionById(const ulong position_id)
{
   if(!InpEnableLogging) return;
   if(GVIsFlag(KeyLogged(position_id))) return; // Avoid duplicate

   double initSL=0, initVol=0, mfe=0, cachedEntry=0; 
   GVGetDouble(KeyInitSL(position_id), initSL); 
   GVGetDouble(KeyInitVol(position_id), initVol); 
   GVGetDouble(KeyMFE(position_id), mfe);
   GVGetDouble(KeyEntry(position_id), cachedEntry);

   string sym=""; int pos_type=-1; double entry=0; datetime tclose=TimeCurrent();
   double closePrice=0, profit=0, commission=0, swap=0; ENUM_DEAL_REASON reason=(ENUM_DEAL_REASON)0; long magic=0;

   datetime from = (datetime)(TimeCurrent() - 60*24*60*60);
   datetime to   = TimeCurrent();
   HistorySelect(from, to);
   uint deals = HistoryDealsTotal();

   datetime firstInTime=0, lastOutTime=0;
   for(uint i=0;i<deals;i++)
   {
      ulong dtk = HistoryDealGetTicket(i);
      if((ulong)HistoryDealGetInteger(dtk, DEAL_POSITION_ID) != position_id) continue;
      long dentry = HistoryDealGetInteger(dtk, DEAL_ENTRY);
      ENUM_DEAL_TYPE dtype  = (ENUM_DEAL_TYPE)HistoryDealGetInteger(dtk, DEAL_TYPE);
      string dsym = HistoryDealGetString(dtk, DEAL_SYMBOL);

      if(dentry == DEAL_ENTRY_IN)
      {
         datetime dt = (datetime)HistoryDealGetInteger(dtk, DEAL_TIME);
         if(firstInTime==0 || dt < firstInTime)
         {
            if(dtype == DEAL_TYPE_BUY || dtype == DEAL_TYPE_SELL)
            {
               firstInTime = dt;
               entry  = HistoryDealGetDouble(dtk, DEAL_PRICE);
               pos_type = (dtype == DEAL_TYPE_BUY) ? POSITION_TYPE_BUY : POSITION_TYPE_SELL;
               sym    = dsym;
               magic  = HistoryDealGetInteger(dtk, DEAL_MAGIC);
            }
         }
      }
      if(dentry == DEAL_ENTRY_OUT)
      {
         datetime dt = (datetime)HistoryDealGetInteger(dtk, DEAL_TIME);
         if(lastOutTime==0 || dt > lastOutTime)
         {
            lastOutTime = dt;
            tclose = dt;
            closePrice = HistoryDealGetDouble(dtk, DEAL_PRICE);
            reason = (ENUM_DEAL_REASON)HistoryDealGetInteger(dtk, DEAL_REASON);
         }
         // accumulate P/L across outs (includes partial closes)
         profit     += HistoryDealGetDouble(dtk, DEAL_PROFIT);
         commission += HistoryDealGetDouble(dtk, DEAL_COMMISSION);
         swap       += HistoryDealGetDouble(dtk, DEAL_SWAP);
         if(sym=="") sym = dsym;
      }
   }

   if(entry<=0) entry = cachedEntry; // best effort
   if(sym=="" && !InpApplyAllSymbols && StringLen(InpSymbolFilter)>0) sym = InpSymbolFilter;

   // Compute Risk in money and realized R multiple
   double risk_money = 0.0;
   if(sym!="" && entry>0 && initSL>0 && initVol>0)
      risk_money = ComputeInitialRiskMoney(sym, entry, initSL, initVol);

   double net_profit = profit + commission + swap; // commission usually negative
   double realized_R = (risk_money>0.0 ? net_profit / risk_money : 0.0);
   // No clamping: if closed by SL with slippage/costs, realized_R <= -1

   // Target prices for hit flags (still based on price-distance R for reference logic)
   double R_price = (entry>0 && initSL>0) ? MathAbs(entry - initSL) : 0.0;
   double tp0=0, tp1=0, tp2=0;
   if(R_price>0 && (sym!=""))
   {
      if(pos_type==POSITION_TYPE_BUY){
         tp0 = entry + InpTP0_RMultiple*R_price;
         tp1 = entry + InpTP1_RMultiple*R_price;
         tp2 = entry + InpTP2_RMultiple*R_price;
      } else if(pos_type==POSITION_TYPE_SELL){
         tp0 = entry - InpTP0_RMultiple*R_price;
         tp1 = entry - InpTP1_RMultiple*R_price;
         tp2 = entry - InpTP2_RMultiple*R_price;
      }
   }

   // Decide hits based on MFE
   int tp0_hit=0, tp1_hit=0, tp2_hit=0;
   double highestR = 0.0;
   if(R_price>0 && mfe>0 && entry>0 && pos_type!=-1)
   {
      if(pos_type==POSITION_TYPE_BUY)
      {
         highestR = (mfe - entry) / R_price;
         tp0_hit = (tp0>0 && mfe >= tp0) ? 1 : 0;
         tp1_hit = (tp1>0 && mfe >= tp1) ? 1 : 0;
         tp2_hit = (tp2>0 && mfe >= tp2) ? 1 : 0;
      }
      else
      {
         highestR = (entry - mfe) / R_price;
         tp0_hit = (tp0>0 && mfe <= tp0) ? 1 : 0;
         tp1_hit = (tp1>0 && mfe <= tp1) ? 1 : 0;
         tp2_hit = (tp2>0 && mfe <= tp2) ? 1 : 0;
      }
      if(highestR < 0) highestR = 0.0;
   }

   // Write log row (compact header)
   int h = OpenLog();
   if(h != INVALID_HANDLE)
   {
      FileWrite(h,
        TimeToString(tclose, TIME_DATE|TIME_SECONDS), (long)position_id, sym,
        (pos_type==POSITION_TYPE_BUY?"BUY":(pos_type==POSITION_TYPE_SELL?"SELL":"")),
        DoubleToString(entry, _Digits),
        DoubleToString(initSL, _Digits),
        DoubleToString((R_price>0 ? R_price/SymbolInfoDouble(sym, SYMBOL_POINT) : 0.0), 1), // SL_Points
        DoubleToString(risk_money, 2),
        DoubleToString(realized_R, 3),
        DoubleToString(tp0, _Digits),
        DoubleToString(tp1, _Digits),
        DoubleToString(tp2, _Digits),
        DoubleToString(mfe, _Digits),
        DoubleToString(highestR, 2),
        tp0_hit, tp1_hit, tp2_hit,
        DoubleToString(closePrice, _Digits),
        CloseCauseToString(reason),
        DoubleToString(profit, 2),
        DoubleToString(commission, 2),
        DoubleToString(swap, 2),
        DoubleToString(initVol, 2),
        (long)magic
      );
      FileClose(h);
   }

   GVSetFlag(KeyLogged(position_id)); // mark as logged
   // cleanup
   GlobalVariableDel(KeyInitSL(position_id));
   GlobalVariableDel(KeyInitVol(position_id));
   GlobalVariableDel(KeyMFE(position_id));
   GlobalVariableDel(KeyEntry(position_id));
}

int OnInit()
{
   int h = OpenLog(); if(h!=INVALID_HANDLE) FileClose(h);
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   int total = PositionsTotal();
   for(int i = 0; i < total; ++i)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;

      string sym = "";         PositionGetString(POSITION_SYMBOL, sym);
      long   mg  = (long)PositionGetInteger(POSITION_MAGIC);
      long   typ = (long)PositionGetInteger(POSITION_TYPE);
      double vol = PositionGetDouble(POSITION_VOLUME);
      double sl  = PositionGetDouble(POSITION_SL);
      double ep  = PositionGetDouble(POSITION_PRICE_OPEN);

      if(!InpApplyAllSymbols)
      {
         if(StringLen(InpSymbolFilter) > 0 && sym != InpSymbolFilter) continue;
      }
      if(InpMagicFilter != -1 && mg != InpMagicFilter) continue;

      if(InpUseInitialSL) MaybeFreezeInitials(ticket, sl, vol, ep);
      UpdateMFE(ticket, sym, typ);
   }

   // Fallback sweep
   int totalGV = GlobalVariablesTotal();
   for(int gi=0; gi<totalGV; ++gi)
   {
      string name = GlobalVariableName(gi);
      if(StringFind(name, "PC_INITSL_") == 0)
      {
         ulong tk = (ulong)StringToInteger(StringSubstr(name, StringLen("PC_INITSL_")));
         if(!PositionSelectByTicket(tk) && !GVIsFlag(KeyLogged(tk)))
            LogPositionById(tk);
      }
   }
}

// Log immediately on close deals
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult&  result)
{
   if(!InpEnableLogging) return;
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;

   ulong deal = trans.deal;
   if(deal==0) return;

   ENUM_DEAL_ENTRY dentry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(deal, DEAL_ENTRY);
   if(dentry != DEAL_ENTRY_OUT) return; // only on exits

   ulong pos_id = (ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID);
   string sym   = HistoryDealGetString(deal, DEAL_SYMBOL);
   long magic   = HistoryDealGetInteger(deal, DEAL_MAGIC);

   if(!InpApplyAllSymbols && StringLen(InpSymbolFilter)>0 && sym != InpSymbolFilter) return;
   if(InpMagicFilter != -1 && magic != InpMagicFilter) return;

   LogPositionById(pos_id);
}

void OnDeinit(const int reason){}
//+------------------------------------------------------------------+
