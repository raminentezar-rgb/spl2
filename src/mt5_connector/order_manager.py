"""
مدیریت سفارشات در متاتریدر 5
"""
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

import pandas as pd
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from ..utils.logger import get_logger
from ..utils.helpers import pips_to_price

logger = get_logger(__name__)

class OrderManager:
    """
    مدیریت سفارشات معاملاتی
    """
    
    def __init__(self, connector, config: Dict):
        """
        Args:
            connector: نمونه MT5Connector
            config: تنظیمات
        """
        self.connector = connector
        self.config = config
        self.magic_number = config.get('trading', {}).get('magic_number', 234000)
        self.symbol = config.get('trading', {}).get('symbol', 'XAUUSD')
        self.deviation = config.get('trading', {}).get('deviation', 10)
        
    def place_buy_order(self, 
                        symbol: str, 
                        volume: float, 
                        sl: Optional[float] = None,
                        tp: Optional[float] = None,
                        comment: str = "SP2L Buy",
                        order_type: str = "market") -> Dict:
        """
        ثبت سفارش خرید
        """
        if not MT5_AVAILABLE or not self.connector.connected:
            logger.error("MT5 not available or not connected")
            return {'success': False, 'error': 'MT5 not available'}

        try:
            # دریافت قیمت‌های فعلی
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Failed to get tick for {symbol}")
                return {'success': False, 'error': 'No tick data'}
            
            price = tick.ask
            logger.info(f"Placing BUY order: {symbol} {volume} lots at {price}")
            
            # آماده‌سازی درخواست
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(volume),
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "deviation": self.deviation,
                "magic": self.magic_number,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # اضافه کردن حد ضرر و سود
            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp
            
            # ارسال سفارش
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order failed: {result.comment} (retcode={result.retcode})")
                return {
                    'success': False,
                    'error': result.comment,
                    'retcode': result.retcode
                }
            
            logger.info(f"Order placed successfully: {result.order}")
            return {
                'success': True,
                'order_id': result.order,
                'price': result.price,
                'volume': result.volume,
                'comment': comment
            }
            
        except Exception as e:
            logger.error(f"Error placing buy order: {e}")
            return {'success': False, 'error': str(e)}
    
    def place_sell_order(self,
                         symbol: str,
                         volume: float,
                         sl: Optional[float] = None,
                         tp: Optional[float] = None,
                         comment: str = "SP2L Sell",
                         order_type: str = "market") -> Dict:
        """
        ثبت سفارش فروش
        """
        if not MT5_AVAILABLE or not self.connector.connected:
            logger.error("MT5 not available or not connected")
            return {'success': False, 'error': 'MT5 not available'}

        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Failed to get tick for {symbol}")
                return {'success': False, 'error': 'No tick data'}
            
            price = tick.bid
            logger.info(f"Placing SELL order: {symbol} {volume} lots at {price}")
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(volume),
                "type": mt5.ORDER_TYPE_SELL,
                "price": price,
                "deviation": self.deviation,
                "magic": self.magic_number,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order failed: {result.comment} (retcode={result.retcode})")
                return {
                    'success': False,
                    'error': result.comment,
                    'retcode': result.retcode
                }
            
            logger.info(f"Order placed successfully: {result.order}")
            return {
                'success': True,
                'order_id': result.order,
                'price': result.price,
                'volume': result.volume,
                'comment': comment
            }
            
        except Exception as e:
            logger.error(f"Error placing sell order: {e}")
            return {'success': False, 'error': str(e)}
    
    def place_limit_order(self, 
                          symbol: str,
                          order_type: str,  # 'buy' or 'sell'
                          volume: float,
                          price: float,
                          sl: Optional[float] = None,
                          tp: Optional[float] = None,
                          comment: str = "SP2L Limit") -> Dict:
        """
        ثبت سفارش محدود (Limit Order)
        """
        if not MT5_AVAILABLE:
            return {'success': False, 'error': 'MT5 not available'}

        try:
            mt5_order_type = mt5.ORDER_TYPE_BUY_LIMIT if order_type == 'buy' else mt5.ORDER_TYPE_SELL_LIMIT
            
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": float(volume),
                "type": mt5_order_type,
                "price": price,
                "deviation": self.deviation,
                "magic": self.magic_number,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }
            
            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Limit order failed: {result.comment}")
                return {'success': False, 'error': result.comment}
            
            return {
                'success': True,
                'order_id': result.order,
                'price': result.price,
                'volume': result.volume
            }
            
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            return {'success': False, 'error': str(e)}
    
    def modify_order(self, order_id: int, sl: Optional[float] = None, tp: Optional[float] = None) -> Dict:
        """
        تغییر سفارش موجود
        """
        if not MT5_AVAILABLE:
            return {'success': False, 'error': 'MT5 not available'}

        try:
            # دریافت سفارش فعلی
            order = mt5.orders_get(ticket=order_id)
            if order is None or len(order) == 0:
                logger.error(f"Order {order_id} not found")
                return {'success': False, 'error': 'Order not found'}
            
            order = order[0]
            
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "order": order_id,
                "symbol": order.symbol,
                "volume": order.volume_current,
                "price": order.price_open,
                "deviation": self.deviation,
                "magic": self.magic_number,
            }
            
            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Modify order failed: {result.comment}")
                return {'success': False, 'error': result.comment}
            
            return {'success': True, 'order_id': order_id}
            
        except Exception as e:
            logger.error(f"Error modifying order: {e}")
            return {'success': False, 'error': str(e)}
    
    def close_position(self, position_id: int, volume: Optional[float] = None) -> Dict:
        """
        بستن یک پوزیشن
        """
        if not MT5_AVAILABLE:
            return {'success': False, 'error': 'MT5 not available'}

        try:
            # دریافت پوزیشن
            position = mt5.positions_get(ticket=position_id)
            if position is None or len(position) == 0:
                logger.error(f"Position {position_id} not found")
                return {'success': False, 'error': 'Position not found'}
            
            position = position[0]
            
            # تعیین نوع سفارش برعکس
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(position.symbol).bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(position.symbol).ask
            
            close_volume = volume if volume is not None else position.volume
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": float(close_volume),
                "type": order_type,
                "position": position_id,
                "price": price,
                "deviation": self.deviation,
                "magic": self.magic_number,
                "comment": "Close by SP2L",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Close position failed: {result.comment}")
                return {'success': False, 'error': result.comment}
            
            logger.info(f"Position {position_id} closed successfully")
            return {
                'success': True,
                'position_id': position_id,
                'profit': position.profit
            }
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {'success': False, 'error': str(e)}
    
    def close_all_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        بستن تمام پوزیشن‌ها
        """
        results = []
        positions = self.connector.get_positions(symbol)
        
        if positions.empty:
            logger.info("No positions to close")
            return results
        
        for _, position in positions.iterrows():
            result = self.close_position(position['ticket'])
            results.append(result)
            
            if result['success']:
                logger.info(f"Closed position {position['ticket']} with profit {result.get('profit', 0)}")
        
        return results
    
    def get_open_positions_count(self, symbol: Optional[str] = None) -> int:
        """تعداد پوزیشن‌های باز"""
        positions = self.connector.get_positions(symbol)
        return len(positions) if not positions.empty else 0
    
    def calculate_pips_to_price(self, symbol: str, pips: float) -> float:
        """تبدیل پیپ به قیمت"""
        if not MT5_AVAILABLE:
            return pips * 0.0001
            
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return pips * 0.0001  # تخمین
        
        return pips_to_price(pips, symbol_info.point, symbol_info.digits)