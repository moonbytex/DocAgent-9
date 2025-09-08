from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from decimal import Decimal


class TxStatus(Enum):
    WAIT = 'pending'
    DONE = 'completed'
    ERR = 'failed'
    RET = 'refunded'


@dataclass
class Tx:
    id: str
    amt: Decimal
    st: TxStatus
    mth: str
    msg: Optional[str] = None


class Handler(ABC):

    @abstractmethod
    def proc(self, amt: Decimal) ->Tx:
        pass

    @abstractmethod
    def rev(self, tx: Tx) ->bool:
        pass


class Cash(Handler):

    def __init__(self):
        self.bal: Decimal = Decimal('0.00')

    def add(self, amt: Decimal) ->None:
        self.bal += amt

    def proc(self, amt: Decimal) ->Tx:
        if self.bal >= amt:
            self.bal -= amt
            return Tx(id=f'C_{id(self)}', amt=amt, st=TxStatus.DONE, mth='cash'
                )
        return Tx(id=f'C_{id(self)}', amt=amt, st=TxStatus.ERR, mth='cash',
            msg='insufficient')

    def rev(self, tx: Tx) ->bool:
        if tx.st == TxStatus.DONE:
            self.bal += tx.amt
            tx.st = TxStatus.RET
            return True
        return False

    def ret(self) ->Decimal:
        tmp = self.bal
        self.bal = Decimal('0.00')
        return tmp
