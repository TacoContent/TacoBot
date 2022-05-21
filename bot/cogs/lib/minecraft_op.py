from enum import Enum

class MinecraftOpLevel(Enum):
    LEVEL1 = 1
    LEVEL2 = 2
    LEVEL3 = 3
    LEVEL4 = 4
    
    def __int__(self):
        return self.value
