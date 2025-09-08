from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Item:
    code: str
    label: str
    val: float
    count: int
    exp: Optional[datetime] = None
    grp: str = 'misc'

    def check(self) ->bool:
        if self.count <= 0:
            return False
        if self.exp and datetime.now() > self.exp:
            return False
        return True

    def mod(self, n: int=1) ->bool:
        if self.count >= n:
            self.count -= n
            return True
        return False
