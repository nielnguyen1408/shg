//+------------------------------------------------------------------+
//|                                              SimpleRunnableEA.mq5 |
//|                         Basic, fully compilable and runnable EA  |
//+------------------------------------------------------------------+
#property copyright "You"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
CTrade trade;

input double Lots = 0.10;        // Lot size
input int    StopLoss = 200;     // Stop Loss in points
input int    TakeProfit = 400;   // Take Profit in points
input bool   AllowTrading = true;// Allow trading

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   Print("SimpleRunnableEA initialized on symbol ", _Symbol);
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   Print("SimpleRunnableEA deinitialized.");
  }
//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
   if(!AllowTrading) return;

   static datetime lastTradeTime = 0;
   datetime currentTime = TimeCurrent();

   // Only one trade per new bar
   if(iTime(_Symbol, PERIOD_M1, 0) == lastTradeTime)
      return;
   lastTradeTime = iTime(_Symbol, PERIOD_M1, 0);

   // Simple logic: Buy if last candle bullish, Sell if bearish
   double openPrice  = iOpen(_Symbol, PERIOD_M1, 1);
   double closePrice = iClose(_Symbol, PERIOD_M1, 1);
   if(openPrice == 0 || closePrice == 0) return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) return;

   double price, sl, tp;

   // No open position check
   if(PositionSelect(_Symbol)) return;

   if(closePrice > openPrice)
     {
      // BUY
      price = tick.ask;
      sl = price - StopLoss * _Point;
      tp = price + TakeProfit * _Point;
      trade.Buy(Lots, _Symbol, price, sl, tp, "SimpleRunnableEA BUY");
     }
   else if(closePrice < openPrice)
     {
      // SELL
      price = tick.bid;
      sl = price + StopLoss * _Point;
      tp = price - TakeProfit * _Point;
      trade.Sell(Lots, _Symbol, price, sl, tp, "SimpleRunnableEA SELL");
     }
  }
//+------------------------------------------------------------------+
